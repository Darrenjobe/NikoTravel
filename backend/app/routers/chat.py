"""POST /api/chat — the Ask tab. Concierge with itinerary RAG, live search,
place recommendations, and the Trip memory mode."""
from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from app import config
from app.services import archive, llm, places, rag, search, tripday

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

SYSTEM = """You are Niko, a warm, knowledgeable travel concierge accompanying one
traveler on a spiritual & historical tour of Greece (Orthodox saints, early
Christianity, classical history). Answer as a trusted local guide: concrete,
practical, grounded in where they are standing right now. Keep answers focused
and scannable on a phone screen. Use the trip context and retrieved notes below;
when you recommend places, ground them in the traveler's logged preferences.

{trip_context}

{retrieved}"""

MEMORY_SYSTEM = """You are Niko, the traveler's trip companion, in TRIP MEMORY
mode: the traveler is asking about something from their own trip — a place they
visited, something they said, a past conversation. Answer from the retrieved
trip archive below. Quote their own words where it helps, and name the source
(e.g. "your journal entry from Sept 5"). If the archive doesn't contain it, say
so plainly — never invent memories.

{trip_context}

Trip archive excerpts:
{retrieved}"""


class ChatRequest(BaseModel):
    message: str
    lat: float | None = None
    lon: float | None = None
    memory_mode: bool = False


@router.post("/api/chat")
def chat(req: ChatRequest):
    ctx = tripday.context()
    trip_context = (
        f"Today is {ctx['date']}, day {ctx['trip_day']} of the trip. "
        f"Current itinerary region: {ctx['region']}."
        if ctx["trip_day"]
        else "The trip has not started yet (planning mode)."
    )

    collection = "archive" if req.memory_mode else "knowledge"
    hits = rag.query(collection, req.message, n=5)
    retrieved = "\n---\n".join(h["text"] for h in hits) or "(nothing retrieved)"
    template = MEMORY_SYSTEM if req.memory_mode else SYSTEM
    system = template.format(trip_context=trip_context, retrieved=retrieved)

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

    result = llm.get_llm().chat_with_tools(
        model=config.CHAT_MODEL,
        system=system,
        messages=[{"role": "user", "content": req.message}],
        tools=[] if req.memory_mode else TOOLS,
        execute_tool=execute_tool,
    )

    archive.record_turn("chat", "user", req.message, {"memory_mode": req.memory_mode})
    archive.record_turn("chat", "assistant", result["text"])

    sources = [h["meta"].get("kind") or h["meta"].get("source") for h in hits] if req.memory_mode else []
    return {"reply": result["text"], "places": recommended, "sources": sources}
