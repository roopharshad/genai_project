"""Runtime configuration, read from environment variables (optionally a .env file)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


# Remote restoration service (internal detail, never exposed to the UI).
RESTORATION_SPACE_URL = os.getenv(
    "RESTORATION_SPACE_URL", "https://randomtable-image-restoration-gfpgan.hf.space"
).rstrip("/")
# Optional Hugging Face token for private / rate-limited Spaces.
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
RESTORATION_TIMEOUT_SECONDS = _int("RESTORATION_TIMEOUT_SECONDS", 300)

MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 10)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
# Images larger than this (longest side, px) are downscaled before remote processing.
MAX_PROCESS_SIDE = _int("MAX_PROCESS_SIDE", 1600)
# Finished jobs older than this are removed at startup.
RETENTION_HOURS = _int("RETENTION_HOURS", 72)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", ROOT_DIR / "storage"))
JOBS_DIR = STORAGE_DIR / "jobs"
DB_PATH = STORAGE_DIR / "docrestore.sqlite3"
FRONTEND_DIR = ROOT_DIR / "frontend"

JOBS_DIR.mkdir(parents=True, exist_ok=True)
