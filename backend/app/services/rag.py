"""ChromaDB retrieval. Two collections:
  knowledge — itinerary + trip notes (rebuilt from the knowledge/ folder)
  archive   — every journal entry and conversation turn (append-only)
"""
from __future__ import annotations

import re

import chromadb

from app import config

_client: chromadb.ClientAPI | None = None


def client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_PATH))
    return _client


def collection(name: str):
    return client().get_or_create_collection(name)


def _chunk_markdown(text: str, source: str) -> list[tuple[str, str, dict]]:
    """Split on ## headings; each chunk keeps its heading for context."""
    parts = re.split(r"(?m)^(?=## )", text)
    chunks = []
    for i, part in enumerate(part for part in parts if part.strip()):
        chunks.append((f"{source}#{i}", part.strip()[:4000], {"source": source}))
    return chunks


def rebuild_knowledge() -> int:
    """Wipe and re-index every .md under knowledge/."""
    try:
        client().delete_collection("knowledge")
    except Exception:
        pass
    coll = collection("knowledge")
    count = 0
    for path in sorted(config.KNOWLEDGE_DIR.rglob("*.md")):
        rel = str(path.relative_to(config.KNOWLEDGE_DIR))
        for cid, text, meta in _chunk_markdown(path.read_text(encoding="utf-8"), rel):
            coll.add(ids=[cid], documents=[text], metadatas=[meta])
            count += 1
    return count


def add_to_archive(doc_id: str, text: str, meta: dict) -> None:
    collection("archive").upsert(ids=[doc_id], documents=[text], metadatas=[meta])


def query(name: str, text: str, n: int = 5) -> list[dict]:
    coll = collection(name)
    if coll.count() == 0:
        return []
    res = coll.query(query_texts=[text], n_results=min(n, coll.count()))
    return [
        {"id": i, "text": d, "meta": m}
        for i, d, m in zip(res["ids"][0], res["documents"][0], res["metadatas"][0])
    ]
