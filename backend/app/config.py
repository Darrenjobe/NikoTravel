import os
from pathlib import Path

# Paths — DATA_DIR must live on the Render persistent disk in production.
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
KNOWLEDGE_DIR = Path(os.environ.get("KNOWLEDGE_DIR", REPO_DIR / "knowledge"))
DB_PATH = DATA_DIR / "niko.db"
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
ITINERARY_FILE = KNOWLEDGE_DIR / "itinerary" / "greece-spiritual-historical-tour.md"

DATA_DIR.mkdir(parents=True, exist_ok=True)
