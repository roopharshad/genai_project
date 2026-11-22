"""Final enhancement step, run after restoration, validation and evaluation have finished.

The restored page is sent to the image model configured in GEMINI_IMAGE_MODEL (.env). The page
is padded to the nearest supported aspect ratio so it cannot be stretched, and the result is
cropped back to the exact restored size. The enhanced image is always saved separately; it is
accepted only if PaddleOCR reads the same text as on the restored page (validate()).
Provider and model details are kept on the server: they are logged, never returned to the UI.
"""
import base64
import io
import logging
import os
import time

import httpx
import numpy as np
import truststore
from PIL import Image

from .. import config  # noqa: F401  (loads .env)
from . import ocr_service

truststore.inject_into_ssl()
log = logging.getLogger("docrestore.enhancement")

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RATIOS = {"1:1": 1.0, "2:3": 2 / 3, "3:2": 1.5, "3:4": 0.75, "4:3": 4 / 3, "4:5": 0.8, "5:4": 1.25,
          "9:16": 9 / 16, "16:9": 16 / 9, "21:9": 21 / 9}
PROMPT = (
    "This is a scanned historical document that has already been restored. Produce a cleaner version of "
    "the SAME page. Strict rules: keep every character, word, number, punctuation mark, handwriting stroke, "
    "line break, margin and position exactly where it is; do not add, remove, correct, translate, retype or "
    "re-letter any text; do not change the handwriting style or the font. You may only: whiten and even out "
    "the paper background, remove remaining stains, specks and dust, increase ink contrast, and sharpen "
    "existing strokes. Return only the image."
)


class EnhancementError(RuntimeError):
    pass


def enabled() -> bool:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    return (bool(key) or _cloudflare_ready()) and os.getenv("ENHANCEMENT_ENABLED", "0") == "1"


def _pad(img: Image.Image) -> tuple[Image.Image, str, tuple[int, int, int, int]]:
    """Pad with the page's own paper colour to the closest supported ratio."""
    w, h = img.size
    r = w / h
    name = min(RATIOS, key=lambda k: abs(np.log(RATIOS[k] / r)))
    target = RATIOS[name]
    if target > r:
        nw, nh = round(h * target), h
    else:
        nw, nh = w, round(w / target)
    rgb = np.asarray(img.convert("RGB"))
    paper = tuple(int(v) for v in np.percentile(rgb.reshape(-1, 3), 90, axis=0))
    canvas = Image.new("RGB", (nw, nh), paper)
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    canvas.paste(img.convert("RGB"), (x0, y0))
    return canvas, name, (x0, y0, x0 + w, y0 + h)


