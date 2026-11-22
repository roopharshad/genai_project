"""Conservative, ink-protecting paper restoration for old (handwritten or printed) documents.

Model of a document photo:  I_c(x) = P_c(x) * R_c(x)
  P = paper/illumination layer (stains, yellow patches, shadows, folds: smooth, large-scale)
  R = reflectance ratio (ink: thin, dark, high-frequency; paper texture: ~1)

Every correction here acts on P (or on a smooth shading offset), never by painting ink:
- stains:   I / P_est  * target paper tone        -> ink keeps its contrast and shape
- folds:    long thin shading ridges are measured and divided out (a multiplicative
            correction applied to ink and paper alike, so strokes crossing a fold keep their
            shape); no inpainting across text
- texture:  edge-preserving smoothing only on pixels outside the dilated ink mask
- ink:      monotonic darkening of pixels already classified as ink (faded strokes become
            more visible; no pixel outside the ink mask can become ink)
When unsure whether a dark region is ink or stain, it is treated as ink (kept).
"""
import logging

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger("docrestore.paper")


def _odd(n: float) -> int:
    n = int(round(n))
    return n if n % 2 else n + 1


def _rgbf(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32)


def _lum(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


# ---------------------------------------------------------------- ink / paper separation
def stroke_width(dark: np.ndarray) -> float:
    """Typical stroke width (px) of a binary ink mask, from the distance transform."""
    if dark.sum() < 50:
        return 3.0
    dt = cv2.distanceTransform(dark.astype(np.uint8), cv2.DIST_L2, 3)
    ridge = dt[(dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)) - 1e-3)]
    return float(np.clip(2 * np.median(ridge), 1.5, 15)) if ridge.size else 3.0


def paper_layer(lum: np.ndarray, sw: float) -> np.ndarray:
    """Paper/illumination estimate: closing removes strokes, median smooths paper fibres but
    still follows stain borders (kernel ~ a few stroke widths, not the whole page)."""
    k1 = _odd(max(7, 4 * sw + 1))
    closed = cv2.morphologyEx(lum, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k1, k1)))
    k2 = _odd(min(255, max(15, 3 * k1)))
    bg = cv2.medianBlur(np.clip(closed, 0, 255).astype(np.uint8), k2).astype(np.float32)
    return np.maximum(cv2.GaussianBlur(bg, (0, 0), k1 / 3), 1.0)


def ink_channel(rgb: np.ndarray) -> np.ndarray:
    """Channel used to separate ink from stains.

    Yellow/brown stains absorb mostly blue and some green, so on aged paper they barely change
    the channel in which the paper is brightest (usually red). Ink darkens all channels. Using
    that channel makes stain rims look like paper and keeps real strokes dark. For neutral grey
    paper the channels are similar and this falls back to luminance."""
    med = np.median(rgb.reshape(-1, 3), axis=0)
    c = int(np.argmax(med))
    if med[c] - med.min() < 15:  # neutral paper
        return _lum(rgb)
    return 0.8 * rgb[..., c] + 0.2 * _lum(rgb)


