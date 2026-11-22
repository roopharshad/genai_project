import os
import uuid
import shutil
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from fastapi import UploadFile, HTTPException
from app.core.config import settings

class FileStorageService:
    @staticmethod
    def _is_safe_path(target_path: Path, base_dir: Path) -> bool:
        """Prevent path traversal attacks."""
        try:
            target_path.resolve().relative_to(base_dir.resolve())
            return True
        except ValueError:
            return False

    @classmethod
    def save_uploaded_original(cls, file: UploadFile) -> Tuple[str, int, int, int, str]:
        """
        Validate and save an uploaded original image.
        Returns: (stored_filename, file_size, width, height, mime_type)
        """
        # Validate type by MIME or extension (browsers report .jpg as image/jpeg, image/jpg,
        # image/pjpeg or application/octet-stream). The Pillow decode below is the real check.
        ext = Path(file.filename or "image.png").suffix.lower()
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES and ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PNG, JPG/JPEG, WebP, BMP, TIFF."
            )

        # Generate unique secure filename
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            ext = ".png"
        stored_filename = f"orig_{uuid.uuid4().hex}{ext}"
        destination = settings.ORIGINALS_DIR / stored_filename

        # Write file and check size
        file.file.seek(0)
        file_size = 0
        with open(destination, "wb") as buffer:
            chunk = file.file.read(1024 * 64)
            while chunk:
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if destination.exists():
                        destination.unlink()
                    raise HTTPException(status_code=400, detail="File size exceeds 25 MB limit.")
                buffer.write(chunk)
                chunk = file.file.read(1024 * 64)

        # Validate with PIL image decoder
        try:
            with Image.open(destination) as img:
                width, height = img.size
                img.verify()
        except Exception as e:
            if destination.exists():
                destination.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid or corrupted image file: {str(e)}")

        # Create thumbnail
        cls.generate_thumbnail(destination, stored_filename)

        return stored_filename, file_size, width, height, file.content_type

    @classmethod
    def generate_thumbnail(cls, image_path: Path, filename: str, max_size: Tuple[int, int] = (280, 280)) -> Optional[str]:
        """Generate thumbnail for UI previews."""
        try:
            thumb_filename = f"thumb_{filename}"
            thumb_path = settings.THUMBNAILS_DIR / thumb_filename
            with Image.open(image_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
                # Convert RGBA to RGB if saving to JPEG or keep format
                if img_copy.mode in ("RGBA", "LA") and thumb_path.suffix.lower() in [".jpg", ".jpeg"]:
                    bg = Image.new("RGB", img_copy.size, (255, 255, 255))
                    bg.paste(img_copy, mask=img_copy.split()[3])
                    bg.save(thumb_path)
                else:
                    img_copy.save(thumb_path)
            return thumb_filename
        except Exception:
            return None

    @classmethod
    def save_restored_image(cls, image: Image.Image, format: str = "PNG") -> Tuple[str, int, int, int]:
        """
        Save a restored image output separately.
        Returns: (stored_filename, file_size, width, height)
        """
        ext = f".{format.lower()}"
        stored_filename = f"rest_{uuid.uuid4().hex}{ext}"
        destination = settings.RESTORED_DIR / stored_filename

        image.save(destination, format=format)
        file_size = destination.stat().st_size
        width, height = image.size

        # Generate thumbnail
        cls.generate_thumbnail(destination, stored_filename)

        return stored_filename, file_size, width, height

    @classmethod
    def get_file_path(cls, filename: str) -> Optional[Path]:
        """Safely retrieve file path across storage subfolders."""
        for folder in [settings.ORIGINALS_DIR, settings.RESTORED_DIR, settings.THUMBNAILS_DIR, settings.REPORTS_DIR]:
            path = folder / filename
            if path.exists() and cls._is_safe_path(path, folder):
                return path
        return None

    @classmethod
    def delete_asset_file(cls, filename: str) -> bool:
        """Safely delete asset file and thumbnail."""
        deleted = False
        for folder in [settings.ORIGINALS_DIR, settings.RESTORED_DIR, settings.THUMBNAILS_DIR]:
            path = folder / filename
            if path.exists() and cls._is_safe_path(path, folder):
                try:
                    path.unlink()
                    deleted = True
                except Exception:
                    pass
            # Also check thumbnail
            thumb_path = settings.THUMBNAILS_DIR / f"thumb_{filename}"
            if thumb_path.exists() and cls._is_safe_path(thumb_path, settings.THUMBNAILS_DIR):
                try:
                    thumb_path.unlink()
                except Exception:
                    pass
        return deleted

