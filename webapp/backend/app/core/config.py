import os
import secrets
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR.parent.parent / ".env", override=True)  # project-root .env (local dev only)


def _secret_key() -> str:
    """JWT signing key. Set SECRET_KEY in production; otherwise a random key is generated
    (users are logged out when the server restarts, but tokens can never be forged)."""
    return os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
STORAGE_DIR = BASE_DIR.parent / "storage"

class Settings(BaseModel):
    PROJECT_NAME: str = "DocRestore AI — Legacy UI Asset Restorer"
    API_V1_STR: str = "/api/v1"
    
    # Storage directories
    STORAGE_PATH: Path = STORAGE_DIR
    ORIGINALS_DIR: Path = STORAGE_DIR / "originals"
    RESTORED_DIR: Path = STORAGE_DIR / "restored"
    THUMBNAILS_DIR: Path = STORAGE_DIR / "thumbnails"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    TEMPORARY_DIR: Path = STORAGE_DIR / "temporary"
    CHECKPOINTS_DIR: Path = STORAGE_DIR / "model_checkpoints"
    
    # Database configuration
    # Primary: PostgreSQL. Fallback: SQLite for local dev
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", 
            f"sqlite:///{STORAGE_DIR / 'docrestore.db'}"
        )
    )
    
    # JWT & Auth
    SECRET_KEY: str = Field(default_factory=_secret_key)

    # Seeded administrator account (first start only). Override both in production.
    ADMIN_EMAIL: str = Field(default_factory=lambda: os.getenv("ADMIN_EMAIL", "demo@docrestore.ai"))
    ADMIN_PASSWORD: str = Field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", "docrestore123"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # File upload
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024
    ALLOWED_IMAGE_TYPES: List[str] = ["image/png", "image/jpeg", "image/jpg", "image/pjpeg", "image/webp",
                                      "image/bmp", "image/x-ms-bmp", "image/tiff"]
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".tif", ".tiff"]

settings = Settings()

# Ensure directories exist
for folder in [
    settings.STORAGE_PATH,
    settings.ORIGINALS_DIR,
    settings.RESTORED_DIR,
    settings.THUMBNAILS_DIR,
    settings.REPORTS_DIR,
    settings.TEMPORARY_DIR,
    settings.CHECKPOINTS_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)