def ink_mask(img: Image.Image) -> dict:
    """Detect ink. Returns masks and the estimates used by the other steps."""
    rgb = _rgbf(img)
    lum = ink_channel(rgb)
    # first pass stroke width on a rough mask, then the real estimate
    rough = cv2.adaptiveThreshold(lum.astype(np.uint8), 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 10)
    sw = stroke_width(rough.astype(bool))
    P = paper_layer(lum, sw)
    ratio = np.clip(lum / P, 0, 1.5)
    dark = 1 - ratio
    paper_px = dark < np.percentile(dark, 60)
    mad = float(np.median(np.abs(dark[paper_px] - np.median(dark[paper_px])))) + 1e-3
    thr = max(0.05, float(np.median(dark[paper_px])) + 5 * mad)
    k = _odd(max(5, 3 * sw))
    blackhat = cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    weak = (dark > thr) & (blackhat > max(6.0, thr * 60))
    # Hysteresis: a component is confident ink only if it contains a strong core. Paper creases
    # and fibre texture are weak everywhere; even faded strokes keep a darker core.
    strong_thr = max(2 * thr, 0.18)
    n, lab, st, _ = cv2.connectedComponentsWithStats(weak.astype(np.uint8), 8)
    has_core = np.zeros(n, bool)
    has_core[np.unique(lab[weak & (dark > strong_thr)])] = True
    has_core[0] = False
    big = np.zeros(n, bool)
    big[1:] = st[1:, cv2.CC_STAT_AREA] >= 4  # dots of i/j and punctuation (>= 4 px) are kept
    # Blobs (burns, holes, heavy stain spots) are much thicker than any pen stroke: the largest
    # inscribed radius of the component is several stroke widths. They are kept exactly as they
    # are (never darkened, never flattened) because they may hide ink.
    dt = cv2.distanceTransform(weak.astype(np.uint8), cv2.DIST_L2, 3)
    rmax = np.zeros(n, np.float32)
    np.maximum.at(rmax, lab.ravel(), dt.ravel())
    blob_c = rmax > max(4.0, 2.5 * sw)
    blob_c[0] = False
    blob = blob_c[lab]
    ink = (has_core & big & ~blob_c)[lab]
    # weak, coreless marks (creases, fibres, possibly very faint ink): uncertain -> only partly
    # flattened, never darkened, never removed
    uncertain = weak & ~ink & ~blob
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd(sw + 2),) * 2)
    protect = cv2.dilate(ink.astype(np.uint8), kern) > 0
    blob_zone = cv2.dilate(blob.astype(np.uint8), kern) > 0
    return {"ink": ink, "uncertain": uncertain, "blob": blob_zone, "protect": protect, "paper": P, "ratio": ratio,
            "lum": lum, "sw": sw, "thr": thr, "rgb": rgb}


# ---------------------------------------------------------------- stains
def normalize_paper(img: Image.Image, m: dict, tone: str = "aged", strength: float = 1.0) -> tuple[np.ndarray, dict]:
    """Divide out the paper layer per channel and re-apply one even paper colour.

    tone='aged' keeps the document's own paper colour (its clean, bright part);
    tone='white' uses near-white paper.
    """
    rgb, lum, P = m["rgb"], m["lum"], m["paper"]
    sw = m["sw"]
    out = np.empty_like(rgb)
    k1 = _odd(max(7, 4 * sw + 1))
    clean = ~m["protect"]
    # target paper colour: bright, clean paper (75-95th percentile of the paper layer)
    sel = clean & (P >= np.percentile(P[clean], 75)) & (P <= np.percentile(P[clean], 97))
    target = np.median(rgb[sel], axis=0) if sel.sum() > 100 else np.median(rgb[clean], axis=0)
    if tone == "aged":
        # Keep an aged cream paper, but remove the strong orange cast common in stained scans.
        neutral_aged = np.array([235, 222, 185], np.float32)
        target = 0.45 * target + 0.55 * neutral_aged
    elif tone == "white":
        target = np.array([246, 244, 238], np.float32)
    # how much of the residual (texture) ratio is kept: 1 inside ink, 0.6 on uncertain marks,
    # 0.35 on clearly-clean paper; soft transitions so no edges are created
    keep = np.full(lum.shape, 0.35, np.float32)
    unc = cv2.dilate(m["uncertain"].astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    keep[unc] = 0.6
    keep[cv2.dilate(m["protect"].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0] = 1.0
    keep = np.maximum(cv2.GaussianBlur(keep, (0, 0), 1.0), m["protect"].astype(np.float32))
    blob_soft = cv2.GaussianBlur(m["blob"].astype(np.float32), (0, 0), 2.0)
    if tone == "white":
        # Neutral output uses one luminance reflectance ratio for all channels. This removes
        # yellow/green stain casts without changing the location or geometry of dark strokes.
        original_lum = _lum(rgb)
        lum_paper = paper_layer(original_lum, sw)
        lum_ratio = original_lum / np.maximum(lum_paper, 1.0)
        lum_ratio = 1 + (lum_ratio - 1) * keep
        for c in range(3):
            neutral = lum_ratio * target[c]
            out[..., c] = neutral * (1 - blob_soft) + rgb[..., c] * blob_soft
    else:
        for c in range(3):
            ch = rgb[..., c]
            closed = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k1, k1)))
            pc = cv2.medianBlur(np.clip(closed, 0, 255).astype(np.uint8), _odd(min(255, max(15, 3 * k1)))).astype(np.float32)
            pc = np.maximum(cv2.GaussianBlur(pc, (0, 0), k1 / 3), 1.0)
            ratio_c = ch / pc
            # Away from ink, the remaining ratio is paper texture: wrinkles, stain rims, fibres.
            ratio_c = 1 + (ratio_c - 1) * keep
            layer = target[c] * strength + pc * (1 - strength)
            layer = pc * np.clip(layer / pc, 0.8, 1.7)
            res = ratio_c * layer
            out[..., c] = res * (1 - blob_soft) + ch * blob_soft
    stain = float(np.std(cv2.GaussianBlur(P, (0, 0), 8)[clean]))
    return np.clip(out, 0, 255), {"paper_tone_rgb": [round(float(v)) for v in target],
                                  "stain_std_before": round(stain, 2)}


