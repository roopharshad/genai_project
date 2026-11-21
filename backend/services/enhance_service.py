"""Local (offline) enhancement steps that complement the remote AI restoration.

- remove_marks:  detects thin scratches, dust and spots and fills them by inpainting.
- colorize:      adds plausible colour to black-and-white photos with a pretrained CNN
                 (Zhang et al., "Colorful Image Colorization", ECCV 2016; OpenCV DNN, CPU).
                 Colours are predicted, not recovered: the network guesses typical colours.
- enhance_document: flattens uneven paper background (stains, yellowing, shadows), boosts
                 contrast and sharpens text. Optional black-and-white "scan" output.

Model files live in models/colorization/ (see README for download).
"""
import logging
import threading

import cv2
import numpy as np
from PIL import Image

from .. import config

log = logging.getLogger("docrestore.enhance")

MODEL_DIR = config.ROOT_DIR / "models" / "colorization"
_PROTO = MODEL_DIR / "colorization_deploy_v2.prototxt"
_WEIGHTS = MODEL_DIR / "colorization_release_v2.caffemodel"
_HULL = MODEL_DIR / "pts_in_hull.npy"
_net = None
_net_lock = threading.Lock()


class EnhanceError(RuntimeError):
    def __init__(self, message: str, status: int = 500):
        super().__init__(message)
        self.status = status


def _to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _to_pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def colorize_available() -> bool:
    return _PROTO.is_file() and _WEIGHTS.is_file() and _HULL.is_file()


def is_grayscale(img: Image.Image, tol: float = 8.0) -> bool:
    """True if the image has (almost) no colour, e.g. old B&W or sepia-free scans."""
    small = np.asarray(img.convert("RGB").resize((128, 128))).astype(np.int16)
    spread = small.max(axis=2) - small.min(axis=2)
    return float(np.percentile(spread, 90)) < tol * 2


def _looks_monochrome(img: Image.Image) -> bool:
    """B&W or sepia/toned: low saturation variation."""
    hsv = cv2.cvtColor(_to_bgr(img.resize((128, 128))), cv2.COLOR_BGR2HSV)
    return float(np.percentile(hsv[..., 1], 90)) < 70 or is_grayscale(img)