def _cloudflare_ready() -> bool:
    return bool((os.getenv("CLOUDFLARE_API_TOKEN") or "").strip() and (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip())


def _cloudflare(img: Image.Image, timeout: float) -> tuple[Image.Image, dict]:
    """Workers AI FLUX.2 image editing: the restored page is the reference image."""
    tok = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    acc = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    model = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-9b")
    w, h = img.size
    side = int(os.getenv("ENHANCEMENT_MAX_SIDE", "1024"))
    s = min(1.0, side / max(w, h))
    tw, th = max(256, round(w * s / 16) * 16), max(256, round(h * s / 16) * 16)
    send = img.convert("RGB").resize((tw, th), Image.LANCZOS)
    buf = io.BytesIO()
    send.save(buf, "PNG")
    fields = {"prompt": PROMPT, "width": str(tw), "height": str(th)}
    if os.getenv("CLOUDFLARE_IMAGE_STEPS"):
        fields["steps"] = os.getenv("CLOUDFLARE_IMAGE_STEPS")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
    t = time.time()
    last = ""
    for attempt in range(2):
        try:
            r = httpx.post(url, headers={"Authorization": f"Bearer {tok}"}, data=fields,
                           files={"input_image_0": ("page.png", buf.getvalue(), "image/png")}, timeout=timeout)
        except httpx.HTTPError as exc:
            last = f"network error {type(exc).__name__}"
            time.sleep(2)
            continue
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if ct.startswith("image/"):
                raw = r.content
            else:
                res = r.json().get("result") or r.json()
                if not res.get("image"):
                    last = f"no image in response: {str(r.json())[:200]}"
                    break
                raw = base64.b64decode(res["image"])
            out = Image.open(io.BytesIO(raw)).convert("RGB")
            native = out.size
            info = {"elapsed_s": round(time.time() - t, 1), "native_size": list(native), "provider": "cf"}
            log.info("enhancement via %s: %s", model, info)
            return out.resize((w, h), Image.LANCZOS), info
        last = f"HTTP {r.status_code} {r.text[:300].replace(tok, '***')}"
        log.warning("enhancement attempt %d failed: %s", attempt + 1, last)
        if r.status_code in (400, 401, 403, 404) or (r.status_code == 429 and ("allocation" in r.text or "quota" in r.text.lower())):
            break  # daily quota / auth errors do not clear within a job
        time.sleep(3)
    raise EnhancementError(last or "enhancement failed")


def enhance(img: Image.Image, timeout: float = 180) -> tuple[Image.Image, dict]:
    """Return (enhanced image at exactly img.size, info). Raises EnhancementError.
    Provider: Cloudflare Workers AI when its credentials are set, otherwise Gemini."""
    if _cloudflare_ready() and os.getenv("ENHANCEMENT_PROVIDER", "cloudflare") == "cloudflare":
        return _cloudflare(img, timeout)
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise EnhancementError("enhancement is not configured")
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
    padded, ratio, box = _pad(img)
    send = padded.copy()
    send.thumbnail((2048, 2048), Image.LANCZOS)
    buf = io.BytesIO()
    send.save(buf, "PNG")
    body = {
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}},
            {"text": PROMPT}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "temperature": 0.1,
                             "imageConfig": {"aspectRatio": ratio, "imageSize": os.getenv("ENHANCEMENT_IMAGE_SIZE", "2K")}},
    }
    t = time.time()
    last = ""
    for attempt in range(3):
        try:
            r = httpx.post(API.format(model=model), json=body, headers={"x-goog-api-key": key}, timeout=timeout)
        except httpx.HTTPError as exc:
            last = f"network error {type(exc).__name__}"
            time.sleep(2)
            continue
        if r.status_code == 400 and "imageSize" in r.text and "imageSize" in body["generationConfig"]["imageConfig"]:
            body["generationConfig"]["imageConfig"].pop("imageSize")  # model without size control
            continue
        if r.status_code == 200:
            parts = ((r.json().get("candidates") or [{}])[0].get("content") or {}).get("parts", [])
            data = next((p.get("inlineData") or p.get("inline_data") for p in parts
                         if (p.get("inlineData") or p.get("inline_data"))), None)
            if not data:
                last = f"no image in response ({(r.json().get('candidates') or [{}])[0].get('finishReason')})"
                break
            out = Image.open(io.BytesIO(base64.b64decode(data["data"]))).convert("RGB")
            native = out.size
            out = out.resize(padded.size, Image.LANCZOS).crop(box)
            info = {"elapsed_s": round(time.time() - t, 1), "native_size": list(native), "ratio": ratio}
            log.info("enhancement via %s: %s", model, info)
            return out, info
        last = f"HTTP {r.status_code} {r.text[:200].replace(key, '***')}"
        log.warning("enhancement attempt %d failed: %s", attempt + 1, last)
        if r.status_code in (401, 403, 404) or (r.status_code == 429 and "quota" in r.text.lower()):
            break  # quota / auth errors do not clear within a restoration job
        time.sleep(3 * (attempt + 1))
    raise EnhancementError(last or "enhancement failed")


