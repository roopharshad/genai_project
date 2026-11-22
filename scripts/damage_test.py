"""Run damage detection + model selection on sample documents and save damage maps."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from backend.services import damage_service as ds  # noqa: E402

files = sys.argv[1:] or ["samples/faded_document.jpg", "samples/old_book_page.jpg", "samples/docs/letter_john.png",
                         "samples/docs/letter_newyork.png", "samples/docs/letter_dense.png", "samples/damaged_bw_photo.jpg"]
out = Path("samples/damage_eval")
out.mkdir(parents=True, exist_ok=True)
for f in files:
    im = Image.open(f).convert("RGB")
    t = time.time()
    r = ds.detect(im)
    dt = time.time() - t
    print(f"== {Path(f).name} {im.size} {dt:.1f}s score={r['damage_score']}")
    for k, v in r["damages"].items():
        print(f"   {k:18} {v['level']:8} {v['severity']:.2f}  {v['evidence']}")
    print("   plan:", [p["stage"] for p in ds.plan(r) if p["run"]])
    ds.overlay(im, r["masks"]).save(out / f"{Path(f).stem}_damage.png")
