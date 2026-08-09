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

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    kind TEXT NOT NULL,                         -- chat | journal
    role TEXT NOT NULL,                         -- user | assistant
    text TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}'
);

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


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "transcript" in d and isinstance(d["transcript"], str):
        d["transcript"] = json.loads(d["transcript"])
    return d