def safe_composite(restored: Image.Image, enhanced: Image.Image) -> Image.Image:
    """Keep every restored ink pixel exactly; elsewhere take the enhanced pixel only where it is
    lighter (removes leftover stains/specks, can never add a dark mark or redraw a letter)."""
    import cv2
    from . import paper_restore_service as paper
    r = np.asarray(restored.convert("RGB")).astype(np.float32)
    e = np.asarray(enhanced.convert("RGB").resize(restored.size, Image.LANCZOS)).astype(np.float32)
    m = paper.ink_mask(restored)
    keep = cv2.dilate((m["protect"] | m["uncertain"]).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    keep = np.maximum(cv2.GaussianBlur(keep, (0, 0), 1.2), keep)[..., None]
    lum = lambda a: a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114  # noqa: E731
    lighter = (lum(e) > lum(r))[..., None].astype(np.float32)
    out = r * keep + (1 - keep) * (e * lighter + r * (1 - lighter))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def ink_check(restored: Image.Image, candidate: Image.Image) -> dict:
    from . import paper_restore_service as paper
    q = paper.quality(restored, candidate)
    ok = ((q.get("stroke_preservation") or 0) >= 0.99 and (q.get("dot_preservation") or 1) >= 0.99
          and q.get("created_ink_pct", 100) <= 0.05)
    return {"ok": ok, "stroke_preservation": q.get("stroke_preservation"),
            "dot_preservation": q.get("dot_preservation"), "created_ink_pct": q.get("created_ink_pct")}


def public_reason(exc: Exception) -> str:
    """User-facing reason without provider details."""
    s = str(exc)
    if "429" in s:
        return "enhancement service quota reached"
    if "401" in s or "403" in s:
        return "enhancement service not authorised"
    if "not configured" in s:
        return "enhancement not configured"
    return "enhancement service unavailable"


def run(restored: Image.Image, restored_lines: list | None = None, progress=None) -> dict:
    """Full final step: enhance, validate with PaddleOCR, fall back to the ink-safe composite.
    Returns {"accepted", "mode", "image", "candidate", "validation", "info"}; never raises."""
    notify = progress or (lambda v, s: None)
    try:
        notify(93, "Enhancement: processing page")
        enhanced, info = enhance(restored)
    except Exception as exc:  # noqa: BLE001
        log.warning("enhancement failed: %s", exc)
        return {"accepted": False, "mode": None, "image": None, "candidate": None, "info": {},
                "validation": {"reasons": [public_reason(exc)]}}
    notify(95, "Enhancement: verifying text with OCR")
    rl = restored_lines if restored_lines is not None else ocr_service.read(restored)
    v = validate(restored, enhanced, rl)
    if v["accepted"]:
        return {"accepted": True, "mode": "full", "image": enhanced, "candidate": enhanced, "validation": v, "info": info}
    notify(97, "Enhancement: verifying text-safe version with OCR")
    comp = safe_composite(restored, enhanced)
    v2 = validate(restored, comp, rl)
    ink = ink_check(restored, comp)
    v2["ink_check"] = ink
    v2["full_enhancement_rejected"] = v["reasons"]
    reliable = (v2["confidence_restored"] or 0) >= 0.85 and v2["lines_restored"] >= 3
    if not v2["accepted"] and not reliable and ink["ok"]:
        # Handwriting: OCR cannot read it reliably, but the composite keeps every ink pixel by
        # construction and the stroke/dot check confirms it, so it is accepted on that basis.
        v2["accepted"], v2["accepted_by"] = True, "ink_preservation (OCR unreliable on this text)"
    elif v2["accepted"]:
        v2["accepted_by"] = "ocr_agreement"
    v2["accepted"] = v2["accepted"] and ink["ok"]
    return {"accepted": v2["accepted"], "mode": "text_safe" if v2["accepted"] else None,
            "image": comp if v2["accepted"] else None, "candidate": enhanced, "composite": comp,
            "validation": v2, "info": info}


def validate(restored: Image.Image, enhanced: Image.Image, restored_lines: list | None = None) -> dict:
    """Accept the enhanced page only if PaddleOCR reads the same text as on the restored page."""
    min_agree = float(os.getenv("ENHANCEMENT_MIN_AGREEMENT", "0.97"))
    rl = restored_lines if restored_lines is not None else ocr_service.read(restored)
    el = ocr_service.read(enhanced)
    agree = ocr_service.line_agreement(rl, el)
    conf_r = float(np.mean([l["score"] for l in rl])) if rl else None
    conf_e = float(np.mean([l["score"] for l in el])) if el else None
    cmp_ = ocr_service.compare(rl, el)
    reasons = []
    if not rl:
        reasons.append("no text found on the restored page to verify against")
    if agree is None or agree < min_agree:
        reasons.append(f"text agreement {agree} below {min_agree}")
    if conf_r is not None and conf_e is not None and conf_e < conf_r - 0.03:
        reasons.append(f"OCR confidence dropped {conf_r:.3f} -> {conf_e:.3f}")
    if len(el) < len(rl) * 0.9:
        reasons.append(f"text lines dropped {len(rl)} -> {len(el)}")
    return {"accepted": not reasons, "reasons": reasons, "char_agreement": agree,
            "confidence_restored": round(conf_r, 4) if conf_r is not None else None,
            "confidence_enhanced": round(conf_e, 4) if conf_e is not None else None,
            "lines_restored": len(rl), "lines_enhanced": len(el),
            "missing": cmp_["missing"][:20], "changed": cmp_["changed"][:20], "added": cmp_["added"][:20],
            "enhanced_lines": el}