# ------------------------------------------------------------------ marks & scratches
def remove_marks(img: Image.Image, strength: str = "normal") -> tuple[Image.Image, float]:
    """Inpaint thin bright/dark defects. Returns (image, % of pixels repaired)."""
    bgr = _to_bgr(img)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    k = max(5, (min(h, w) // 150) | 1)  # defect scale relative to image size
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)    # bright scratches / dust
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)  # dark specks / cracks
    resp = cv2.max(tophat, blackhat)

    factor = {"light": 5.0, "normal": 4.0, "strong": 3.0}.get(strength, 4.0)
    mean, std = float(resp.mean()), float(resp.std())

    # Pass 1: dust and specks (strong, small outliers).
    strong = (resp > max(28.0, mean + factor * std)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(strong, 8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] <= k * k
    mask = keep[labels]

    # Pass 2: scratches (weaker responses forming long thin lines).
    weak = (resp > max(14.0, mean + (factor - 1.8) * std)).astype(np.uint8)
    min_len = max(h, w) * 0.04
    n, labels, stats, _ = cv2.connectedComponentsWithStats(weak, 8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        _, _, bw, bh, area = stats[i]
        length = float(np.hypot(bw, bh))
        keep[i] = length >= min_len and area / max(length, 1.0) <= max(2.5, k / 2) and area <= h * w * 0.01
    mask |= keep[labels]
    mask = cv2.dilate(mask.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=1)
    pct = round(100 * float((mask > 0).mean()), 2)
    if pct == 0:
        return img, 0.0
    out = cv2.inpaint(bgr, mask, max(3, k // 2), cv2.INPAINT_TELEA)
    return _to_pil(out), pct


# ------------------------------------------------------------------ colourization
def _load_net():
    global _net
    with _net_lock:
        if _net is None:
            if not colorize_available():
                raise EnhanceError("Colourization model files are missing on the server.", 503)
            net = cv2.dnn.readNetFromCaffe(str(_PROTO), str(_WEIGHTS))
            pts = np.load(_HULL).transpose().reshape(2, 313, 1, 1).astype(np.float32)
            net.getLayer(net.getLayerId("class8_ab")).blobs = [pts]
            net.getLayer(net.getLayerId("conv8_313_rh")).blobs = [np.full((1, 313), 2.606, np.float32)]
            _net = net
            log.info("colourization model loaded")
    return _net


def colorize(img: Image.Image, vibrance: float = 1.15) -> Image.Image:
    bgr = _to_bgr(img)
    lab = cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    L_full = lab[:, :, 0]
    small = cv2.resize(lab, (224, 224))[:, :, 0] - 50
    net = _load_net()
    with _net_lock:  # cv2.dnn.Net is not thread-safe
        net.setInput(cv2.dnn.blobFromImage(small))
        ab = net.forward()[0].transpose((1, 2, 0))
    ab = cv2.resize(ab, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_CUBIC) * vibrance
    out = cv2.cvtColor(np.dstack([L_full, ab]).astype(np.float32), cv2.COLOR_LAB2BGR)
    return _to_pil((np.clip(out, 0, 1) * 255).astype(np.uint8))


# ------------------------------------------------------------------ photo finishing
def finish_photo(img: Image.Image) -> Image.Image:
    """Gentle local contrast (CLAHE on lightness) + light sharpening."""
    bgr = _to_bgr(img)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(l)
    bgr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(bgr, (0, 0), 1.2)
    return _to_pil(cv2.addWeighted(bgr, 1.35, blur, -0.35, 0))


# ------------------------------------------------------------------ documents
def _order_quad(pts: np.ndarray) -> np.ndarray:
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], np.float32)


def crop_page(bgr: np.ndarray):
    """Find a page that is clearly brighter than its surroundings (e.g. paper on a table).

    Returns (cropped, note) or (original, None) when no confident page is found.
    """
    h, w = bgr.shape[:2]
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (0, 0), 3)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bgr, None
    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if not 0.2 * h * w < area < 0.95 * h * w:
        return bgr, None
    inside = np.zeros((h, w), np.uint8)
    cv2.drawContours(inside, [c], -1, 255, -1)
    if float(gray[inside > 0].mean()) - float(gray[inside == 0].mean()) < 40:
        return bgr, None  # page is not distinct from background: leave untouched

    quad = cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)
    if len(quad) == 4 and cv2.isContourConvex(quad):
        src = _order_quad(quad.reshape(4, 2).astype(np.float32))
        tw = int(max(np.linalg.norm(src[0] - src[1]), np.linalg.norm(src[3] - src[2])))
        th_ = int(max(np.linalg.norm(src[0] - src[3]), np.linalg.norm(src[1] - src[2])))
        dst = np.array([[0, 0], [tw - 1, 0], [tw - 1, th_ - 1], [0, th_ - 1]], np.float32)
        return cv2.warpPerspective(bgr, cv2.getPerspectiveTransform(src, dst), (tw, th_)), "Cropped and straightened the page"
    x, y, bw, bh = cv2.boundingRect(c)
    return bgr[y:y + bh, x:x + bw], "Cropped to the page"


