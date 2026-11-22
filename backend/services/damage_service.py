"""Computer-vision damage detection for document images, and restoration model selection.

detect(img) measures blur, fading, stains, creases/scratches, specks, tears and missing
regions with classical CV (no training data needed), returns per-damage severity 0..1, the
evidence behind it, and boolean masks. plan(report) turns the measurements into the list of
restoration stages to run, each with the reason it was chosen or skipped.
Analysis runs on a copy scaled to <= 1200 px; masks are returned at the input size.
"""
import cv2
import numpy as np
from PIL import Image

from . import paper_restore_service as paper

WORK_SIDE = 1200


def _sev(x: float) -> float:
    return round(float(np.clip(x, 0.0, 1.0)), 3)


def _work(img: Image.Image) -> tuple[Image.Image, float]:
    s = min(1.0, WORK_SIDE / max(img.size))
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    return img.convert("RGB"), s


def _page_mask(rgb: np.ndarray, ink: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Paper (plus ink) mask, and its convex hull. Missing paper = hull minus page."""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    h, w = ink.shape
    core = np.zeros((h, w), bool)
    core[h // 4:3 * h // 4, w // 4:3 * w // 4] = True
    ref = np.median(lab[core & ~ink], axis=0)
    dist = np.linalg.norm((lab - ref) * np.array([0.6, 1.0, 1.0]), axis=2)
    paper_like = dist < max(28.0, float(np.percentile(dist[core], 97)) * 1.15)
    page = (paper_like | ink).astype(np.uint8)
    page = cv2.morphologyEx(page, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab_cc, st, _ = cv2.connectedComponentsWithStats(page, 8)
    if n <= 1:
        return np.ones((h, w), bool), np.ones((h, w), bool)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    page = (lab_cc == big).astype(np.uint8)
    cnts, _ = cv2.findContours(page, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = np.zeros((h, w), np.uint8)
    cv2.fillPoly(hull, [cv2.convexHull(max(cnts, key=cv2.contourArea))], 1)
    return page.astype(bool), hull.astype(bool)


def _lines(gray: np.ndarray, protect: np.ndarray) -> tuple[np.ndarray, list]:
    """Long thin straight marks outside text: scratches and crease lines."""
    h, w = gray.shape
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    resp = cv2.max(cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k))
    edges = (resp > max(18, float(np.percentile(resp, 97)))).astype(np.uint8) * 255
    edges[cv2.dilate(protect.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0] = 0
    min_len = int(0.12 * min(h, w))
    segs = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=min_len, maxLineGap=6)
    mask = np.zeros((h, w), np.uint8)
    out = []
    for s in (segs if segs is not None else [])[:200]:
        x0, y0, x1, y1 = map(int, s[0])
        cv2.line(mask, (x0, y0), (x1, y1), 1, 3)
        out.append([x0, y0, x1, y1])
    return mask.astype(bool), out


def detect(img: Image.Image) -> dict:
    work, s = _work(img)
    rgb = np.asarray(work)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    m = paper.ink_mask(work)
    ink, protect = m["ink"], m["protect"]
    h, w = gray.shape

    # --- blur: sharpness of ink edges (Laplacian energy on stroke borders) relative to contrast
    edge_zone = cv2.dilate(ink.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~cv2.erode(
        ink.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    lap = np.abs(cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F))
    contrast = float(np.percentile(gray, 95) - np.percentile(gray, 5)) + 1.0
    sharp = float(np.mean(lap[edge_zone])) / contrast if edge_zone.any() else 0.0
    blur_sev = _sev((0.22 - sharp) / 0.14)

    # --- fading: how dark the ink is relative to its local paper
    dark = 1 - m["ratio"]
    ink_dark = float(np.percentile(dark[ink], 90)) if ink.sum() > 50 else 0.0
    fade_sev = _sev((0.55 - ink_dark) / 0.35)

    # --- stains: variation of the paper layer (luminance + colour) away from ink
    page, hull = _page_mask(rgb, ink)
    clean = page & ~protect & ~m["blob"]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    smooth = cv2.GaussianBlur(lab, (0, 0), 9)
    # The paper layer P (strokes closed away) shows stains as regions darker than clean paper,
    # independent of how much handwriting crosses them.
    P = cv2.GaussianBlur(m["paper"], (0, 0), 3)
    bright = float(np.percentile(P[page], 92)) if page.any() else float(np.percentile(P, 92))
    rel = P / max(bright, 1.0)
    if clean.sum() > 500:
        std_l = float(np.std(smooth[..., 0][clean]))
        std_c = float(np.std(smooth[..., 1][clean]) + np.std(smooth[..., 2][clean]))
    else:
        std_l = std_c = 0.0
    stain_mask = page & (rel < 0.86) & (rel >= 0.55)
    stain_mask = cv2.morphologyEx(stain_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)).astype(bool)
    stain_sev = _sev(std_l / 22 + std_c / 18 - 0.15)
    yellow = float(np.median(lab[..., 2][clean]) - 128) if clean.any() else 0.0

    # --- creases / scratches
    lines_mask, segs = _lines(gray, protect)
    _, folds = paper.fold_map(m["lum"], protect)
    # Horizontal "folds" between text lines are line spacing, not creases: keep long, strong ones.
    folds = [f for f in folds if f["coverage"] >= 0.6 and f["strength"] >= 0.015]
    crease_sev = _sev(len(segs) / 25 + sum(f["strength"] for f in folds) * 4)

    # --- specks: tiny isolated dark components outside text
    small = (gray < np.percentile(gray, 50) - 40).astype(np.uint8)
    n, lab_cc, st, _ = cv2.connectedComponentsWithStats(small, 8)
    far_text = cv2.dilate(protect.astype(np.uint8), np.ones((15, 15), np.uint8)) == 0
    specks = sum(1 for i in range(1, n) if st[i, cv2.CC_STAT_AREA] <= 30
                 and far_text[st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] // 2,
                              st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH] // 2])
    speck_sev = _sev(specks / 150)

    # --- tears and missing regions: paper absent inside the page outline, or interior holes
    missing = hull & ~page
    missing = cv2.morphologyEx(missing.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab_cc, st, _ = cv2.connectedComponentsWithStats(missing, 8)
    min_area = max(40, int(h * w * 0.0004))
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_area
    missing = keep[lab_cc]
    regions = [{"x": int(st[i, 0] / s), "y": int(st[i, 1] / s), "w": int(st[i, 2] / s), "h": int(st[i, 3] / s),
                "area_pct": round(100 * st[i, 4] / (h * w), 3)} for i in range(1, n) if keep[i]]
    # Burns, holes and heavy blotches: dark regions far thicker than any pen stroke. An opening
    # with a disk of ~3 stroke widths erases handwriting and keeps only these thick regions.
    r = max(4, int(round(3 * m["sw"])))
    thick = cv2.morphologyEx((page & (rel < 0.55)).astype(np.uint8), cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(thick.astype(np.uint8), 8)
    for i in range(1, n2):
        if st2[i, cv2.CC_STAT_AREA] >= min_area:
            regions.append({"x": int(st2[i, 0] / s), "y": int(st2[i, 1] / s), "w": int(st2[i, 2] / s),
                            "h": int(st2[i, 3] / s), "area_pct": round(100 * st2[i, 4] / (h * w), 3), "kind": "burn_or_blotch"})
        else:
            thick[lab2 == i] = False
    m["blob"] = m["blob"] | thick
    missing_pct = 100 * float(missing.mean())
    blob_pct = 100 * float(m["blob"].mean())
    tear_sev = _sev(missing_pct / 4 + blob_pct / 3)

    # --- noise
    # measured on clean paper only: handwriting edges are not noise
    resid = gray.astype(np.float32) - cv2.medianBlur(gray, 3).astype(np.float32)
    noise = float(np.std(resid[clean])) if clean.sum() > 500 else float(np.std(resid))
    noise_sev = _sev((noise - 4) / 10)

    damages = {
        "blur": {"severity": blur_sev, "evidence": f"edge sharpness {sharp:.3f} (sharp text > 0.22)"},
        "fading": {"severity": fade_sev, "evidence": f"ink darkness {ink_dark:.2f} relative to paper (clear ink > 0.55)"},
        "stains": {"severity": stain_sev, "evidence": f"paper tone variation L={std_l:.1f}, colour={std_c:.1f}, yellowing b*={yellow:+.0f}"},
        "creases_scratches": {"severity": crease_sev, "evidence": f"{len(segs)} long straight marks, {len(folds)} fold lines"},
        "specks_noise": {"severity": max(speck_sev, noise_sev), "evidence": f"{specks} isolated specks, noise sigma {noise:.1f}"},
        "tears_missing": {"severity": tear_sev, "evidence": f"{missing_pct:.2f}% paper missing inside the page outline, {blob_pct:.2f}% burn/hole blobs",
                          "regions": regions[:50]},
    }
    for d in damages.values():
        sv = d["severity"]
        d["level"] = "none" if sv < 0.15 else "mild" if sv < 0.4 else "moderate" if sv < 0.7 else "severe"
        d["detected"] = sv >= 0.15
    sevs = [d["severity"] for d in damages.values()]
    overall = round(100 * (0.6 * max(sevs) + 0.4 * float(np.mean(sevs))), 1)

    def up(mask):
        return cv2.resize(mask.astype(np.uint8), img.size, interpolation=cv2.INTER_NEAREST).astype(bool)

    masks = {"stains": up(stain_mask), "creases_scratches": up(lines_mask), "tears_missing": up(missing | m["blob"]),
             "missing_paper": up(missing)}
    return {"damages": damages, "damage_score": overall, "yellowing": round(yellow, 1),
            "ink_pct": round(100 * float(ink.mean()), 2), "size": list(img.size), "masks": masks}


def overlay(img: Image.Image, masks: dict) -> Image.Image:
    """Colour-coded damage map: stains amber, creases/scratches cyan, tears/missing red."""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    out = np.repeat(gray[..., None], 3, axis=2) * 0.75 + 50
    for key, colour in (("stains", (255, 170, 0)), ("creases_scratches", (0, 200, 255)), ("tears_missing", (255, 40, 60))):
        mk = masks.get(key)
        if mk is not None and mk.any():
            out[mk] = out[mk] * 0.4 + np.array(colour, np.float32) * 0.6
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def plan(report: dict) -> list[dict]:
    """Choose restoration stages from the damage report. Every stage records why."""
    d = {k: v["severity"] for k, v in report["damages"].items()}
    steps = [{"stage": "page_crop", "model": "OpenCV page detection", "run": True, "reason": "always: isolate the page"}]

    def add(stage, model, cond, why_yes, why_no):
        steps.append({"stage": stage, "model": model, "run": bool(cond), "reason": why_yes if cond else why_no})

    add("lama_repair", "LaMa (big-lama)", d["tears_missing"] >= 0.15 or d["stains"] >= 0.4,
        "tears, holes or heavy blotches detected (repair limited to paper outside text)", "no tears or holes detected")
    add("docres_deblur", "DocRes deblurring", d["blur"] >= 0.35,
        "text edges are blurred", "text edges are sharp enough (saves ~45 s on CPU)")
    add("docres_appearance", "DocRes appearance", True,
        "always: shadow and appearance correction (measured best OCR result on the printed sample)", "")
    add("text_refine", "Stroke recovery + PaddleOCR line guard", True,
        "always: put back strokes the models erased (verification needs readable OCR)", "")
    add("speck_cleanup", "OCR-guarded speck removal", d["specks_noise"] >= 0.15,
        "isolated specks detected outside text", "no specks detected")
    add("paper_normalize", "Ink-protecting paper normalisation", d["stains"] >= 0.15 or d["fading"] >= 0.15 or d["creases_scratches"] >= 0.15,
        "stains, tint or creases detected (kept only if it does not lower text readability)", "paper is already even")
    return steps


def summary(report: dict) -> dict:
    """JSON-safe report (masks removed)."""
    return {k: v for k, v in report.items() if k != "masks"}
