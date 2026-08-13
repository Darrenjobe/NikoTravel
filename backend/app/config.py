import os
from pathlib import Path

# Paths — DATA_DIR must live on the Render persistent disk in production.
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Load backend/.env into the environment if it exists.

    Deliberately dependency-free and deliberately non-overriding: real
    environment variables always win, so Render's dashboard config is never
    shadowed by a stray .env baked into an image. Without this, the server
    only sees your keys if you `source .env` in the *same* shell that launches
    uvicorn — a new terminal tab silently starts an unconfigured server.

    Inline comments are NOT stripped: `KEY=abc # note` yields "abc # note".
    Keep comments on their own line so a '#' inside a secret survives intact.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        # Real env vars win — only fill in what the platform didn't set.
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
KNOWLEDGE_DIR = Path(os.environ.get("KNOWLEDGE_DIR", REPO_DIR / "knowledge"))
DB_PATH = DATA_DIR / "hodegos.db"
CHROMA_PATH = DATA_DIR / "chroma"

# Auth — single-user static bearer token. Generate with: openssl rand -hex 32
API_TOKEN = os.environ.get("API_TOKEN", "")

# LLM. Default provider is Anthropic; set LLM_PROVIDER=openai to swap.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")
# Starting point only — these are the *fallbacks*. A selection made through
# POST /api/models is stored in SQLite and wins over both of these, so the
# model can be changed from the phone without an env var or a redeploy.
#
# Sonnet 5 is the default because it is the sensible place to sit for a trip's
# worth of usage: chat runs on demand, and four cron jobs a day each generate
# real content. Move CHAT_MODEL up to claude-opus-5 when depth matters more
# than spend, or down to claude-haiku-4-5 when it doesn't.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-5")
JOB_MODEL = os.environ.get("JOB_MODEL", "claude-sonnet-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# External services
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# Text to speech (ElevenLabs).
#
# VOICE and MODEL are separate things and easy to conflate: the 20-character
# ID is the *voice*, while the model is a slug like eleven_flash_v2_5. Sending
# a voice id as model_id is rejected by the API.
#
# The default voice is a Greek speaker who handles English too, which is why
# the system prompt asks for Greek place names in Greek script — the
# characters are what drive correct pronunciation.
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# TTS_VOICE_ID = os.environ.get("TTS_VOICE_ID", "QnPbsq4pmOZkrE4RQQCA")
TTS_VOICE_ID = os.environ.get("TTS_VOICE_ID", "0ZJ6CiTzPB5e41TNRP12")
TTS_MODEL = os.environ.get("TTS_MODEL", "eleven_flash_v2_5")
TTS_OUTPUT_FORMAT = os.environ.get("TTS_OUTPUT_FORMAT", "mp3_44100_128")
# Synthesis costs credits, so results are cached on the persistent disk and
# the oldest are evicted past this ceiling.
TTS_CACHE_MB = int(os.environ.get("TTS_CACHE_MB", "500"))
TTS_MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "5000"))

# Google Drive backup.
#
# A service account will NOT work on a personal Google account: it gets its
# own Drive identity with zero storage quota, so uploads into a folder you
# shared with it fail with "storage quota exceeded". An OAuth refresh token
# makes the server act as you, so files are yours and use your quota.
# scripts/google_auth.py walks through getting one.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "")
# Optional. Left blank, the app creates and owns its own folder, which keeps
# the drive.file scope sufficient — it can then never see the rest of Drive.
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")
GDRIVE_FOLDER_NAME = os.environ.get("GDRIVE_FOLDER_NAME", "Ὁδηγός Trip Archive")
# The SQLite snapshot is for restore, not reading, so it does not need to ride
# along every hour.
GDRIVE_DB_EVERY_HOURS = int(os.environ.get("GDRIVE_DB_EVERY_HOURS", "20"))

# Trip
TRIP_YEAR = int(os.environ.get("TRIP_YEAR", "2026"))
TRIP_TZ = os.environ.get("TRIP_TZ", "Europe/Athens")
def _find_itinerary() -> Path:
    """Locate the itinerary that drives date→region and stop parsing.

    Every other file in knowledge/ is picked up by the RAG glob, but this one
    is also parsed structurally, so it has to be found by path. Renaming it
    would otherwise break /api/today and /api/itinerary silently while the
    concierge kept answering — hence the fallback.
    """
    explicit = os.environ.get("ITINERARY_FILE")
    if explicit:
        return Path(explicit)
    default = KNOWLEDGE_DIR / "itinerary" / "greece-spiritual-historical-tour.md"
    if default.is_file():
        return default
    candidates = sorted((KNOWLEDGE_DIR / "itinerary").glob("*.md"))
    return candidates[0] if candidates else default


ITINERARY_FILE = _find_itinerary()

DATA_DIR.mkdir(parents=True, exist_ok=True)
