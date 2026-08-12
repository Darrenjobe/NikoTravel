"""AI-generated conversation summaries — the titles on the history screen.

Threads are summarized once they've gone quiet, so we don't burn a model call
after every message. Runs from the background task scheduled by
GET /api/conversations, and from POST /api/jobs/summarize.
"""
from __future__ import annotations

import logging

from app import config
from app.services import archive, llm
from app.storage import db

log = logging.getLogger("hodegos")

IDLE_SECONDS = 600  # a thread is "finished" after 10 quiet minutes
MIN_TURNS = 2

ASK_PROMPT = (
    "Summarize this travel conversation in one sentence, focusing on the "
    "specific topics and places discussed. Write it as a title for a history "
    "list — no preamble, no 'The user asked about'. Example: "
    "'Byzantine history at Mystras and taverna recommendations near the site.'"
)

JOURNAL_PROMPT = (
    "Summarize this journal conversation in one sentence, describing what was "
    "discussed about the place — not just the place's name. Write it as a "
    "title for a history list. Example: 'Disappointing service at Taverna "
    "Klimataria, though the grilled octopus was excellent.'"
)


def pending(limit: int = 10, idle_seconds: int = IDLE_SECONDS) -> list[dict]:
    """Threads that are idle, substantial, and not yet summarized."""
    cutoff = db.now() - idle_seconds
    with db.conn() as c:
        rows = c.execute(
            "SELECT t.id, t.kind FROM threads t "
            "WHERE t.summary IS NULL AND t.last_at < ? "
            "AND (SELECT COUNT(*) FROM conversations WHERE thread_id = t.id) >= ? "
            "ORDER BY t.last_at DESC LIMIT ?",
            (cutoff, MIN_TURNS, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def summarize_thread(thread_id: str, kind: str) -> str | None:
    messages = archive.thread_messages(thread_id)
    if len(messages) < MIN_TURNS:
        return None
    transcript = "\n".join(f"{m['role']}: {m['text']}" for m in messages)
    try:
        summary = llm.get_llm().complete(
            model=config.JOB_MODEL,
            system=JOURNAL_PROMPT if kind == "journal" else ASK_PROMPT,
            prompt=transcript[:20000],
            max_tokens=150,
        ).strip()
    except Exception as exc:  # a failed summary must never break the feed
        log.warning("summary failed for thread %s: %s", thread_id, exc)
        return None
    with db.conn() as c:
        c.execute(
            "UPDATE threads SET summary=?, summarized_at=? WHERE id=?",
            (summary, db.now(), thread_id),
        )
    return summary


def run(limit: int = 10, force: bool = False) -> dict:
    """Summarize idle threads.

    `force` drops the 10-minute idle requirement so a thread you just finished
    typing can be summarized immediately — useful when testing locally.
    """
    idle = 0 if force else IDLE_SECONDS
    candidates = pending(limit, idle_seconds=idle)
    done = [t["id"] for t in candidates if summarize_thread(t["id"], t["kind"])]
    return {
        "summarized": len(done),
        "thread_ids": done,
        "candidates": len(candidates),
    }
