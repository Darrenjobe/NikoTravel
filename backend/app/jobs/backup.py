"""Hourly incremental push of the trip archive to Google Drive.

Runs every hour and uploads only what changed. Each journal entry and each Ask
thread becomes one Markdown file, updated in place as it evolves — a journal
entry gains its summary minutes after it is filed, and a thread gains its
title ten minutes after it goes quiet, so "already uploaded" is not the same
as "final". Content is hashed, so a quiet hour costs one Drive token refresh
and nothing else.

The SQLite file rides along less often (GDRIVE_DB_EVERY_HOURS). It is the
restore path; the Markdown is the readable record that outlives the app.

Journal *threads* are skipped on purpose — their transcript is already inside
the entry file, and uploading both would duplicate the whole conversation.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import re

from app import config
from app.services import gdrive
from app.storage import db

log = logging.getLogger("hodegos")

DB_MARKER = "db"


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


def _slug(text: str | None, fallback: str) -> str:
    base = (text or fallback).strip().lower()
    base = re.sub(r"[^\w\s-]", "", base, flags=re.UNICODE)
    base = re.sub(r"[\s_]+", "-", base).strip("-")
    return base[:60] or fallback


def _stamp(epoch: float | None) -> str:
    if not epoch:
        return "unknown-date"
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%d")


def _records() -> dict[str, dict]:
    with db.conn() as c:
        rows = c.execute("SELECT * FROM drive_files").fetchall()
    return {r["local_id"]: dict(r) for r in rows}


def _remember(local_id: str, drive_id: str, checksum: str) -> None:
    with db.conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO drive_files "
            "(local_id, drive_id, checksum, synced_at) VALUES (?,?,?,?)",
            (local_id, drive_id, checksum, db.now()),
        )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _journal_markdown(entry: dict) -> str:
    lines = [
        f"# {entry.get('place_name') or 'Unconfirmed location'}",
        "",
        f"- **Date:** {_stamp(entry.get('created_at'))}",
        f"- **Status:** {entry.get('status')}",
    ]
    for label, key in (("Verdict", "sentiment"), ("One line", "line"),
                       ("Best", "best"), ("Worst", "worst")):
        if entry.get(key):
            lines.append(f"- **{label}:** {entry[key]}")
    if entry.get("maps_url"):
        lines.append(f"- **Maps:** {entry['maps_url']}")
    if entry.get("lat") is not None and entry.get("lon") is not None:
        lines.append(f"- **Coordinates:** {entry['lat']}, {entry['lon']}")
    if entry.get("summary"):
        lines += ["", "## Summary", "", entry["summary"]]

    transcript = entry.get("transcript") or []
    if transcript:
        lines += ["", "## Conversation", ""]
        for turn in transcript:
            who = "Nikos" if turn.get("role") == "assistant" else "Me"
            lines.append(f"**{who}:** {turn.get('text', '')}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _thread_markdown(thread: dict, messages: list[dict]) -> str:
    title = thread.get("summary") or "Conversation"
    lines = [
        f"# {title}",
        "",
        f"- **Started:** {_stamp(thread.get('started_at'))}",
        f"- **Turns:** {len(messages)}",
        "",
    ]
    for m in messages:
        who = "Nikos" if m["role"] == "assistant" else "Me"
        lines.append(f"**{who}:** {m['text']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Job
# --------------------------------------------------------------------------

def run(force: bool = False, limit: int = 500) -> dict:
    """Push anything new or changed. `force` re-uploads even if unchanged."""
    if not gdrive.configured():
        return {
            "skipped": "Google Drive is not configured "
            "(GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN).",
            "uploaded": 0,
        }

    known = _records()
    uploaded, unchanged, errors = [], 0, []

    def push(local_id: str, name: str, body: str, mime: str = "text/markdown"):
        nonlocal unchanged
        data = body.encode("utf-8") if isinstance(body, str) else body
        checksum = _checksum(data)
        prior = known.get(local_id)
        if prior and prior["checksum"] == checksum and not force:
            unchanged += 1
            return
        try:
            drive_id = gdrive.upsert(
                name, data, mime, prior["drive_id"] if prior else None
            )
        except gdrive.DriveError as exc:
            # One bad file must not abort the run — the next hour retries it.
            log.warning("Drive push failed for %s: %s", local_id, exc)
            errors.append(f"{local_id}: {exc}")
            return
        _remember(local_id, drive_id, checksum)
        uploaded.append(name)

    with db.conn() as c:
        entries = [
            db.row_to_dict(r)
            for r in c.execute(
                "SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]
        threads = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM threads WHERE kind='ask' "
                "ORDER BY last_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]

    for entry in entries:
        name = (
            f"{_stamp(entry.get('created_at'))}-"
            f"{_slug(entry.get('place_name'), entry['id'])}.md"
        )
        push(f"journal:{entry['id']}", name, _journal_markdown(entry))

    for thread in threads:
        with db.conn() as c:
            messages = [
                dict(r)
                for r in c.execute(
                    "SELECT role, text, created_at FROM conversations "
                    "WHERE thread_id=? ORDER BY created_at",
                    (thread["id"],),
                ).fetchall()
            ]
        if not messages:
            continue
        name = (
            f"{_stamp(thread.get('started_at'))}-ask-"
            f"{_slug(thread.get('summary'), thread['id'])}.md"
        )
        push(f"thread:{thread['id']}", name, _thread_markdown(thread, messages))

    # SQLite snapshot — the restore path, so it does not need to be hourly.
    prior_db = known.get(DB_MARKER)
    due = (
        force
        or not prior_db
        or db.now() - prior_db["synced_at"] > config.GDRIVE_DB_EVERY_HOURS * 3600
    )
    if due and config.DB_PATH.is_file():
        push(
            DB_MARKER,
            "hodegos.db",
            config.DB_PATH.read_bytes(),
            "application/x-sqlite3",
        )

    return {
        "uploaded": len(uploaded),
        "files": uploaded[:20],
        "unchanged": unchanged,
        "errors": errors,
        "folder": gdrive.folder_link(),
    }
