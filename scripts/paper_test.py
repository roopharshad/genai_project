"""Run the paper-restoration stage on sample documents; print quality metrics and save sheets."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw  # noqa: E402

from backend.services import paper_restore_service as pr  # noqa: E402

files = sys.argv[1:] or ["samples/docs/letter_newyork.png", "samples/docs/letter_john.png", "samples/docs/letter_dense.png"]
out_dir = Path("samples/paper_eval")
out_dir.mkdir(parents=True, exist_ok=True)
for f in files:
    im = Image.open(f).convert("RGB")
    t = time.time()
    st = {}
    out, info = pr.restore(im, "aged", st)
    dt = time.time() - t
    m = pr.ink_mask(im)
    q0 = pr.quality(im, im, m)
    q1 = pr.quality(im, out, m)
    stem = Path(f).stem
    out.save(out_dir / f"{stem}_restored.png")
    for k, v in st.items():
        v.save(out_dir / f"{stem}_{k}.png")
    print(f"== {stem} {im.size} {dt:.1f}s info={ {k: v for k, v in info.items() if k != 'folds'} }")
    print("   folds:", info["folds"])
    print("   original:", q0)
    print("   restored:", q1)
    h = 560
    a = im.resize((int(im.width * h / im.height), h))
    b = out.resize((int(out.width * h / out.height), h))
    c = Image.new("RGB", (a.width + b.width + 10, h + 20), "white")
    d = ImageDraw.Draw(c)
    d.text((4, 2), "ORIGINAL", fill="red")
    d.text((a.width + 14, 2), "PAPER RESTORED", fill="red")
    c.paste(a, (0, 20))
    c.paste(b, (a.width + 10, 20))
    c.save(out_dir / f"{stem}_cmp.png")
