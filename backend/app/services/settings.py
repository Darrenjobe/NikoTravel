"""Runtime settings — env-var defaults that the app can override at runtime.

config.py values are read once at import, so changing a model used to mean an
env-var edit and a restart. These helpers layer a persisted override on top:
the stored value wins, the env var is the fallback, and nothing needs a
redeploy. Reads hit SQLite directly rather than caching in-process, because
background jobs run in the same process as the request that changed the
setting and a stale memo would silently keep the old model alive.
"""
from __future__ import annotations

from app import config
from app.storage import db


def get(key: str) -> str | None:
    with db.conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def get_with_time(key: str) -> tuple[str | None, float | None]:
    """Value plus when it was written — used for the catalog's cache age."""
    with db.conn() as c:
        row = c.execute(
            "SELECT value, updated_at FROM settings WHERE key=?", (key,)
        ).fetchone()
    return (row["value"], row["updated_at"]) if row else (None, None)


def set(key: str, value: str) -> None:
    with db.conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, db.now()),
        )


def clear(key: str) -> None:
    """Drop an override so the env-var default applies again."""
    with db.conn() as c:
        c.execute("DELETE FROM settings WHERE key=?", (key,))


def chat_model() -> str:
    return get("chat_model") or config.CHAT_MODEL


def job_model() -> str:
    return get("job_model") or config.JOB_MODEL