# ---------------------------------------------------------------- folds
def fold_map(lum: np.ndarray, protect: np.ndarray) -> tuple[np.ndarray, list]:
    """Find long straight horizontal/vertical shading ridges (fold lines) and return a smooth
    multiplicative shading map S (1 = no fold) plus a description of each fold."""
    h, w = lum.shape
    L = lum.copy()
    # replace ink by local paper so text does not look like a ridge
    if protect.any():
        L[protect] = cv2.medianBlur(np.clip(lum, 0, 255).astype(np.uint8), 21).astype(np.float32)[protect]
    S = np.ones_like(L)
    folds = []
    for axis in ("vertical", "horizontal"):
        if axis == "vertical":
            across = cv2.blur(L, (_odd(w * 0.03), 1))          # smooth across the fold
            along_k = (1, _odd(h * 0.15))                       # average along the fold
        else:
            across = cv2.blur(L, (1, _odd(h * 0.03)))
            along_k = (_odd(w * 0.15), 1)
        rel = L / np.maximum(across, 1) - 1                     # ridge: darker/lighter than neighbours
        line = cv2.blur(rel, along_k)                           # only long, straight ridges survive
        prof = np.median(line, axis=0 if axis == "vertical" else 1)  # per column / per row
        n = len(prof)
        noise = float(np.median(np.abs(prof - np.median(prof)))) * 1.4826 + 1e-4
        cand = np.abs(prof) > max(0.012, 4 * noise)
        # group adjacent columns/rows, keep thin groups (folds are a few % of the page wide)
        i = 0
        while i < n:
            if not cand[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and cand[j + 1]:
                j += 1
            width = j - i + 1
            if width <= max(3, int(0.03 * n)):
                # coverage: fraction of the fold's length where the ridge is present
                band = line[:, i:j + 1] if axis == "vertical" else line[i:j + 1, :]
                sign = np.sign(prof[i:j + 1].mean())
                cover = float(((band * sign) > noise * 2).mean())
                if cover > 0.45:
                    folds.append({"axis": axis, "from": int(i), "to": int(j),
                                  "strength": round(float(np.abs(prof[i:j + 1]).max()), 4), "coverage": round(cover, 2)})
                    seg = line[:, max(0, i - 2):j + 3] if axis == "vertical" else line[max(0, i - 2):j + 3, :]
                    seg = cv2.GaussianBlur(seg, (0, 0), 1.2)
                    if axis == "vertical":
                        S[:, max(0, i - 2):j + 3] *= (1 + seg)
                    else:
                        S[max(0, i - 2):j + 3, :] *= (1 + seg)
            i = j + 1
    return np.clip(S, 0.7, 1.3), folds


# ---------------------------------------------------------------- ink enhancement
def enhance_ink(rgb: np.ndarray, m: dict, paper_rgb: np.ndarray, gamma: float = 0.75) -> tuple[np.ndarray, dict]:
    """Darken faded strokes. Only pixels inside the ink mask (plus a 1 px soft edge) change, and
    the mapping is monotonic, so stroke shapes and widths are unchanged."""
    lum = _lum(rgb)
    pl = max(1.0, float(_lum(paper_rgb[None, None, :])[0, 0]))
    d = np.clip(1 - lum / pl, 0, 1)  # darkness relative to restored paper
    ink = m["ink"]
    if ink.sum() < 20:
        return rgb, {"ink_pixels": int(ink.sum())}
    d_ref = float(np.percentile(d[ink], 90))  # well-inked stroke darkness
    target = max(d_ref, 0.55)
    dn = np.clip(d / max(d_ref, 1e-3), 0, 1)
    d_new = np.maximum(d, target * dn ** gamma)
    soft = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 0.7)
    soft = np.maximum(soft, ink.astype(np.float32))
    d_out = d + (d_new - d) * soft
    scale = np.where(d < 0.999, (1 - d_out) / np.maximum(1 - d, 1e-3), 1.0)
    out = rgb * scale[..., None]
    return np.clip(out, 0, 255), {"ink_pixels": int(ink.sum()), "faded_ink_ref": round(d_ref, 3),
                                  "ink_target": round(target, 3)}


