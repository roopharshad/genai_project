"""Local Real-ESRGAN x2plus background restoration using the official pretrained weight."""
import os
import sys
import threading
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .. import config

WEIGHT = config.ROOT_DIR / "models" / "realesrgan" / "RealESRGAN_x2plus.pth"
_lock = threading.Lock()
_upsampler = None
_error = None


def _patch_torchvision():
    try:
        import torchvision.transforms.functional_tensor  # noqa: F401
    except ImportError:
        import types
        import torchvision.transforms.functional as F
        mod = types.ModuleType("torchvision.transforms.functional_tensor")
        mod.rgb_to_grayscale = F.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = mod


def available() -> tuple[bool, str]:
    global _error
    if not WEIGHT.is_file() or WEIGHT.stat().st_size < 60_000_000:
        return False, "missing or incomplete RealESRGAN_x2plus.pth"
    if _error is None:
        try:
            _patch_torchvision()
            from basicsr.archs.rrdbnet_arch import RRDBNet  # noqa: F401
            from realesrgan import RealESRGANer  # noqa: F401
            _error = ""
        except Exception as exc:  # noqa: BLE001
            _error = f"{type(exc).__name__}: {exc}"
    return _error == "", _error or "ok"


def get_upsampler():
    global _upsampler
    if _upsampler is None:
        ok, why = available()
        if not ok:
            raise RuntimeError(f"Real-ESRGAN unavailable: {why}")
        import torch
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23,
                        num_grow_ch=32, scale=2)
        _upsampler = RealESRGANer(
            scale=2, model_path=str(WEIGHT), model=model,
            tile=int(os.getenv("REALESRGAN_TILE", "256")), tile_pad=10, pre_pad=0,
            half=torch.cuda.is_available(), gpu_id=None)
    return _upsampler


def restore(img: Image.Image, scale: float = 2) -> Image.Image:
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    with _lock:
        out, _ = get_upsampler().enhance(bgr, outscale=float(scale))
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
