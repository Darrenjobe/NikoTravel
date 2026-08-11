"""Conversation history — GET /api/conversations[?type=], /{id}.

One feed covering both Ask threads and Journal entries. Summaries are
AI-generated once a thread goes quiet; until then a title is derived from the
first user message so the list is never blank or "Untitled".
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.jobs import summarize
from app.services import archive
from app.storage import db

router = APIRouter()

VALID_TYPES = ("ask", "journal")


def _fallback_title(thread_id: str) -> str:
    """First user message, trimmed — used until the AI summary exists."""
    with db.conn() as c:
        row = c.execute(
            "SELECT text FROM conversations WHERE thread_id=? AND role='user' "
            "ORDER BY created_at LIMIT 1",
            (thread_id,),
        ).fetchone()
    if not row or not row["text"]:
        return "New conversation"
    text = " ".join(row["text"].split())
    return text if len(text) <= 80 else text[:77].rstrip() + "…"


def _serialize(row: dict) -> dict:
    with db.conn() as c:
        count = c.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE thread_id=?", (row["id"],)
        ).fetchone()["n"]
        place_name = None
        if row["entry_id"]:
            entry = c.execute(
                "SELECT place_name FROM journal_entries WHERE id=?", (row["entry_id"],)
            ).fetchone()
            place_name = entry["place_name"] if entry else None
    return {
        "id": row["id"],
        "type": row["kind"],
        "summary": row["summary"] or _fallback_title(row["id"]),
        "summary_is_ai": bool(row["summary"]),
        "started_at": row["started_at"],
        "updated_at": row["last_at"],
        "message_count": count,
        "entry_id": row["entry_id"],
        "place_name": place_name,
    }


@router.get("/api/conversations")
def list_conversations(
    background: BackgroundTasks,
    type: str | None = Query(default=None, description="ask | journal"),
    limit: int = Query(default=100, le=500),
):
    if type is not None and type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of {VALID_TYPES}")

    sql = "SELECT * FROM threads"
    params: list = []
    if type:
        sql += " WHERE kind=?"
        params.append(type)
    sql += " ORDER BY last_at DESC LIMIT ?"
    params.append(limit)

    with db.conn() as c:
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]

    # Backfill summaries off the request path so the list stays fast.
    if summarize.pending(limit=1):
        background.add_task(summarize.run, 5)

    return {"conversations": [_serialize(r) for r in rows]}


@router.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    with db.conn() as c:
        row = c.execute(
            "SELECT * FROM threads WHERE id=?", (conversation_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "conversation not found")

    payload = _serialize(dict(row))
    payload["messages"] = [
        {"role": m["role"], "text": m["text"], "timestamp": m["created_at"]}
        for m in archive.thread_messages(conversation_id)
    ]
    return payload