def remove_document_specks(img: Image.Image) -> tuple[Image.Image, float]:
    """Remove isolated dots on a flattened page without touching letter strokes."""
    bgr = _to_bgr(img)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    if n <= 1:
        return img, 0.0
    areas = stats[1:, cv2.CC_STAT_AREA]
    big = areas[areas > 8]
    typical = float(np.median(big)) if big.size else 40.0
    limit = max(4.0, typical * 0.12)
    # Small ink next to larger ink is likely part of text (i-dots, punctuation): keep it.
    text = np.isin(labels, 1 + np.nonzero(areas > limit)[0]).astype(np.uint8)
    text_zone = cv2.dilate(text, np.ones((9, 9), np.uint8))
    speck = np.zeros(n, bool)
    speck[1:] = areas <= limit
    mask = speck[labels] & (text_zone == 0)
    pct = round(100 * float(mask.mean()), 2)
    if pct == 0:
        return img, 0.0
    m = cv2.dilate(mask.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    return _to_pil(cv2.inpaint(bgr, m, 3, cv2.INPAINT_TELEA)), pct


def _flatten(bgr: np.ndarray) -> np.ndarray:
    """Divide out uneven paper tone: stains, creases, shadows, yellowing gradients."""
    h, w = bgr.shape[:2]
    k = max(9, (min(h, w) // 60) | 1)  # larger than a text stroke
    kb = max(21, (min(h, w) // 12) | 1)
    planes = []
    for ch in cv2.split(bgr):
        bg = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        bg = cv2.medianBlur(bg, kb if kb < 255 else 255)
        planes.append(cv2.divide(ch, bg, scale=255))
    return cv2.merge(planes)


_face_cascade = None


def _faces(gray: np.ndarray) -> int:
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    m = max(24, min(gray.shape) // 12)
    return len(_face_cascade.detectMultiScale(gray, 1.15, 6, minSize=(m, m)))


def document_score(img: Image.Image) -> dict:
    """Measure how much the image looks like a page of text (lines of dark glyphs on paper)."""
    rgb = img.convert("RGB")
    s = 1000 / max(rgb.size)
    if s < 1:
        rgb = rgb.resize((round(rgb.width * s), round(rgb.height * s)))
    gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    # Dark strokes on a lighter background (text), independent of paper colour.
    bh = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17)))
    _, bw = cv2.threshold(bh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.bitwise_and(bw, (bh > 18).astype(np.uint8) * 255)
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    hs = stats[1:, cv2.CC_STAT_HEIGHT]
    ws = stats[1:, cv2.CC_STAT_WIDTH]
    glyphs = int(((hs >= 5) & (hs <= h * 0.08) & (ws >= 2) & (ws <= w * 0.15)).sum())
    lines_img = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 40), 3)))
    contours, _ = cv2.findContours(lines_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lines = 0
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw >= w * 0.12 and 6 <= ch <= h * 0.1 and cw >= 4 * ch:
            lines += 1
    return {"glyphs": glyphs, "text_lines": lines, "faces": _faces(gray)}


def is_document(img: Image.Image) -> bool:
    d = document_score(img)
    if d["faces"] > 0 and d["text_lines"] < 8:
        return False
    return d["text_lines"] >= 4 and d["glyphs"] >= 60


def _clean_ink(ink: np.ndarray) -> tuple[np.ndarray, int]:
    """Remove ink that is not text: dust dots, specks and crease/scratch lines.

    Text is found as lines of glyphs (glyphs joined horizontally). Punctuation inside a
    text line is kept. Outside text lines, small blobs and thin long strokes are removed.
    """
    mask = (ink > 0.4).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return ink, 0
    hs, ws, areas = stats[1:, cv2.CC_STAT_HEIGHT], stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_AREA]
    glyph_like = (hs >= 6) & (hs <= ink.shape[0] * 0.08)
    gh = float(np.median(hs[glyph_like])) if glyph_like.any() else 20.0  # typical letter height
    garea = float(np.median(areas[glyph_like])) if glyph_like.any() else 80.0

    # Text-line zones: glyphs merged along the line, then grown a little vertically.
    glyph_ids = 1 + np.nonzero(glyph_like & (hs >= gh * 0.5))[0]
    glyphs = np.isin(labels, glyph_ids).astype(np.uint8)
    lines = cv2.morphologyEx(glyphs, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (int(gh * 1.6) | 1, 1)))
    lc, ll, lstats, _ = cv2.connectedComponentsWithStats(lines, 8)
    keep_line = np.zeros(lc, bool)
    keep_line[1:] = lstats[1:, cv2.CC_STAT_WIDTH] >= gh * 3  # a real text line has several glyphs
    zone = cv2.dilate(keep_line[ll].astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_RECT, (int(gh) | 1, int(gh * 0.5) | 1))) > 0

    remove = np.zeros(n, bool)
    inside = np.zeros(n, np.int64)
    np.add.at(inside, labels[zone], 1)
    in_zone = inside[1:] >= areas * 0.5
    length = np.hypot(hs, ws)
    thin_long = (length > gh * 2.5) & (areas / np.maximum(length, 1) < gh * 0.18)
    small = areas < garea * 0.5
    # A small blob is punctuation / an i-dot only if a letter sits right next to it.
    letters = np.isin(labels, 1 + np.nonzero(~small & ~thin_long)[0]).astype(np.uint8)
    reach = cv2.dilate(letters, cv2.getStructuringElement(cv2.MORPH_RECT, (int(gh * 1.8) | 1, int(gh * 0.9) | 1)))
    touch = np.zeros(n, np.int64)
    np.add.at(touch, labels[reach > 0], 1)
    isolated = touch[1:] == 0
    remove[1:] = (small & isolated) | (~in_zone & (small | thin_long)) | (thin_long & (length > gh * 6))
    # Faint haze far from any kept stroke.
    kept = (mask > 0) & ~remove[labels]
    near = cv2.dilate(kept.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    out = ink.copy()
    out[remove[labels] | ((ink > 0) & ~near)] = 0
    return out, int(remove.sum())


def enhance_document(img: Image.Image, scale: float = 2, style: str = "color",
                     crop: bool = True, remove_specks: bool = True) -> tuple[Image.Image, list]:
    """Restore a photographed or scanned page.

    1. crop the page off the table, 2. denoise (at source size, fast),
    3. upscale, 4. divide out stains/creases/shadows, 5. separate ink from paper with a
    soft threshold so paper becomes clean and faded text becomes solid, 6. recompose.
    """
    notes = []
    bgr = _to_bgr(img)
    if crop:
        bgr, note = crop_page(bgr)
        if note:
            notes.append(note)
    gray0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    paper = np.median(bgr[gray0 >= np.percentile(gray0, 60)], axis=0).astype(np.float32)

    bgr = cv2.fastNlMeansDenoisingColored(bgr, None, 7, 7, 7, 21)
    if scale != 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    flat = _flatten(bgr)
    notes.append("Removed stains, creases, shadows and yellowing")

    gray = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY).astype(np.float32)
    darkness = 255.0 - gray  # 0 = paper, high = ink
    # Paper level = typical darkness of background pixels; ink level = strong strokes.
    lo = float(np.percentile(darkness, 55)) + 6.0
    hi = max(lo + 25.0, float(np.percentile(darkness, 99.3)))
    ink = np.clip((darkness - lo) / (hi - lo), 0, 1)
    ink = cv2.GaussianBlur(ink, (0, 0), 0.5) ** 0.75  # make faded strokes solid

    if remove_specks:
        ink, removed = _clean_ink(ink)
        notes.append(f"Removed {removed} specks, dust marks and crease lines" if removed else "No specks found")

    if style == "bw":
        out = np.where(ink > 0.35, 0, 255).astype(np.uint8)
        out = cv2.medianBlur(out, 3)
        notes.append("High-contrast black & white scan")
        return Image.fromarray(out).convert("RGB"), notes

    if style == "aged":
        tone = np.clip(paper * 1.08 + 8, 0, 255)  # cleaned, lighter, even parchment
        ink_color = np.array([28, 34, 45], np.float32)  # dark sepia-black (BGR)
        notes.append("Even, clean aged-paper tone with dark ink")
    else:
        tone = np.array([250, 250, 250], np.float32)
        ink_color = np.array([22, 20, 18], np.float32)
        notes.append("Clean white paper with dark ink")
    out = tone * (1 - ink[..., None]) + ink_color * ink[..., None]
    out = np.clip(out, 0, 255).astype(np.uint8)
    blur = cv2.GaussianBlur(out, (0, 0), 1.0)
    out = cv2.addWeighted(out, 1.35, blur, -0.35, 0)
    return _to_pil(out), notes
