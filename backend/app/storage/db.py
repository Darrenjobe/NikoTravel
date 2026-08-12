"""SQLite storage. Single user, single writer — keep it simple."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',      -- draft | done
    place_name TEXT,
    place_id TEXT,                              -- Google Place ID
    maps_url TEXT,
    lat REAL, lon REAL,
    category TEXT,
    sentiment TEXT,                             -- loved | mixed | skip
    line TEXT,                                  -- one-line verdict
    summary TEXT,
    best TEXT, worst TEXT,
    transcript TEXT NOT NULL DEFAULT '[]'       -- JSON list of {role, text}
);

-- One row per turn. thread_id groups turns into a conversation.
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    kind TEXT NOT NULL,                         -- chat | journal
    role TEXT NOT NULL,                         -- user | assistant
    text TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}',
    thread_id TEXT
);

-- A conversation thread. Ask threads are created by /api/chat; journal
-- threads mirror a journal_entries row so both appear in one history feed.
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                         -- ask | journal
    started_at REAL NOT NULL,
    last_at REAL NOT NULL,
    summary TEXT,                               -- AI-generated; NULL until then
    summarized_at REAL,
    entry_id TEXT                               -- journal threads -> journal_entries.id
);

-- Runtime settings that outlive a restart, so the phone can change them
-- without a redeploy. Currently the chat/job model selection and the cached
-- model catalog; updated_at doubles as the catalog's cache timestamp.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

-- Places hearted on the Map tab. The whole Google payload is denormalized here
-- on purpose: saved pins then render straight from SQLite with no Places call,
-- which is what makes them survive the Mt Athos leg (Sept 20-23, no data).
CREATE TABLE IF NOT EXISTS saved_places (
    place_id TEXT PRIMARY KEY,                  -- Google Place ID
    saved_at REAL NOT NULL,
    name TEXT,
    address TEXT,
    lat REAL, lon REAL,
    category TEXT,
    rating REAL,
    rating_count INTEGER,
    maps_url TEXT,
    note TEXT
);
"""

# Indexes run AFTER _migrate(), because an index over a column that a legacy
# database is still missing would fail before the migration could add it.
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_conversations_thread
    ON conversations (thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_threads_last ON threads (last_at DESC);

CREATE TABLE IF NOT EXISTS guides (
    day TEXT NOT NULL,                          -- YYYY-MM-DD
    kind TEXT NOT NULL,                         -- morning | evening
    created_at REAL NOT NULL,
    payload TEXT NOT NULL,                      -- JSON
    PRIMARY KEY (day, kind)
);

CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    emoji TEXT, text TEXT NOT NULL, tag TEXT
);

CREATE TABLE IF NOT EXISTS preferences (
    kind TEXT NOT NULL,                         -- like | dislike
    label TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (kind, label)
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        _migrate(c)
        c.executescript(INDEXES)


def _migrate(c: sqlite3.Connection) -> None:
    """Additive migrations for databases created before a column existed.

    CREATE TABLE IF NOT EXISTS won't alter an existing table, so a dev database
    from an earlier run needs the new columns added explicitly.
    """
    have = {r["name"] for r in c.execute("PRAGMA table_info(conversations)")}
    if "thread_id" not in have:
        c.execute("ALTER TABLE conversations ADD COLUMN thread_id TEXT")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "transcript" in d and isinstance(d["transcript"], str):
        d["transcript"] = json.loads(d["transcript"])
    return d
