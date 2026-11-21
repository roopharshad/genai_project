"""Score the saved stages of one pipeline run with PaddleOCR and write a before/after image.

Usage: python scripts/stage_report.py webapp/storage/stages/<run_id> [ground_truth.txt]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw  # noqa: E402

from backend.services import ocr_service as o  # noqa: E402

if __name__ == "__main__":
    d = Path(sys.argv[1])
    gt = Path(sys.argv[2]).read_text(encoding="utf-8") if len(sys.argv) > 2 else None
    ol = o.read(Image.open(d / "1_preprocessed.png"))
    print(f"{'stage':16} {'agree':>7} {'miss':>5} {'chg':>5} {'conf':>6}" + ("   CER     WER" if gt else ""))
    for s in ["1_preprocessed", "2_docres", "3_text_refined", "4_ocr_guarded", "5_final"]:
        if not (d / f"{s}.png").exists():
            continue
        lines = o.read(Image.open(d / f"{s}.png"))
        c = o.compare(ol, lines)
        row = f"{s:16} {c['char_agreement']:7} {len(c['missing']):5} {len(c['changed']):5} {c['restored_mean_confidence']:6}"
        if gt:
            t = o.joined(lines)
            row += f"  {o.cer(gt, t):.4f}  {o.wer(gt, t):.4f}"
        print(row)
    names = [("ORIGINAL (page)", "1_preprocessed"), ("DOCRES", "2_docres"), ("FINAL", "5_final")]
    ims = [Image.open(d / f"{p}.png").convert("RGB") for _, p in names]
    w = 1000
    ims = [im.resize((w, int(im.height * w / im.width)), Image.LANCZOS) for im in ims]
    canvas = Image.new("RGB", (w, sum(im.height + 24 for im in ims)), "white")
    dr = ImageDraw.Draw(canvas)
    y = 0
    for (n, _), im in zip(names, ims):
        dr.text((4, y + 5), n, fill="red")
        canvas.paste(im, (0, y + 22))
        y += im.height + 24
    out = d / "comparison.png"
    canvas.save(out)
    print("comparison image:", out)
