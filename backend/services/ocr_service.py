"""PaddleOCR text verification (read-only: OCR never edits the restored image).

Uses PaddleOCR 3.x with the PP-OCRv5 *mobile* detection/recognition models (CPU friendly).
Models are downloaded once by PaddleX into ~/.paddlex/official_models.

Functions
- read(img)            -> list of {text, score, box}
- compare(orig, rest)  -> text-preservation report (characters/words present in the original
                          reading that are missing or changed in the restored reading)
- cer / wer            -> standard edit-distance error rates (for ground-truth evaluation)
"""
import logging
import os
import re
import threading
import time
from difflib import SequenceMatcher

import numpy as np
from PIL import Image

log = logging.getLogger("docrestore.ocr")

_ocr = None
_lock = threading.Lock()  # serialises requests to the worker
_local_lock = threading.Lock()  # guards the in-process engine
_error: str | None = None
DET_MODEL = os.getenv("OCR_DET_MODEL", "PP-OCRv5_mobile_det")
REC_MODEL = os.getenv("OCR_REC_MODEL", "PP-OCRv5_mobile_rec")


def available() -> tuple[bool, str]:
    global _error
    if _error is None:
        try:
            import paddleocr  # noqa: F401
            _error = ""
        except Exception as exc:  # noqa: BLE001
            _error = f"{type(exc).__name__}: {exc}"
    return _error == "", _error or "ok"


def _accept_installed_opencv():
    """PaddleX checks for the 'opencv-contrib-python' *distribution* by name (importlib.metadata).
    The project already ships OpenCV 4.x as opencv-python-headless; installing a second cv2 build
    into the same folder would conflict. The OCR pipeline only uses core cv2 functions, so report
    the installed cv2 for that name. Must run before paddlex is imported."""
    import importlib.metadata as md
    if getattr(md.version, "_docrestore", False):
        return
    import cv2
    orig = md.version
    aliases = {"opencv-contrib-python": "4.10.0.84", "opencv-python": cv2.__version__}

    def version(name):
        try:
            return orig(name)
        except md.PackageNotFoundError:
            if name in aliases:
                return aliases[name]
            raise

    version._docrestore = True
    md.version = version


_accept_installed_opencv()


def _engine():
    global _ocr
    if _ocr is None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        t = time.time()
        _ocr = PaddleOCR(
            text_detection_model_name=DET_MODEL,
            text_recognition_model_name=REC_MODEL,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device=os.getenv("OCR_DEVICE", "cpu"),
            # Paddle 3.3 oneDNN kernels fail on these models ("ConvertPirAttribute2RuntimeAttribute
            # not support"); the plain CPU kernels work.
            enable_mkldnn=os.getenv("OCR_MKLDNN", "0") == "1",
        )
        log.info("PaddleOCR (%s / %s) ready in %.1fs", DET_MODEL, REC_MODEL, time.time() - t)
    return _ocr


# ---------------------------------------------------------------- isolated worker process
# PyTorch and Paddle each bundle their own MKL / OpenMP DLLs. Loading both into one Windows
# process crashed the web server natively (no Python traceback). OCR therefore runs in a
# separate process that never imports torch; if it dies, the job gets a normal error and the
# worker is restarted on the next request.
_proc = None
_conn = None
WORKER_TIMEOUT = int(os.getenv("OCR_TIMEOUT_SECONDS", "300"))


def _worker(conn):
    import io as _io
    while True:
        try:
            msg = conn.recv()
        except EOFError:
            return
        if msg is None:
            return
        try:
            conn.send(("ok", _read_local(Image.open(_io.BytesIO(msg)))))
        except Exception as exc:  # noqa: BLE001
            conn.send(("err", f"{type(exc).__name__}: {exc}"))


def _ensure_worker():
    global _proc, _conn
    import multiprocessing as mp
    if _proc is not None and _proc.is_alive():
        return
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe()
    _proc = ctx.Process(target=_worker, args=(child,), daemon=True, name="docrestore-ocr")
    _proc.start()
    _conn = parent
    log.info("OCR worker process started (pid %s)", _proc.pid)


def read(img: Image.Image) -> list[dict]:
    """OCR an image (in the worker process). Lines are in reading order."""
    ok, why = available()
    if not ok:
        raise RuntimeError(f"PaddleOCR unavailable: {why}")
    if os.getenv("OCR_IN_PROCESS", "0") == "1":
        return _read_local(img)
    import io as _io
    buf = _io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    with _lock:
        _ensure_worker()
        try:
            _conn.send(buf.getvalue())
            if not _conn.poll(WORKER_TIMEOUT):
                raise TimeoutError(f"OCR timed out after {WORKER_TIMEOUT}s")
            status, payload = _conn.recv()
        except (EOFError, BrokenPipeError, OSError, TimeoutError) as exc:
            if _proc is not None:
                _proc.kill()
            raise RuntimeError(f"OCR worker failed: {exc}") from exc
    if status != "ok":
        raise RuntimeError(f"OCR failed: {payload}")
    return payload


