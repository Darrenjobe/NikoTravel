"""Interaction archive — the corpus behind Trip memory, the Insights digest,
and the conversation history screens.

Every turn lands twice: a row in SQLite (system of record, grouped into
threads) and a document in the Chroma 'archive' collection (retrieval index).
"""
from __future__ import annotations

import json

from app.services import rag
from app.storage import db

MAX_CONTEXT_TURNS = 12  # turns replayed to the LLM for multi-turn continuity


# --------------------------------------------------------------------------
# Threads
# --------------------------------------------------------------------------

def ensure_thread(thread_id: str | None, kind: str, entry_id: str | None = None) -> str:
    """Return an existing thread id, or create a new thread."""
    now = db.now()
    if thread_id:
        with db.conn() as c:
            row = c.execute("SELECT id FROM threads WHERE id=?", (thread_id,)).fetchone()
            if row:
                c.execute("UPDATE threads SET last_at=? WHERE id=?", (now, thread_id))
                return thread_id
    new_id = thread_id or db.new_id()
    with db.conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO threads (id, kind, started_at, last_at, entry_id) "
            "VALUES (?,?,?,?,?)",
            (new_id, kind, now, now, entry_id),
        )
    return new_id


def touch_thread(thread_id: str) -> None:
    with db.conn() as c:
        c.execute("UPDATE threads SET last_at=? WHERE id=?", (db.now(), thread_id))


def thread_messages(thread_id: str, limit: int | None = None) -> list[dict]:
    sql = (
        "SELECT role, text, created_at FROM conversations "
        "WHERE thread_id=? ORDER BY created_at"
    )
    with db.conn() as c:
        rows = c.execute(sql, (thread_id,)).fetchall()
    msgs = [dict(r) for r in rows]
    return msgs[-limit:] if limit else msgs


def llm_history(thread_id: str) -> list[dict]:
    """Prior turns shaped for the Messages API, so follow-up questions
    ('what about tomorrow?') resolve against what was already said."""
    return [
        {"role": m["role"], "content": m["text"]}
        for m in thread_messages(thread_id, limit=MAX_CONTEXT_TURNS)
        if m["role"] in ("user", "assistant") and m["text"]
    ]


# --------------------------------------------------------------------------
# Turns
# --------------------------------------------------------------------------

def record_turn(
    kind: str,
    role: str,
    text: str,
    meta: dict | None = None,
    thread_id: str | None = None,
) -> None:
    with db.conn() as c:
        cur = c.execute(
            "INSERT INTO conversations (created_at, kind, role, text, meta, thread_id) "
            "VALUES (?,?,?,?,?,?)",
            (db.now(), kind, role, text, json.dumps(meta or {}), thread_id),
        )
        row_id = cur.lastrowid
    if thread_id:
        touch_thread(thread_id)
    if role == "user" or len(text) > 80:  # skip trivial assistant acks
        rag.add_to_archive(
            f"conv-{row_id}",
            f"[{kind}/{role}] {text}",
            {"kind": kind, "role": role, "thread_id": thread_id or ""},
        )


def record_entry(entry: dict) -> None:
    doc = (
        f"Journal entry — {entry.get('place_name') or 'Unconfirmed location'} "
        f"({entry.get('sentiment')}): {entry.get('summary')} "
        f"Best: {entry.get('best')} Worst: {entry.get('worst')}"
    )
    rag.add_to_archive(f"entry-{entry['id']}", doc, {"kind": "journal_entry"})


# --------------------------------------------------------------------------
# Digest windows
# --------------------------------------------------------------------------

def interactions_last_hours(hours: int = 24) -> int:
    cutoff = db.now() - hours * 3600
    with db.conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE created_at > ? AND role='user'",
            (cutoff,),
        ).fetchone()
    return row["n"]


def window_text(hours: int = 24, limit: int = 200) -> str:
    cutoff = db.now() - hours * 3600
    with db.conn() as c:
        rows = c.execute(
            "SELECT kind, role, text FROM conversations WHERE created_at > ? "
            "ORDER BY created_at LIMIT ?",
            (cutoff, limit),
        ).fetchall()
    return "\n".join(f"[{r['kind']}/{r['role']}] {r['text']}" for r in rows)
