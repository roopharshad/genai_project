"""Shared image validation and helpers."""
import io
import secrets
import shutil
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .. import config

ALLOWED_IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
Image.MAX_IMAGE_PIXELS = 40_000_000  # guard against decompression bombs


class ValidationError(ValueError):
    """Raised for user-correctable input problems (maps to HTTP 400/413)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def new_job_dir() -> tuple[str, Path]:
    job_id = time.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(4)
    path = config.JOBS_DIR / job_id
    path.mkdir(parents=True)
    return job_id, path


def check_size(data: bytes) -> None:
    if not data:
        raise ValidationError("The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValidationError(f"File is larger than the {config.MAX_UPLOAD_MB} MB limit.", 413)


def load_image(data: bytes) -> tuple[Image.Image, str]:
    """Validate bytes as a JPG/PNG/WEBP image. Returns (image, extension)."""
    check_size(data)
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("The file is not a readable image.") from exc
    if img.format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Unsupported format. Please upload a JPG, JPEG, PNG or WEBP image.")
    ext = ALLOWED_IMAGE_FORMATS[img.format]
    img = ImageOps.exif_transpose(img)
    return img, ext


def to_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def fit_for_processing(img: Image.Image) -> tuple[Image.Image, bool]:
    longest = max(img.size)
    if longest <= config.MAX_PROCESS_SIDE:
        return img, False
    scale = config.MAX_PROCESS_SIDE / longest
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS), True


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def describe(path: Path) -> dict:
    with Image.open(path) as im:
        return {"width": im.width, "height": im.height, "size": path.stat().st_size}


def cleanup_old_jobs() -> int:
    cutoff = time.time() - config.RETENTION_HOURS * 3600
    removed = 0
    for d in config.JOBS_DIR.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed
