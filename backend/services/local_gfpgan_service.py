"""Local GFPGAN inference using the bundled GFPGAN-master source (no internet needed).

Mirrors GFPGAN-master/inference_gfpgan.py: GFPGANer(model_path=GFPGANv1.4.pth, upscale, arch='clean',
channel_multiplier=2, bg_upsampler=None) and restorer.enhance(img, has_aligned=False,
only_center_face=False, paste_back=True).

Without a background upsampler (the official script also disables Real-ESRGAN on CPU),
faces are restored by GFPGAN and the rest of the image is resized with Lanczos.
Face detection / parsing weights (facexlib) are downloaded once into GFPGAN-master/gfpgan/weights.
"""
import contextlib
import logging
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .. import config

log = logging.getLogger("docrestore.gfpgan_local")

GFPGAN_DIR = config.ROOT_DIR / "GFPGAN-master"
WEIGHTS = {
    "v1.4": GFPGAN_DIR / "experiments" / "pretrained_models" / "GFPGANv1.4.pth",
}
_restorers: dict = {}
_lock = threading.Lock()
_import_error: str | None = None


def _patch_torchvision():
    """basicsr 1.4.2 imports torchvision.transforms.functional_tensor, removed in torchvision 0.17."""
    try:
        import torchvision.transforms.functional_tensor  # noqa: F401
    except ImportError:
        import types

        import torchvision.transforms.functional as F
        mod = types.ModuleType("torchvision.transforms.functional_tensor")
        mod.rgb_to_grayscale = F.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = mod


def available() -> tuple[bool, str]:
    global _import_error
    if not WEIGHTS["v1.4"].is_file():
        return False, f"missing weights {WEIGHTS['v1.4'].name}"
    if _import_error is None:
        try:
            _patch_torchvision()
            import basicsr  # noqa: F401
            import facexlib  # noqa: F401
            import torch  # noqa: F401
            _import_error = ""
        except Exception as exc:  # noqa: BLE001
            _import_error = f"{type(exc).__name__}: {exc}"
    return (_import_error == ""), _import_error or "ok"


@contextlib.contextmanager
def _in_gfpgan_dir():
    # GFPGANer stores facexlib weights under the relative path 'gfpgan/weights'.
    old = os.getcwd()
    os.chdir(GFPGAN_DIR)
    try:
        yield
    finally:
        os.chdir(old)


def _get(version: str, upscale: float):
    key = (version, upscale)
    if key not in _restorers:
        _patch_torchvision()
        if str(GFPGAN_DIR) not in sys.path:
            sys.path.insert(0, str(GFPGAN_DIR))
        from gfpgan import GFPGANer
        t = time.time()
        with _in_gfpgan_dir():
            _restorers[key] = GFPGANer(model_path=str(WEIGHTS[version]), upscale=upscale, arch="clean",
                                       channel_multiplier=2, bg_upsampler=None)
        log.info("loaded local GFPGAN %s x%s in %.1fs", version, upscale, time.time() - t)
    return _restorers[key]


def restore(img: Image.Image, scale: float = 2, weight: float = 0.5) -> tuple[Image.Image, int]:
    """Returns (restored image, number of faces restored)."""
    ok, why = available()
    if not ok:
        raise RuntimeError(f"Local GFPGAN unavailable: {why}")
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    with _lock:  # one inference at a time on CPU; also guards the cwd switch
        restorer = _get("v1.4", float(scale))
        t = time.time()
        with _in_gfpgan_dir():
            _, faces, out = restorer.enhance(bgr, has_aligned=False, only_center_face=False,
                                             paste_back=True, weight=weight)
        log.info("local GFPGAN: %d faces, %.1fs", len(faces), time.time() - t)
    if out is None:
        raise RuntimeError("GFPGAN returned no image.")
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)), len(faces)
