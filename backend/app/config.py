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
# Chat needs snappy answers on the go; jobs can take their time.
# claude-opus-5 is the recommended default; drop CHAT_MODEL to
# claude-haiku-4-5 if on-the-ground latency matters more than depth.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "claude-opus-5")
JOB_MODEL = os.environ.get("JOB_MODEL", "claude-opus-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# External services
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

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
