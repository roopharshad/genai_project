"""Download the pretrained weights DocRestore AI needs (they are too large for git).

Usage:
  python scripts/download_models.py          # required for document restoration (~380 MB)
  python scripts/download_models.py --all    # also photo models (GFPGAN, Real-ESRGAN, colourization)

Existing files with the expected size are skipped, so the script is safe to re-run.
PaddleOCR downloads its own models (~20 MB) on first use.
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ("DocRes-master/checkpoints/docres.pkl",
     "https://huggingface.co/spaces/qubvel-hf/documents-restoration/resolve/main/checkpoints/docres.pkl", 150_000_000),
    ("models/lama/big-lama.pt",
     "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt", 190_000_000),
]
OPTIONAL = [
    ("GFPGAN-master/experiments/pretrained_models/GFPGANv1.4.pth",
     "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth", 300_000_000),
    ("GFPGAN-master/gfpgan/weights/detection_Resnet50_Final.pth",
     "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth", 100_000_000),
    ("GFPGAN-master/gfpgan/weights/parsing_parsenet.pth",
     "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth", 80_000_000),
    ("models/realesrgan/RealESRGAN_x2plus.pth",
     "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth", 60_000_000),
    ("models/colorization/colorization_deploy_v2.prototxt",
     "https://raw.githubusercontent.com/richzhang/colorization/caffe/colorization/models/colorization_deploy_v2.prototxt", 5_000),
    ("models/colorization/pts_in_hull.npy",
     "https://raw.githubusercontent.com/richzhang/colorization/caffe/colorization/resources/pts_in_hull.npy", 4_000),
    ("models/colorization/colorization_release_v2.caffemodel",
     "https://huggingface.co/spaces/BilalSardar/Black-N-White-To-Color/resolve/main/colorization_release_v2.caffemodel", 120_000_000),
]


def fetch(rel: str, url: str, min_size: int) -> bool:
    dest = ROOT / rel
    if dest.is_file() and dest.stat().st_size >= min_size:
        print(f"ok       {rel} ({dest.stat().st_size / 1e6:.0f} MB)")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"download {rel}")
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        print(f"FAILED   {rel}: {exc}")
        return False
    if tmp.stat().st_size < min_size:
        print(f"FAILED   {rel}: file too small ({tmp.stat().st_size} bytes)")
        tmp.unlink()
        return False
    tmp.replace(dest)
    print(f"saved    {rel} ({dest.stat().st_size / 1e6:.0f} MB)")
    return True


if __name__ == "__main__":
    try:
        import truststore
        truststore.inject_into_ssl()  # use the OS certificate store (needed on some Windows setups)
    except ImportError:
        pass
    items = REQUIRED + (OPTIONAL if "--all" in sys.argv else [])
    results = [fetch(*item) for item in items]
    required_ok = all(results[:len(REQUIRED)])
    print("\nrequired models:", "ready" if required_ok else "MISSING (document restoration will not work)")
    sys.exit(0 if required_ok else 1)
