"""Check document detection and document restoration quality on local samples."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from backend.services import enhance_service as es  # noqa: E402

files = ["samples/faded_document.jpg", "samples/old_book_page.jpg", "samples/damaged_bw_photo.jpg",
         "GFPGAN-master/inputs/whole_imgs/Blake_Lively.jpg", "GFPGAN-master/inputs/whole_imgs/00.jpg",
         "GFPGAN-master/inputs/whole_imgs/10045.png"] + sys.argv[1:]
for f in files:
    im = Image.open(f).convert("RGB")
    t = time.time()
    print(f"{f}: is_document={es.is_document(im)} ({time.time() - t:.2f}s) {es.document_score(im)}")

for f in ["samples/faded_document.jpg", "samples/old_book_page.jpg"]:
    im = Image.open(f).convert("RGB")
    for style in ("aged", "color", "bw"):
        t = time.time()
        out, notes = es.enhance_document(im, 2, style)
        out.save(f"samples/chk_{Path(f).stem}_{style}.png")
        print(style, f, f"{time.time() - t:.1f}s", notes)
