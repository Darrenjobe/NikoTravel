"""POST /api/journal/* — conversational feedback capture with place resolution."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import config
from app.services import archive, llm, places
from app.storage import db

router = APIRouter()

INTERVIEW_SYSTEM = """You are Niko, interviewing a traveler about a place they
just experienced ({place}). Ask one short, warm follow-up question at a time,
tuned to the kind of place (food for restaurants, atmosphere/history for sites).
After two or three exchanges, invite them to tap Done. Never ask more than one
question per reply."""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": ["loved", "mixed", "skip"]},
        "line": {"type": "string", "description": "One-line verdict, first person tone"},
        "summary": {"type": "string", "description": "3-4 sentence experience summary"},
        "best": {"type": "string"},
        "worst": {"type": "string"},
        "likes": {"type": "array", "items": {"type": "string"}},
        "dislikes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sentiment", "line", "summary", "best", "worst", "likes", "dislikes"],
    "additionalProperties": False,
}


class StartRequest(BaseModel):
    maps_link: str | None = None


class MessageRequest(BaseModel):
    entry_id: str
    message: str
    lat: float | None = None
    lon: float | None = None


class ConfirmRequest(BaseModel):
    entry_id: str
    accepted: bool


class FinishRequest(BaseModel):
    entry_id: str


def _get(entry_id: str) -> dict:
    with db.conn() as c:
        row = c.execute("SELECT * FROM journal_entries WHERE id=?", (entry_id,)).fetchone()
    if not row:
        raise HTTPException(404, "entry not found")
    return db.row_to_dict(row)


def _append(entry_id: str, role: str, text: str) -> list:
    entry = _get(entry_id)
    transcript = entry["transcript"] + [{"role": role, "text": text}]
    with db.conn() as c:
        c.execute(
            "UPDATE journal_entries SET transcript=? WHERE id=?",
            (json.dumps(transcript), entry_id),
        )
    return transcript


@router.post("/api/journal/start")
def start(req: StartRequest):
    entry_id = db.new_id()
    with db.conn() as c:
        c.execute(
            "INSERT INTO journal_entries (id, created_at, maps_url) VALUES (?,?,?)",
            (entry_id, db.now(), req.maps_link),
        )
    # A journal thread reuses the entry id, so the conversation feed and the
    # journal entry are the same object from two angles — no extra state.
    archive.ensure_thread(entry_id, kind="journal", entry_id=entry_id)
    reply = "How was it? Tell me about somewhere you just went — a meal, a monastery, a museum, anything."
    _append(entry_id, "assistant", reply)
    archive.record_turn("journal", "assistant", reply, thread_id=entry_id)
    return {"entry_id": entry_id, "reply": reply}


@router.post("/api/journal/message")
def message(req: MessageRequest):
    entry = _get(req.entry_id)
    _append(req.entry_id, "user", req.message)
    archive.record_turn("journal", "user", req.message, thread_id=req.entry_id)

    candidate = None
    # First user message with no place attached → try to resolve one.
    if entry["place_id"] is None and entry["place_name"] is None:
        resolved = places.resolve(req.message, req.lat, req.lon)
        if resolved and resolved.get("name"):
            candidate = resolved
            reply = f"Is this the place — {resolved['name']}, {resolved.get('address', '')}?"
            _append(req.entry_id, "assistant", reply)
            # The candidate rides in the transcript (role="candidate") until
            # /confirm accepts or rejects it — no extra schema needed.
            _append(req.entry_id, "candidate", json.dumps(resolved))
            return {"reply": reply, "candidate": candidate}

    place = entry["place_name"] or "an unconfirmed location"
    transcript = _get(req.entry_id)["transcript"]
    convo = "\n".join(
        f"{t['role']}: {t['text']}" for t in transcript if t["role"] in ("user", "assistant")
    )
    reply = llm.get_llm().complete(
        model=config.CHAT_MODEL,
        system=INTERVIEW_SYSTEM.format(place=place),
        prompt=f"Conversation so far:\n{convo}\n\nWrite your next reply.",
        max_tokens=300,
    )
    _append(req.entry_id, "assistant", reply)
    archive.record_turn("journal", "assistant", reply, thread_id=req.entry_id)
    return {"reply": reply, "candidate": None}


@router.post("/api/journal/confirm")
def confirm(req: ConfirmRequest):
    entry = _get(req.entry_id)
    candidate = next(
        (json.loads(t["text"]) for t in reversed(entry["transcript"]) if t["role"] == "candidate"),
        None,
    )
    if req.accepted and candidate:
        with db.conn() as c:
            c.execute(
                "UPDATE journal_entries SET place_name=?, place_id=?, maps_url=?, lat=?, lon=?, category=? WHERE id=?",
                (
                    candidate["name"],
                    candidate["place_id"],
                    candidate["maps_url"],
                    candidate["lat"],
                    candidate["lon"],
                    candidate["category"],
                    req.entry_id,
                ),
            )
        reply = "Perfect, linked it. So — what stood out?"
    else:
        with db.conn() as c:
            c.execute(
                "UPDATE journal_entries SET place_name=NULL, place_id=NULL WHERE id=?",
                (req.entry_id,),
            )
        reply = "No problem — I'll leave it unlinked. Tell me about it anyway."
    _append(req.entry_id, "assistant", reply)
    return {"reply": reply}


@router.post("/api/journal/finish")
def finish(req: FinishRequest):
    entry = _get(req.entry_id)
    convo = "\n".join(
        f"{t['role']}: {t['text']}"
        for t in entry["transcript"]
        if t["role"] in ("user", "assistant")
    )
    extracted = llm.get_llm().extract_json(
        model=config.JOB_MODEL,
        system="Extract structured feedback from this travel journal conversation.",
        prompt=convo,
        schema=EXTRACTION_SCHEMA,
    )
    with db.conn() as c:
        c.execute(
            "UPDATE journal_entries SET status='done', sentiment=?, line=?, summary=?, best=?, worst=? WHERE id=?",
            (
                extracted["sentiment"],
                extracted["line"],
                extracted["summary"],
                extracted["best"],
                extracted["worst"],
                req.entry_id,
            ),
        )
        for kind, labels in (("like", extracted["likes"]), ("dislike", extracted["dislikes"])):
            for label in labels:
                c.execute(
                    "INSERT OR REPLACE INTO preferences (kind, label, updated_at) VALUES (?,?,?)",
                    (kind, label.lower(), db.now()),
                )
    final = _get(req.entry_id)
    archive.record_entry(final)
    return {"entry": final}


@router.get("/api/journal/{entry_id}/transcript")
def transcript(entry_id: str):
    """The full back-and-forth that produced an entry — not just the summary.

    The stored transcript is authoritative (it includes Niko's opener). The
    internal 'candidate' rows are place-resolution bookkeeping, not dialogue,
    so they're filtered out.
    """
    entry = _get(entry_id)
    return {
        "entry_id": entry_id,
        "place_name": entry["place_name"],
        "status": entry["status"],
        "messages": [
            {"role": t["role"], "text": t["text"]}
            for t in entry["transcript"]
            if t["role"] in ("user", "assistant")
        ],
    }


@router.delete("/api/journal/{entry_id}")
def discard(entry_id: str):
    """Discard an in-progress entry (the client's 'Discard' button).

    Refuses to delete a finished entry — those are the trip's record and
    should go through a deliberate delete, not an accidental one.
    """
    entry = _get(entry_id)
    if entry["status"] == "done":
        raise HTTPException(
            409, "entry is already filed; discard only applies to drafts"
        )
    with db.conn() as c:
        c.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
        c.execute("DELETE FROM conversations WHERE thread_id=?", (entry_id,))
        c.execute("DELETE FROM threads WHERE id=?", (entry_id,))
    return {"discarded": entry_id}
