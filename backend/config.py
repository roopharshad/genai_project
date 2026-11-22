"""Runtime configuration, read from environment variables (optionally a .env file)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
# .env (local development) wins over variables inherited from the shell. In a container there
# is no .env file (see .dockerignore), so the platform's environment variables are used.
load_dotenv(ROOT_DIR / ".env", override=True)


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
