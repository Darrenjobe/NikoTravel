"""The model catalog — which models this app can actually run on.

Anthropic's Models API is the source of truth for what exists and what each
model supports, but it is a network call and the answer changes maybe a few
times a year. So the result is cached in SQLite with a long TTL: the settings
screen opens instantly, the trip doesn't spend requests re-asking, and a
manual refresh is always one flag away.
"""
from __future__ import annotations

import json
import logging
import time

from app import config
from app.services import settings

log = logging.getLogger("hodegos")

CATALOG_KEY = "model_catalog"
TTL_SECONDS = 24 * 60 * 60

# Shown when the catalog can't be fetched — no key, no signal, or the SDK is
# too old to expose models.list(). Better a usable picker than an empty one,
# and `source` in the response says plainly that this is not live data.
FALLBACK = [
    {"id": "claude-opus-5", "display_name": "Claude Opus 5"},
    {"id": "claude-sonnet-5", "display_name": "Claude Sonnet 5"},
    {"id": "claude-haiku-4-5", "display_name": "Claude Haiku 4.5"},
]


def _supported(caps: dict, *path: str) -> bool:
    """Read a capability leaf defensively.

    The capability tree is untyped and grows over time; a KeyError here would
    take down the settings screen over a field we only use for a badge.
    """
    node: object = caps
    for part in path:
        if not isinstance(node, dict):
            return False
        node = node.get(part, {})
    return bool(isinstance(node, dict) and node.get("supported"))


def _describe(model) -> dict:
    """One catalog entry from a Models API record.

    `compatible` is the load-bearing field: the concierge needs tool use and
    the journal extractor needs structured outputs, so a model without them
    would fail at the worst possible moment rather than at selection time.
    """
    caps = getattr(model, "capabilities", None) or {}
    structured = _supported(caps, "structured_outputs")
    return {
        "id": model.id,
        "display_name": getattr(model, "display_name", None) or model.id,
        # The Models API reports max_input_tokens / max_tokens; there is no
        # `context_window` field, despite the name being the obvious guess.
        "max_input_tokens": getattr(model, "max_input_tokens", None),
        "max_output_tokens": getattr(model, "max_tokens", None),
        "structured_outputs": structured,
        "vision": _supported(caps, "image_input"),
        "adaptive_thinking": _supported(caps, "thinking", "types", "adaptive"),
        "compatible": structured,
        "incompatible_reason": (
            None if structured
            else "No structured outputs — journal extraction would fail."
        ),
    }


def _fetch() -> list[dict]:
    """Live catalog from the Anthropic Models API."""
    import anthropic

    client = anthropic.Anthropic()
    # Iterate the page object directly — it auto-paginates. Reading .data
    # would silently return only the first page.
    return [_describe(m) for m in client.models.list()]


def catalog(refresh: bool = False) -> dict:
    """Available models, cached for a day.

    Returns `source` so the caller can tell live data from a stale cache or
    the built-in fallback — a picker that silently shows hardcoded defaults
    when the key is missing is worse than one that says so.
    """
    cached, fetched_at = settings.get_with_time(CATALOG_KEY)
    age = (time.time() - fetched_at) if fetched_at else None
    fresh_enough = cached and age is not None and age < TTL_SECONDS

    if fresh_enough and not refresh:
        return {
            "models": json.loads(cached),
            "source": "cache",
            "fetched_at": fetched_at,
            "age_seconds": int(age),
        }

    if config.LLM_PROVIDER != "anthropic":
        return {"models": FALLBACK, "source": "fallback",
                "note": f"Model listing is Anthropic-only; provider is {config.LLM_PROVIDER}."}

    try:
        models = _fetch()
    except Exception as exc:
        log.warning("model catalog fetch failed: %s", exc)
        if cached:
            # A stale cache still beats the fallback: it is real data for this
            # account, just older than the TTL.
            return {
                "models": json.loads(cached),
                "source": "stale-cache",
                "fetched_at": fetched_at,
                "age_seconds": int(age) if age is not None else None,
                "note": f"Refresh failed ({exc.__class__.__name__}); serving the last good catalog.",
            }
        return {"models": FALLBACK, "source": "fallback",
                "note": f"Could not reach the Models API ({exc.__class__.__name__}). "
                        "Check ANTHROPIC_API_KEY in the startup log."}

    settings.set(CATALOG_KEY, json.dumps(models))
    return {"models": models, "source": "live", "fetched_at": time.time(), "age_seconds": 0}


def known_ids(models: list[dict]) -> set[str]:
    return {m["id"] for m in models}
