"""Time PaddleOCR reads (worker start, first read, warm reads) on a sample page."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import torch  # noqa: F401  (same import order as the server)
    from PIL import Image
    from backend.services import ocr_service

    img = Image.open(sys.argv[1] if len(sys.argv) > 1 else "samples/faded_document.jpg").convert("RGB")
    for i in range(3):
        t = time.time()
        lines = ocr_service.read(img)
        print(f"read {i + 1}: {time.time() - t:.1f}s, {len(lines)} lines, size {img.size}", flush=True)
