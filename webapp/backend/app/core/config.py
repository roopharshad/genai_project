import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
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
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "docrestore-ai-super-secret-jwt-key-royal-spectrum-extreme-neon-2026")
    )
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
    ALLOWED_IMAGE_TYPES: List[str] = ["image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"]

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
