"""Asset recovery: extract real visual assets from legacy files.

Supported inputs
- Office / archive files (.docx .pptx .xlsx .odt .odp .zip): embedded images are extracted.
- Markup (.html .htm .css .svg): base64 data-URI images are decoded.
- Screenshots / sprite sheets (.png .jpg .jpeg .webp): separate visual elements are cropped
  by detecting regions that differ from the dominant background colour.

Categories are derived from measurable properties (size and aspect ratio), not guessed meaning.
"""
import base64
import io
import re
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from .image_utils import ValidationError, check_size, load_image

ARCHIVE_EXT = {".docx", ".pptx", ".xlsx", ".odt", ".odp", ".ods", ".zip"}
MARKUP_EXT = {".html", ".htm", ".css", ".svg"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
EMBEDDED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
MAX_ASSETS = 200
DATA_URI = re.compile(rb"data:image/(png|jpe?g|gif|webp|bmp);base64,([A-Za-z0-9+/=\s]+)")


def categorize(w: int, h: int) -> str:
    ratio = w / h if h else 1
    if max(w, h) <= 64:
        return "Icon"
    if ratio >= 2.5 and h <= 120:
        return "Button / Bar"
    if ratio >= 2.5:
        return "Banner"
    if max(w, h) <= 256:
        return "Graphic"
    return "Image"


def _save(img: Image.Image, out_dir: Path, idx: int, source: str) -> dict:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    name = f"asset_{idx:03d}.png"
    img.save(out_dir / name, "PNG")
    return {"name": name, "source": source, "width": img.width, "height": img.height,
            "size": (out_dir / name).stat().st_size, "category": categorize(img.width, img.height)}


def _open_bytes(raw: bytes):
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        return im
    except Exception:  # noqa: BLE001 - skip unreadable embedded files
        return None


def _from_archive(data: bytes, out_dir: Path) -> list:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValidationError("The archive could not be opened.") from exc
    assets = []
    for info in zf.infolist():
        if len(assets) >= MAX_ASSETS:
            break
        if info.is_dir() or Path(info.filename).suffix.lower() not in EMBEDDED_IMAGE_EXT:
            continue
        if info.file_size > 25 * 1024 * 1024:
            continue
        im = _open_bytes(zf.read(info))
        if im:
            assets.append(_save(im, out_dir, len(assets) + 1, info.filename))
    return assets


def _from_markup(data: bytes, out_dir: Path) -> list:
    assets = []
    for m in DATA_URI.finditer(data):
        if len(assets) >= MAX_ASSETS:
            break
        try:
            raw = base64.b64decode(re.sub(rb"\s", b"", m.group(2)))
        except ValueError:
            continue
        im = _open_bytes(raw)
        if im:
            assets.append(_save(im, out_dir, len(assets) + 1, f"embedded data URI #{len(assets) + 1}"))
    return assets


def _label(mask: np.ndarray):
    """Connected components (8-way) on a downsampled mask; returns bounding boxes."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    boxes = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        y1 = y2 = y0
        x1 = x2 = x0
        while stack:
            y, x = stack.pop()
            y1, y2, x1, x2 = min(y1, y), max(y2, y), min(x1, x), max(x2, x)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        boxes.append((x1, y1, x2 + 1, y2 + 1))
    return boxes


def _from_screenshot(data: bytes, out_dir: Path) -> list:
    img, _ = load_image(data)
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).astype(np.int16)
    # Background = most common colour along the border.
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    colors, counts = np.unique(border.reshape(-1, 4), axis=0, return_counts=True)
    bg = colors[counts.argmax()]
    diff = np.abs(arr - bg).max(axis=2) > 24
    if bg[3] < 16:
        diff = arr[..., 3] > 16

    # Work on a reduced grid for speed, dilating so nearby parts of one element merge.
    step = max(1, max(img.size) // 400)
    small = diff[::step, ::step]
    pad = 2
    dil = np.zeros_like(small)
    for dy in range(-pad, pad + 1):
        for dx in range(-pad, pad + 1):
            dil |= np.roll(np.roll(small, dy, 0), dx, 1)

    assets = []
    min_side = max(8, min(img.size) // 60)
    boxes = sorted(_label(dil), key=lambda b: (b[1], b[0]))
    for x1, y1, x2, y2 in boxes:
        X1, Y1 = max(0, x1 * step - step), max(0, y1 * step - step)
        X2, Y2 = min(img.width, x2 * step + step), min(img.height, y2 * step + step)
        if X2 - X1 < min_side or Y2 - Y1 < min_side:
            continue
        if (X2 - X1) * (Y2 - Y1) > 0.9 * img.width * img.height:
            continue
        assets.append(_save(rgba.crop((X1, Y1, X2, Y2)), out_dir, len(assets) + 1, f"region {X1},{Y1} {X2 - X1}x{Y2 - Y1}"))
        if len(assets) >= MAX_ASSETS:
            break
    return assets


def recover(data: bytes, filename: str, out_dir: Path) -> tuple[str, list]:
    check_size(data)
    ext = Path(filename or "").suffix.lower()
    if ext in ARCHIVE_EXT:
        return "Embedded files", _from_archive(data, out_dir)
    if ext in MARKUP_EXT:
        return "Embedded data", _from_markup(data, out_dir)
    if ext in IMAGE_EXT:
        return "Screenshot regions", _from_screenshot(data, out_dir)
    raise ValidationError(
        "Unsupported file. Upload a screenshot (PNG/JPG/WEBP), an Office document "
        "(DOCX/PPTX/XLSX), a ZIP archive, or an HTML/CSS/SVG file."
    )