def smooth_paper(rgb: np.ndarray, protect: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """Edge-preserving smoothing of paper texture, away from ink only."""
    u8 = np.clip(rgb, 0, 255).astype(np.uint8)
    sm = cv2.bilateralFilter(u8, 7, 18, 5).astype(np.float32)
    far = cv2.dilate(protect.astype(np.uint8), np.ones((5, 5), np.uint8)) == 0
    a = cv2.GaussianBlur(far.astype(np.float32), (0, 0), 1.5)[..., None] * strength
    return rgb * (1 - a) + sm * a


# ---------------------------------------------------------------- whole stage
def restore(img: Image.Image, tone: str = "aged", stages: dict | None = None) -> tuple[Image.Image, dict]:
    """Stain normalisation -> fold reduction -> texture smoothing -> ink enhancement."""
    m = ink_mask(img)
    info = {"stroke_width_px": round(m["sw"], 2), "ink_pct": round(100 * float(m["ink"].mean()), 2)}
    norm, s_info = normalize_paper(img, m, tone)
    info.update(s_info)
    if stages is not None:
        stages["ink_mask"] = Image.fromarray(np.where(m["ink"], 0, 255).astype(np.uint8))
        stages["paper_normalized"] = Image.fromarray(norm.astype(np.uint8))
    S, folds = fold_map(_lum(norm), m["protect"])
    info["folds"] = folds
    defold = norm / S[..., None] if folds else norm
    if stages is not None:
        stages["folds_reduced"] = Image.fromarray(np.clip(defold, 0, 255).astype(np.uint8))
    paper_rgb = np.array(s_info["paper_tone_rgb"], np.float32)
    smooth = smooth_paper(defold, m["protect"])
    out, e_info = enhance_ink(smooth, m, paper_rgb)
    info.update(e_info)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), info


# ---------------------------------------------------------------- quality checks
def quality(original: Image.Image, stage: Image.Image, m: dict | None = None) -> dict:
    """Compare a stage with the original page (same size).

    stroke_preservation: share of original ink pixels that are still darker than their local
        paper in the stage (1.0 = nothing erased)
    dot_preservation:    same, for small ink components (dots, punctuation)
    created_ink_pct:     stage ink pixels far from any original ink (possible artefacts)
    stain_std:           std of the smoothed paper layer on clean paper (lower = cleaner)
    ink_contrast:        median darkness of ink relative to paper (higher = more visible)
    """
    if stage.size != original.size:
        return {"error": f"size mismatch {stage.size} vs {original.size}"}
    m = m or ink_mask(original)
    ink, protect, sw = m["ink"], m["protect"], m["sw"]
    lum_s = _lum(_rgbf(stage))
    P_s = paper_layer(lum_s, sw)
    dark_s = 1 - np.clip(lum_s / P_s, 0, 1.5)
    kept = dark_s > max(0.03, m["thr"] * 0.5)
    sp = float(kept[ink].mean()) if ink.any() else None
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    small = np.zeros(n, bool)
    small[1:] = st[1:, cv2.CC_STAT_AREA] <= max(12, int(sw * sw * 3))
    dots = small[lab]
    dp = float(kept[dots].mean()) if dots.any() else None
    s_ink = ink_mask(stage)["ink"]
    far = cv2.dilate(protect.astype(np.uint8), np.ones((5, 5), np.uint8)) == 0
    created = float((s_ink & far).mean())
    clean = ~cv2.dilate(protect.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    stain = float(np.std(cv2.GaussianBlur(P_s, (0, 0), 8)[clean]))
    contrast = float(np.median(dark_s[ink])) if ink.any() else None
    _, folds = fold_map(lum_s, protect)
    return {
        "stroke_preservation": round(sp, 4) if sp is not None else None,
        "dot_preservation": round(dp, 4) if dp is not None else None,
        "created_ink_pct": round(100 * created, 3),
        "stain_std": round(stain, 2),
        "ink_contrast": round(contrast, 3) if contrast is not None else None,
        "fold_strength": round(sum(f["strength"] for f in folds), 4),
        "size": list(stage.size),
    }
