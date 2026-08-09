"""Interaction archive — the corpus behind Trip memory and the Insights digest.

Every chat turn and finished journal entry lands here twice: a row in SQLite
(the system of record) and a document in the Chroma 'archive' collection
(the retrieval index).
"""
from __future__ import annotations

import json

from app.services import rag
from app.storage import db


def record_turn(kind: str, role: str, text: str, meta: dict | None = None) -> None:
    with db.conn() as c:
        cur = c.execute(
            "INSERT INTO conversations (created_at, kind, role, text, meta) VALUES (?,?,?,?,?)",
            (db.now(), kind, role, text, json.dumps(meta or {})),
        )
        row_id = cur.lastrowid
    if role == "user" or len(text) > 80:  # skip trivial assistant acks
        rag.add_to_archive(
            f"conv-{row_id}", f"[{kind}/{role}] {text}", {"kind": kind, "role": role}
        )


def record_entry(entry: dict) -> None:
    doc = (
        f"Journal entry — {entry.get('place_name') or 'Unconfirmed location'} "
        f"({entry.get('sentiment')}): {entry.get('summary')} "
        f"Best: {entry.get('best')} Worst: {entry.get('worst')}"
    )
    rag.add_to_archive(f"entry-{entry['id']}", doc, {"kind": "journal_entry"})


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
            "SELECT kind, role, text FROM conversations WHERE created_at > ? ORDER BY created_at LIMIT ?",
            (cutoff, limit),
        ).fetchall()
    return "\n".join(f"[{r['kind']}/{r['role']}] {r['text']}" for r in rows)
