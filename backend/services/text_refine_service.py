"""Text-preserving refinement after DocRes.

Problem: DocRes cleans the paper well, but thin/faint strokes (the 'r' in 'original', the 'i' in
'revision', dots, 'x' in '32 x 32') can be lightened or erased.

Approach (no character is ever generated; only pixels that exist in the original are used):
1. Ink from the original: divide the original by its own estimated paper background at full
   resolution (removes stains/shadows but keeps every stroke the original has).
2. In detected text regions (PaddleOCR boxes), put back original ink that DocRes lost:
   ink_final = max(ink_docres, ink_original * gain). Outside text regions DocRes is kept as is.
3. Gentle unsharp mask on text regions only; no global thresholding.
4. Per-line OCR check: if a restored line reads worse than the original line (lower agreement
   with the original reading AND lower confidence), that line falls back to the stroke-preserving
   original-ink rendering. OCR results are only used to choose between existing pixels.
"""
import logging
from difflib import SequenceMatcher

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger("docrestore.text_refine")


def _gray(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)


def original_ink(original: Image.Image) -> np.ndarray:
    """0..1 ink strength of the original after removing its uneven paper background."""
    g = _gray(original)
    h, w = g.shape
    k = max(9, (min(h, w) // 60) | 1)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.medianBlur(bg.astype(np.uint8), min(255, max(21, (min(h, w) // 12) | 1))).astype(np.float32)
    ratio = np.clip(g / np.maximum(bg, 1), 0, 1)  # 1 = paper
    dark = 1 - ratio
    noise = float(np.percentile(dark, 60))  # paper texture level
    strong = float(np.percentile(dark, 99.5))
    ink = np.clip((dark - noise - 0.02) / max(0.05, strong - noise), 0, 1)
    return cv2.GaussianBlur(ink, (0, 0), 0.4)


def docres_ink(restored: Image.Image) -> tuple[np.ndarray, float]:
    g = _gray(restored)
    paper = float(np.percentile(g, 90))
    ink = np.clip((paper - g) / max(1.0, paper - float(np.percentile(g, 0.5))), 0, 1)
    return ink, paper


def _render(base_rgb: np.ndarray, ink: np.ndarray, ink_color: np.ndarray, region: np.ndarray) -> np.ndarray:
    """Darken base towards ink_color where `ink` exceeds what base already shows (region only)."""
    out = base_rgb.astype(np.float32)
    cur, _ = docres_ink(Image.fromarray(base_rgb))
    add = np.clip(ink - cur, 0, 1) * region
    out = out * (1 - add[..., None]) + ink_color[None, None, :] * add[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _sharpen(rgb: np.ndarray, region: np.ndarray, amount: float = 0.6, sigma: float = 1.0) -> np.ndarray:
    blur = cv2.GaussianBlur(rgb, (0, 0), sigma)
    sharp = cv2.addWeighted(rgb, 1 + amount, blur, -amount, 0)
    r = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 2)[..., None]
    return np.clip(sharp * r + rgb * (1 - r), 0, 255).astype(np.uint8)


def refine(original: Image.Image, restored: Image.Image, text_mask: np.ndarray) -> tuple[Image.Image, dict]:
    if restored.size != original.size:
        restored = restored.resize(original.size, Image.LANCZOS)
    rgb = np.asarray(restored.convert("RGB"))
    ink_o = original_ink(original)
    ink_d, _ = docres_ink(restored)
    region = text_mask.astype(np.float32)

    # Scale original ink so its solid strokes match DocRes' solid strokes.
    both = (ink_o > 0.5) & (ink_d > 0.5) & text_mask
    gain = float(np.clip(np.median(ink_d[both]) / max(1e-3, np.median(ink_o[both])), 0.8, 1.6)) if both.sum() > 50 else 1.0
    ink_target = np.clip(ink_o * gain, 0, 1)

    dark = rgb[(ink_d > 0.7) & text_mask]
    ink_color = np.median(dark, axis=0).astype(np.float32) if len(dark) > 50 else np.array([25, 22, 20], np.float32)

    # Work per stroke (connected component of original ink), not per pixel: a stroke is "lost"
    # when DocRes kept much less of it than the original had. Only those strokes are put back,
    # at their original shape, so letter spacing and stroke width elsewhere are unchanged.
    comp_mask = ((ink_target > 0.3) & text_mask).astype(np.uint8)
    n, labels, cstats, _ = cv2.connectedComponentsWithStats(comp_mask, 8)
    keep_o = np.bincount(labels.ravel(), weights=ink_target.ravel(), minlength=n)
    keep_d = np.bincount(labels.ravel(), weights=np.minimum(ink_d, ink_target).ravel(), minlength=n)
    retained = keep_d / np.maximum(keep_o, 1e-6)
    areas = cstats[:, cv2.CC_STAT_AREA]
    cand = np.nonzero((retained < 0.6) & (areas >= 3))[0]
    cand = cand[cand > 0]
    # A lost stroke is restored only if it belongs to a letter: it touches ink DocRes kept
    # (a partly erased stroke) or sits right above a kept stroke (i/j dots). Isolated dots in
    # gaps are dust and stay removed. This never creates ink the original did not have.
    kept = (ink_d > 0.35).astype(np.uint8)
    kn, kl, kst, _ = cv2.connectedComponentsWithStats(kept, 8)
    hs = kst[1:, cv2.CC_STAT_HEIGHT]
    gh = float(np.median(hs[(hs >= 5) & (hs <= kept.shape[0] * 0.1)])) if (hs >= 5).any() else 12.0
    near = cv2.dilate(kept, np.ones((3, 3), np.uint8)) > 0
    lost_ids = []
    for i in cand:
        x, y, cw, ch, _ = cstats[i]
        comp = labels[y:y + ch, x:x + cw] == i
        if (near[y:y + ch, x:x + cw] & comp).any():
            lost_ids.append(i)  # partly erased stroke of a letter
            continue
        if max(cw, ch) <= gh * 0.45:  # small dot: keep only if a stroke is directly below
            below = kept[y + ch:min(kept.shape[0], y + ch + int(gh * 0.7)), max(0, x - 1):x + cw + 1]
            if below.size and below.any():
                lost_ids.append(i)
    lost_ids = np.array(lost_ids, dtype=int)
    lost = np.isin(labels, lost_ids) if len(lost_ids) else np.zeros_like(text_mask)
    restore_ink = np.where(lost, ink_target, 0).astype(np.float32)
    merged = _render(rgb, restore_ink, ink_color, region)
    merged = _sharpen(merged, text_mask, amount=0.35, sigma=0.8)
    stats = {"gain": round(gain, 3), "strokes_checked": int(n - 1), "strokes_restored": int(len(lost_ids)),
             "restored_stroke_pixels": int(lost.sum()), "text_area_pct": round(100 * float(text_mask.mean()), 2)}
    log.info("text refine: %s", stats)
    return Image.fromarray(merged), stats


def remove_dark_specks(img: Image.Image, text_mask: np.ndarray, lines: list | None = None) -> tuple[Image.Image, int]:
    """Remove dust specks that sit on or between letters.

    A speck is a tiny, compact blob that is clearly darker than the document's own ink
    (dust/toner dots are near-black; printed strokes are not). Letters are never matched because
    their strokes have the typical ink darkness. Pixels are filled from their surroundings.
    """
    rgb = np.asarray(img.convert("RGB"))
    g = _gray(img)
    ink = g < np.percentile(g, 25)
    if not (ink & text_mask).any():
        return img, 0
    ink_level = float(np.median(g[ink & text_mask]))  # typical stroke darkness
    local_min = cv2.erode(g, np.ones((3, 3), np.uint8))
    cand = ((g < ink_level - 18) & (local_min < ink_level - 25)).astype(np.uint8)
    n, labels, st, _ = cv2.connectedComponentsWithStats(cand, 8)
    kept = (g < ink_level + 25).astype(np.uint8)
    kn, _, kst, _ = cv2.connectedComponentsWithStats(kept, 8)
    hs = kst[1:, cv2.CC_STAT_HEIGHT]
    gh = float(np.median(hs[(hs >= 5) & (hs <= g.shape[0] * 0.1)])) if (hs >= 5).any() else 12.0
    max_side = max(2, int(gh * 0.3))
    # Punctuation (. , : ;) sits in the lower part of a text line: never touch that band.
    baseline = np.zeros(g.shape, bool)
    for l in lines or []:
        x0, y0, x1, y1 = l["box"]
        baseline[int(y0 + (y1 - y0) * 0.6):y1 + 2, x0:x1] = True
    ids = [i for i in range(1, n)
           if max(st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]) <= max_side
           and st[i, cv2.CC_STAT_AREA] <= max_side * max_side
           and not baseline[st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] // 2,
                            st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH] // 2]]
    if not ids:
        return img, 0
    m = np.isin(labels, ids)
    # Grow the mask only into pixels that are darker than paper but not part of a normal stroke,
    # so filling a speck never eats into the neighbouring letter.
    halo = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    m = m | (halo & (g < ink_level - 10))
    return Image.fromarray(cv2.inpaint(rgb, m.astype(np.uint8) * 255, 1, cv2.INPAINT_TELEA)), len(ids)


def remove_background_specks(img: Image.Image, text_mask: np.ndarray, lines: list) -> tuple[Image.Image, int]:
    """Remove compact dark dust only well outside high-confidence OCR text regions."""
    if len(lines) < 4:
        return img, 0
    scores = [float(line.get("score", 0)) for line in lines]
    if not scores or float(np.mean(scores)) < 0.90:
        return img, 0
    rgb = np.asarray(img.convert("RGB"))
    gray = _gray(img)
    paper = float(np.percentile(gray, 85))
    dark = (gray < paper - 65).astype(np.uint8)
    n, labels, st, _ = cv2.connectedComponentsWithStats(dark, 8)
    protected = cv2.dilate(text_mask.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
    remove_ids = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        comp = labels[y:y + h, x:x + w] == i
        if (area <= 40 and max(w, h) <= 10 and
                not protected[y:y + h, x:x + w][comp].any()):
            remove_ids.append(i)
    if not remove_ids:
        return img, 0
    erase = np.isin(labels, remove_ids)
    erase = cv2.dilate(erase.astype(np.uint8), np.ones((3, 3), np.uint8))
    return Image.fromarray(cv2.inpaint(rgb, erase * 255, 2, cv2.INPAINT_TELEA)), len(remove_ids)


def fallback_render(original: Image.Image, restored: Image.Image, box_mask: np.ndarray) -> np.ndarray:
    """Clean paper (from DocRes) + full original ink inside box_mask: the most literal rendering."""
    rgb = np.asarray(restored.convert("RGB")).astype(np.float32)
    ink_o = original_ink(original)
    ink_d, paper = docres_ink(restored)
    # Match stroke darkness to the rest of the restored page (outside this line).
    out_box = box_mask < 0.5
    solid_d = ink_d[(ink_d > 0.5) & out_box]
    solid_o = ink_o[(ink_o > 0.5) & (box_mask > 0.5)]
    # Normalise this line's strokes so its darkest strokes match the page's solid ink, and drop
    # the faint haze (crease shadows) under the line's own noise floor.
    inside = box_mask > 0.5
    if inside.any():
        vals = ink_o[inside]
        floor = float(np.percentile(vals, 55))
        top = max(floor + 0.05, float(np.percentile(vals, 98)))
        target = float(np.median(solid_d)) if solid_d.size > 50 else 0.9
        ink_o = np.where(inside, np.clip((ink_o - floor) / (top - floor), 0, 1) * max(0.8, target), ink_o)
    elif solid_d.size > 50 and solid_o.size > 20:
        ink_o = np.clip(ink_o * float(np.clip(np.median(solid_d) / np.median(solid_o), 0.8, 2.0)), 0, 1)
    ink_o = np.clip(ink_o, 0, 1) ** 0.85
    paper_rgb = np.median(rgb[_gray(restored) >= paper - 3], axis=0) if (_gray(restored) >= paper - 3).any() else np.array([250] * 3)
    dark = rgb[(docres_ink(restored)[0] > 0.7)]
    ink_color = np.median(dark, axis=0) if len(dark) > 50 else np.array([25, 22, 20], np.float32)
    lit = paper_rgb[None, None, :] * (1 - ink_o[..., None]) + ink_color[None, None, :] * ink_o[..., None]
    m = box_mask[..., None]
    return np.clip(lit * m + rgb * (1 - m), 0, 255).astype(np.uint8)


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio() if (a or b) else 1.0


def _iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua else 0.0


def line_guard(original: Image.Image, refined: Image.Image, orig_lines: list, ref_lines: list,
               ocr_read) -> tuple[Image.Image, list, list]:
    """Revert lines whose restored reading is worse than the original's. Returns (image, lines, reverted)."""
    # All differing lines are fallback-rendered into ONE candidate page and read with ONE OCR call
    # (previously one OCR call per line: 20+ calls of ~5 s each on handwritten pages).
    reverted = []
    base = np.asarray(refined.convert("RGB")).copy()
    h, w = base.shape[:2]
    todo = []
    for ol in orig_lines:
        match = max(ref_lines, key=lambda r: _iou(ol["box"], r["box"]), default=None)
        if match is None or _iou(ol["box"], match["box"]) < 0.3:
            rtext, rscore = "", 0.0
        else:
            rtext, rscore = match["text"], match["score"]
        if rtext != ol["text"]:
            todo.append((ol, rtext, rscore))
    if not todo:
        return refined, ref_lines, reverted
    boxes = np.zeros((h, w), np.float32)
    for ol, _, _ in todo:
        x0, y0, x1, y1 = ol["box"]
        pad = max(2, (y1 - y0) // 5)
        boxes[max(0, y0 - pad):min(h, y1 + pad), max(0, x0 - pad):min(w, x1 + pad)] = 1
    candidate = fallback_render(original, refined, boxes)
    cand_lines = ocr_read(Image.fromarray(candidate))
    accept = np.zeros((h, w), bool)
    for ol, rtext, rscore in todo:
        # The original reading can be wrong too (e.g. a speck read as a letter), so the fallback
        # is accepted only if it reads closer to the original AND at least as confidently.
        cm = max(cand_lines, key=lambda r: _iou(ol["box"], r["box"]), default=None)
        if cm is None or _iou(ol["box"], cm["box"]) < 0.3:
            continue
        if _sim(cm["text"], ol["text"]) > _sim(rtext, ol["text"]) and cm["score"] >= rscore:
            x0, y0, x1, y1 = ol["box"]
            pad = max(2, (y1 - y0) // 5)
            accept[max(0, y0 - pad):min(h, y1 + pad), max(0, x0 - pad):min(w, x1 + pad)] = True
            reverted.append({"original": ol["text"], "restored": rtext, "after_fallback": cm["text"],
                             "box": ol["box"]})
    if not reverted:
        return refined, ref_lines, reverted
    out = base.copy()
    out[accept] = candidate[accept]
    out_img = Image.fromarray(out)
    return out_img, ocr_read(out_img), reverted
