"""Run DocRes on sample pages and save before/after comparisons to samples/."""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(message)s")
from PIL import Image  # noqa: E402

from backend.services import docres_service as d  # noqa: E402

print("available:", d.available(), flush=True)
files = sys.argv[1:] or ["samples/docres_for_deshadowing.jpg", "samples/old_book_page.jpg", "samples/faded_document.jpg"]
for f in files:
    im = Image.open(f).convert("RGB")
    t = time.time()
    out, steps = d.restore(im, "end2end")
    stem = Path(f).stem
    out.save(f"samples/docres_out_{stem}.png")
    h = 420
    a = im.resize((int(im.width * h / im.height), h))
    b = out.resize((int(out.width * h / out.height), h))
    c = Image.new("RGB", (a.width + b.width + 10, h), "white")
    c.paste(a, (0, 0))
    c.paste(b, (a.width + 10, 0))
    c.save(f"samples/docres_cmp_{stem}.png")
    print(f"{f} {im.size} -> {out.size} {time.time() - t:.1f}s {steps}", flush=True)
print("ALLDONE", flush=True)