def _read_local(img: Image.Image) -> list[dict]:
    arr = np.asarray(img.convert("RGB"))[:, :, ::-1].copy()  # BGR, as PaddleOCR expects
    with _local_lock:
        res = list(_engine().predict(arr))
    lines = []
    for page in res:
        d = page.json["res"] if hasattr(page, "json") else page
        for text, score, poly in zip(d.get("rec_texts", []), d.get("rec_scores", []), d.get("rec_polys", d.get("dt_polys", []))):
            p = np.asarray(poly, dtype=float).reshape(-1, 2)
            x0, y0 = p.min(0)
            x1, y1 = p.max(0)
            lines.append({"text": text, "score": round(float(score), 4),
                          "box": [int(x0), int(y0), int(x1), int(y1)]})
    # reading order: group by line (y), then x
    lines.sort(key=lambda l: (round(l["box"][1] / max(8, (l["box"][3] - l["box"][1]) * 0.6)), l["box"][0]))
    return lines


def text_boxes(lines: list[dict], shape) -> np.ndarray:
    """Boolean mask of detected text regions (slightly padded)."""
    h, w = shape[:2]
    m = np.zeros((h, w), bool)
    for l in lines:
        x0, y0, x1, y1 = l["box"]
        pad = max(2, (y1 - y0) // 4)
        m[max(0, y0 - pad):min(h, y1 + pad), max(0, x0 - pad):min(w, x1 + pad)] = True
    return m


# ---------------------------------------------------------------- metrics
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("×", "x")).strip()


def _lev(a, b) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    ref, hyp = _norm(ref), _norm(hyp)
    return round(_lev(ref, hyp) / max(1, len(ref)), 4)


def wer(ref: str, hyp: str) -> float:
    r, h = _norm(ref).split(), _norm(hyp).split()
    return round(_lev(r, h) / max(1, len(r)), 4)


def joined(lines: list[dict]) -> str:
    return "\n".join(l["text"] for l in lines)


def _iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def match_lines(orig_lines: list[dict], rest_lines: list[dict]) -> list[tuple[dict, dict | None]]:
    """Pair each original line with the restored line at the same position (order-independent)."""
    pairs = []
    for ol in orig_lines:
        best = max(rest_lines, key=lambda r: _iou(ol["box"], r["box"]), default=None)
        pairs.append((ol, best if best is not None and _iou(ol["box"], best["box"]) >= 0.3 else None))
    return pairs


def line_agreement(orig_lines: list[dict], rest_lines: list[dict]) -> float | None:
    """Character agreement of position-matched lines, weighted by length; spaces ignored."""
    total = err = 0
    for ol, rl in match_lines(orig_lines, rest_lines):
        a = re.sub(r"\s+", "", _norm(ol["text"]))
        b = re.sub(r"\s+", "", _norm(rl["text"])) if rl else ""
        total += len(a)
        err += min(len(a), _lev(a, b))
    return round(1 - err / total, 4) if total else None


def compare(orig_lines: list[dict], rest_lines: list[dict], min_conf: float = 0.0) -> dict:
    """Report characters/words that the original reading has but the restored reading lost or changed.

    The original's OCR is not ground truth (it may itself be wrong on degraded input); this
    measures *agreement*, and lists every disagreement for review.
    """
    a, b = _norm(joined(orig_lines)), _norm(joined(rest_lines))
    missing, changed, added = [], [], []
    for ol, rl in match_lines(orig_lines, rest_lines):  # compare line by line, by position
        la, lb = _norm(ol["text"]), _norm(rl["text"]) if rl else ""
        if rl is None:
            missing.append({"original": la, "context": "whole line not found", "box": ol["box"]})
            continue
        for op, i1, i2, j1, j2 in SequenceMatcher(None, la, lb, autojunk=False).get_opcodes():
            ctx = la[max(0, i1 - 12):min(len(la), i2 + 12)]
            if op == "delete" and la[i1:i2].strip():
                missing.append({"original": la[i1:i2], "context": ctx, "box": ol["box"]})
            elif op == "replace":
                changed.append({"original": la[i1:i2], "restored": lb[j1:j2], "context": ctx, "box": ol["box"]})
            elif op == "insert" and lb[j1:j2].strip():
                added.append({"restored": lb[j1:j2], "context": lb[max(0, j1 - 12):min(len(lb), j2 + 12)], "box": ol["box"]})
    ow, rw = a.split(), b.split()
    wsm = SequenceMatcher(None, ow, rw, autojunk=False)
    words_kept = sum(t.size for t in wsm.get_matching_blocks())
    conf = lambda ls: round(float(np.mean([l["score"] for l in ls])), 4) if ls else None  # noqa: E731
    return {
        "original_text": joined(orig_lines),
        "restored_text": joined(rest_lines),
        "original_lines": len(orig_lines),
        "restored_lines": len(rest_lines),
        "original_mean_confidence": conf(orig_lines),
        "restored_mean_confidence": conf(rest_lines),
        "char_agreement": line_agreement(orig_lines, rest_lines),
        "word_agreement": round(words_kept / max(1, len(ow)), 4) if ow else None,
        "cer_vs_original_reading": cer(a, b) if a else None,
        "wer_vs_original_reading": wer(a, b) if a else None,
        "missing": missing,
        "changed": changed,
        "added": added,
        "low_confidence_lines": [l for l in rest_lines if l["score"] < 0.8],
    }
