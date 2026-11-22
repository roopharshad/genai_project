"""Conservative LaMa repair for interior paper defects.

LaMa is never allowed to generate pixels in or near detected text/handwriting. The generated
image is composited only through the supplied defect mask; all other pixels stay byte-identical.
"""
import os
import threading

import cv2
import numpy as np
from PIL import Image

from .. import config

WEIGHT = config.ROOT_DIR / "models" / "lama" / "big-lama.pt"
_model = None
_lock = threading.Lock()
_error = None


def available() -> tuple[bool, str]:
    global _error
    if not WEIGHT.is_file() or WEIGHT.stat().st_size < 190_000_000:
        return False, "missing or incomplete big-lama.pt"
    if _error is None:
        try:
            from simple_lama_inpainting import SimpleLama  # noqa: F401
            _error = ""
        except Exception as exc:  # noqa: BLE001
            _error = f"{type(exc).__name__}: {exc}"
    return _error == "", _error or "ok"


def _lama_worker(conn, image_bytes: bytes, mask_bytes: bytes):
    """Load LaMa in an isolated process so all model memory is returned before DocRes runs."""
    import io
    try:
        os.environ["LAMA_MODEL"] = str(WEIGHT)
        from simple_lama_inpainting import SimpleLama
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
        result = SimpleLama()(image, mask)
        out = io.BytesIO()
        result.save(out, "PNG")
        conn.send(("ok", out.getvalue()))
    except Exception as exc:  # noqa: BLE001
        conn.send(("err", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()


def defect_mask(img: Image.Image, protect: np.ndarray) -> np.ndarray:
    """Detect only large interior paper anomalies; reject lines, page borders and protected ink."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    h, w = rgb.shape[:2]
    smooth = cv2.medianBlur(rgb, 31)
    delta = np.linalg.norm(rgb.astype(np.float32) - smooth.astype(np.float32), axis=2)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    local = cv2.medianBlur(gray, 31).astype(np.float32)
    score = delta + 0.6 * np.abs(gray.astype(np.float32) - local)
    threshold = max(28.0, float(np.percentile(score, 98.5)))
    raw = score > threshold
    margin = max(8, round(min(h, w) * 0.018))
    raw[:margin] = raw[-margin:] = False
    raw[:, :margin] = raw[:, -margin:] = False
    safe = ~cv2.dilate(protect.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
    raw &= safe
    raw = cv2.morphologyEx(raw.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw, 8)
    keep = np.zeros(n, bool)
    min_area = max(36, int(h * w * 0.00015))
    max_area = int(h * w * 0.04)
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        # Exclude thin fold/pen-like structures. LaMa is for holes, tears and isolated blotches.
        if min_area <= area <= max_area and min(cw, ch) >= 5 and max(cw, ch) / max(1, min(cw, ch)) < 8:
            keep[i] = True
    mask = keep[labels]
    mask &= safe
    return cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) * 255


def inpaint(img: Image.Image, mask: np.ndarray) -> Image.Image:
    """Run LaMa on an explicit mask (uint8 0/255 or bool). Only masked pixels change."""
    import io
    import multiprocessing as mp
    mask = (np.asarray(mask) > 0).astype(np.uint8) * 255
    if not mask.any():
        return img.copy()
    ok, why = available()
    if not ok:
        raise RuntimeError(f"LaMa unavailable: {why}")
    image_buf, mask_buf = io.BytesIO(), io.BytesIO()
    img.convert("RGB").save(image_buf, "PNG")
    Image.fromarray(mask).save(mask_buf, "PNG")
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(False)
    proc = ctx.Process(target=_lama_worker, args=(child, image_buf.getvalue(), mask_buf.getvalue()),
                       name="docrestore-lama")
    proc.start()
    if not parent.poll(int(os.getenv("LAMA_TIMEOUT_SECONDS", "180"))):
        proc.kill()
        proc.join()
        raise RuntimeError("LaMa worker timed out")
    status, payload = parent.recv()
    proc.join()
    if status != "ok":
        raise RuntimeError(f"LaMa worker failed: {payload}")
    gen = np.asarray(Image.open(io.BytesIO(payload)).convert("RGB").crop((0, 0, img.width, img.height)))
    out = np.asarray(img.convert("RGB")).copy()
    use = mask > 0
    out[use] = gen[use]
    return Image.fromarray(out)


def regions(mask: np.ndarray) -> list[dict]:
    """Bounding boxes of AI-generated regions (for labelling them in the UI and reports)."""
    n, _, st, _ = cv2.connectedComponentsWithStats((np.asarray(mask) > 0).astype(np.uint8), 8)
    return [{"x": int(st[i, 0]), "y": int(st[i, 1]), "w": int(st[i, 2]), "h": int(st[i, 3]),
             "pixels": int(st[i, 4])} for i in range(1, n)]


def mark(img: Image.Image, mask: np.ndarray) -> Image.Image:
    """Visible marking of AI-generated pixels: magenta tint plus outline."""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    m = np.asarray(mask) > 0
    if m.any():
        rgb[m] = rgb[m] * 0.55 + np.array([236, 72, 153], np.float32) * 0.45
        edge = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        rgb[edge] = (236, 72, 153)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def restore(img: Image.Image, protect: np.ndarray, extra_mask: np.ndarray | None = None) -> tuple[Image.Image, np.ndarray, dict]:
    mask = defect_mask(img, protect)
    if extra_mask is not None:
        # detector-found tears/holes, minus anything near protected text
        safe = ~cv2.dilate(protect.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        mask = np.maximum(mask, ((np.asarray(extra_mask) > 0) & safe).astype(np.uint8) * 255)
    pixels = int((mask > 0).sum())
    if pixels == 0:
        return img.copy(), mask, {"repaired_pixels": 0, "repaired_pct": 0.0, "regions": []}
    out = inpaint(img, mask)
    use = mask > 0
    return out, mask, {
        "regions": regions(mask),
        "repaired_pixels": pixels,
        "repaired_pct": round(100 * pixels / (img.width * img.height), 3),
        "text_pixels_modified": int((use & protect).sum()),
    }
