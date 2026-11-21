"""One place for model names, limits and paths. Everything comes from env vars."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
RAW_DIR = DATA_DIR / "raw"
CUTOUT_DIR = DATA_DIR / "cutouts"
DB_PATH = DATA_DIR / "wardrobe.db"
QDRANT_PATH = DATA_DIR / "qdrant"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "gemini-2.5-flash")  # verify current name on AI Studio
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")  # verify current name
MAX_REQUESTS = int(os.getenv("MAX_REQUESTS_PER_RUN", "300"))
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

# Editable: top occasions drive tag vocabulary. Replace with your real top five.
OCCASIONS = ["casual", "college", "office", "festive", "wedding_guest", "party", "engagement_evening"]


def ensure_dirs() -> None:
    for d in (RAW_DIR, CUTOUT_DIR, QDRANT_PATH, RENDER_DIR):
        d.mkdir(parents=True, exist_ok=True)

LAT = float(os.getenv("LAT", "12.97"))
LON = float(os.getenv("LON", "77.59"))
ALLOW_PERSON_PHOTOS = os.getenv("ALLOW_PERSON_PHOTOS", "false").lower() == "true"
TRYON_SPACE = os.getenv("TRYON_SPACE", "yisol/IDM-VTON")
TRYON_QA_THRESHOLD = int(os.getenv("TRYON_QA_THRESHOLD", "3"))
RENDER_DIR = DATA_DIR / "renders"
USER_DIR = DATA_DIR / "user"
KEY_PATH = DATA_DIR / "secret.key"
TRYON_JOBS = DATA_DIR / "tryon_jobs"
TRYON_RESULTS = DATA_DIR / "tryon_results"
OCCASION_FORMALITY = {"casual": 2, "college": 2, "office": 3, "festive": 4, "wedding_guest": 4,
                      "party": 4, "engagement_evening": 5}


def llm_enabled() -> bool:
    return bool(GEMINI_API_KEY) and os.getenv("DISABLE_LLM", "false").lower() != "true"
