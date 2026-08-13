"""POST /api/chat — the Ask tab.

Threaded: a request without `conversation_id` starts a new thread and the
response returns its id; sending it back continues the thread, so follow-up
questions resolve against what was already said. Every turn is persisted for
the conversation-history screens.
"""
from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from app import config
from app.services import archive, context, llm, places, rag, search, settings, tripday

router = APIRouter()

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the live web. Call this when the answer depends on current "
            "information: opening hours, weather, ferry/transit schedules, "
            "prices, or anything time-sensitive. Do not answer hours or "
            "weather questions from memory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "recommend_places",
        "description": (
            "Find real nearby places (restaurants, cafes, sites) via Google "
            "Places, biased to the traveler's GPS position. Call this whenever "
            "you recommend somewhere to eat, drink, or visit, so each "
            "recommendation carries a real Place ID and Maps link."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "e.g. 'seafood taverna'"},
                "count": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
]

SYSTEM = """You are Nikos, a warm, knowledgeable greek travel companion accompanying one
traveler on a spiritual & historical tour of Greece (Orthodox saints, early
Christianity, classical history). Answer as a trusted local guide: concrete,
practical, grounded in where they are standing right now. Keep answers focused, easy to TTS 
(text to speech, meaning no weird formating or special characters) and scannable on a 
phone screen.

Adopt the persona of a deeply spiritual greek orthodox man who is friendly, casual, 
knowledgable about greece. You will sometime slip in a greek idom, phrase or use a 
greek word when describing something uniquely greek (but try to provide an explanation 
of the meaning if unclear).
While primarily speaking english, when using a greek word or referring to a greek place,
use the greek character set (and english in parenthesis).

You already know the following — never ask the traveler for it:
{ambient}

{retrieved}"""

MEMORY_SYSTEM = """You are Nikos, the traveler's trip companion, in TRIP MEMORY
mode: they are asking about something from their own trip — a place they
visited, something they said, a past conversation. Answer from the retrieved
trip archive below. Quote their own words where it helps, and name the source
(e.g. "your journal entry from Sept 5"). If the archive doesn't contain it, say
so plainly — never invent memories.

Current context:
{ambient}

Trip archive excerpts:
{retrieved}"""


class ChatRequest(BaseModel):
    message: str
    lat: float | None = None
    lon: float | None = None
    memory_mode: bool = False
    timestamp: str | None = None
    conversation_id: str | None = None


@router.post("/api/chat")
def chat(req: ChatRequest):
    thread_id = archive.ensure_thread(req.conversation_id, kind="ask")

    ambient = context.build(lat=req.lat, lon=req.lon, timestamp=req.timestamp)

    collection = "archive" if req.memory_mode else "knowledge"
    hits = rag.query(collection, req.message, n=5)
    retrieved = "\n---\n".join(h["text"] for h in hits) or "(nothing retrieved)"
    template = MEMORY_SYSTEM if req.memory_mode else SYSTEM
    system = template.format(ambient=ambient, retrieved=retrieved)

    recommended: list[dict] = []

    def execute_tool(name: str, tool_input: dict) -> str:
        if name == "web_search":
            return search.web_search(tool_input["query"])
        if name == "recommend_places":
            results = places.recommend(
                tool_input["query"], req.lat, req.lon, n=tool_input.get("count", 3)
            )
            recommended.extend(results)
            return json.dumps(results)
        return "Unknown tool."

    # Prior turns first, then this one — gives Nikos continuity within a thread.
    messages = archive.llm_history(thread_id) + [
        {"role": "user", "content": req.message}
    ]

    result = llm.get_llm().chat_with_tools(
        model=settings.chat_model(),
        system=system,
        messages=messages,
        tools=[] if req.memory_mode else TOOLS,
        execute_tool=execute_tool,
    )

    archive.record_turn(
        "chat", "user", req.message,
        {"memory_mode": req.memory_mode}, thread_id=thread_id,
    )
    archive.record_turn("chat", "assistant", result["text"], thread_id=thread_id)

    sources = (
        [h["meta"].get("kind") or h["meta"].get("source") for h in hits]
        if req.memory_mode
        else []
    )
    return {
        "reply": result["text"],
        "places": recommended,
        "sources": sources,
        "conversation_id": thread_id,
    }
