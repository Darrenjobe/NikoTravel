"""Text to speech via ElevenLabs.

Two jobs beyond calling the API. First, the model writes for a screen —
markdown, bullets, the occasional emoji — and a speech engine reads all of
that literally. `speakable()` strips it. Second, synthesis costs credits per
character, so identical text is cached on the persistent disk: replaying this
morning's guide should be free.

Greek script is deliberately preserved. The configured voice is a Greek
speaker, and the Greek characters are what produce correct pronunciation of
place names — stripping them to ASCII would defeat the reason for the voice.
"""
from __future__ import annotations

import hashlib
import logging
import re

import httpx

from app import config

log = logging.getLogger("hodegos")

API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
CACHE_DIR = config.DATA_DIR / "tts"


class TTSError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Making model output speakable
# --------------------------------------------------------------------------

_CODE_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HEADING = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]*")
_BLOCKQUOTE = re.compile(r"(?m)^[ \t]{0,3}>[ \t]?")
_LIST_MARK = re.compile(r"(?m)^[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]+")
_RULE = re.compile(r"(?m)^[ \t]*(?:[-*_][ \t]*){3,}$")
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})(\S.*?\S|\S)\1", re.S)
_TABLE_ROW = re.compile(r"(?m)^[ \t]*\|(.+)\|[ \t]*$")
_TABLE_SEP = re.compile(r"(?m)^[ \t]*\|[ \t:|-]+\|[ \t]*$")
_BLANK_RUN = re.compile(r"\n{3,}")
_SPACE_RUN = re.compile(r"[ \t]{2,}")

# Pictographs and dingbats only. Deliberately does NOT touch U+1F00–U+1FFF,
# which is Greek Extended — Ὁδηγός itself lives there, and confusing it with
# the U+1F300+ emoji planes would mangle exactly the text this exists to
# pronounce correctly.
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF]+"
)


def speakable(text: str) -> str:
    """Flatten markdown and drop glyphs a voice engine would read aloud."""
    out = _CODE_FENCE.sub(" ", text)
    out = _IMAGE.sub(" ", out)
    out = _LINK.sub(r"\1", out)          # keep the label, drop the URL
    out = _INLINE_CODE.sub(r"\1", out)
    out = _TABLE_SEP.sub("", out)
    out = _TABLE_ROW.sub(lambda m: m.group(1).replace("|", ", ").strip(), out)
    out = _RULE.sub("", out)
    out = _HEADING.sub("", out)
    out = _BLOCKQUOTE.sub("", out)
    out = _LIST_MARK.sub("", out)
    out = _EMPHASIS.sub(r"\2", out)
    out = _EMOJI.sub("", out)
    out = _SPACE_RUN.sub(" ", out)
    out = _BLANK_RUN.sub("\n\n", out)
    return out.strip()


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------

def _cache_key(text: str, voice_id: str, model_id: str, fmt: str) -> str:
    digest = hashlib.sha256(
        "\x00".join((text, voice_id, model_id, fmt)).encode("utf-8")
    ).hexdigest()
    return digest[:32]


def _cache_path(key: str):
    return CACHE_DIR / f"{key}.mp3"


def _evict_if_needed() -> None:
    """Keep the cache under TTS_CACHE_MB, oldest-first.

    Audio is regenerable, so evicting is cheap; filling a 5GB disk that also
    holds the journal would not be.
    """
    limit = config.TTS_CACHE_MB * 1024 * 1024
    files = sorted(CACHE_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    while files and total > limit:
        victim = files.pop(0)
        total -= victim.stat().st_size
        victim.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Synthesis
# --------------------------------------------------------------------------

def synthesize(
    text: str,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> tuple[bytes, bool]:
    """Return (mp3_bytes, from_cache). Raises TTSError with a usable message."""
    if not config.ELEVENLABS_API_KEY:
        raise TTSError(
            "ELEVENLABS_API_KEY is not set on the server. Add it to "
            "backend/.env (or the Render dashboard) and restart — see the "
            "startup log for what the server loaded."
        )
    spoken = speakable(text)
    if not spoken:
        raise TTSError("Nothing speakable in that text.")
    if len(spoken) > config.TTS_MAX_CHARS:
        raise TTSError(
            f"Text is {len(spoken)} characters after cleanup; the limit is "
            f"{config.TTS_MAX_CHARS}. Split it and request each part."
        )

    voice = voice_id or config.TTS_VOICE_ID
    model = model_id or config.TTS_MODEL
    fmt = config.TTS_OUTPUT_FORMAT

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(_cache_key(spoken, voice, model, fmt))
    if path.is_file():
        path.touch()  # keep recently played audio out of the eviction window
        return path.read_bytes(), True

    try:
        r = httpx.post(
            f"{API_URL}/{voice}",
            params={"output_format": fmt},
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={"text": spoken, "model_id": model},
            timeout=60,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # ElevenLabs explains itself in the body; surfacing it turns "500" into
        # "that voice id doesn't exist" or "quota exceeded".
        detail = exc.response.text[:400]
        log.warning("ElevenLabs %s: %s", exc.response.status_code, detail)
        raise TTSError(
            f"ElevenLabs returned {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise TTSError(f"Could not reach ElevenLabs: {exc}") from exc

    audio = r.content
    path.write_bytes(audio)
    _evict_if_needed()
    return audio, False


def voices() -> list[dict]:
    """Available voices, for picking one other than the default."""
    if not config.ELEVENLABS_API_KEY:
        raise TTSError("ELEVENLABS_API_KEY is not set on the server.")
    try:
        r = httpx.get(
            "https://api.elevenlabs.io/v2/voices",
            headers={"xi-api-key": config.ELEVENLABS_API_KEY},
            params={"page_size": 100},
            timeout=30,
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise TTSError(f"Could not list voices: {exc}") from exc
    return [
        {
            "voice_id": v.get("voice_id"),
            "name": v.get("name"),
            "labels": v.get("labels") or {},
            "preview_url": v.get("preview_url"),
            "is_default": v.get("voice_id") == config.TTS_VOICE_ID,
        }
        for v in r.json().get("voices", [])
    ]
