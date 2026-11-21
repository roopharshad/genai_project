"""Compare original vs DocRes vs DocRes+DocDiff vs DocRes+text refinement with PaddleOCR CER/WER.

Usage: python scripts/text_eval.py ORIGINAL DOCRES_OUTPUT GROUND_TRUTH.txt [DOCDIFF_OUTPUT]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import truststore  # noqa: E402

truststore.inject_into_ssl()
import torch  # noqa: E402,F401  (load torch before paddle on Windows)
from PIL import Image  # noqa: E402

from backend.services import ocr_service as o, text_refine_service as tr  # noqa: E402

orig_p, docres_p, gt_p = sys.argv[1:4]
docdiff_p = sys.argv[4] if len(sys.argv) > 4 else None
gt = Path(gt_p).read_text(encoding="utf-8")
orig, docres = Image.open(orig_p).convert("RGB"), Image.open(docres_p).convert("RGB")

ol = o.read(orig)
dl = o.read(docres)
mask = o.text_boxes(ol, (orig.height, orig.width)) | o.text_boxes(dl, (orig.height, orig.width))
ref, stats = tr.refine(orig, docres, mask)
ref, nspecks = tr.remove_dark_specks(ref, mask, dl)
stats["specks_removed"] = nspecks
rl = o.read(ref)
guarded, gl, reverted = tr.line_guard(orig, ref, ol, rl, o.read)
if reverted:  # fallback lines come from the original: clean their specks too, then re-read
    guarded, n2 = tr.remove_dark_specks(guarded, mask, gl)
    stats["specks_removed_after_guard"] = n2
    gl = o.read(guarded)
stem = Path(orig_p).stem
ref.save(f"samples/stage_refined_{stem}.png")
guarded.save(f"samples/stage_final_{stem}.png")

rows = [("original", ol), ("docres", dl), ("docres+refine", rl), ("final (refine+guard)", gl)]
if docdiff_p:
    rows.insert(2, ("docres+docdiff", o.read(Image.open(docdiff_p))))
print(f"{'stage':24} {'CER':>7} {'WER':>7} {'conf':>6}")
for name, lines in rows:
    t = o.joined(lines)
    conf = sum(l["score"] for l in lines) / max(1, len(lines))
    print(f"{name:24} {o.cer(gt, t):7.4f} {o.wer(gt, t):7.4f} {conf:6.3f}")
print("refine stats:", stats)
print("reverted lines:", json.dumps(reverted, ensure_ascii=False))
print("--- final text ---")
print(o.joined(gl))
