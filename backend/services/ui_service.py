"""UI reconstruction: rebuild a legacy interface screenshot at higher resolution.

Engines
- "ai": the remote restoration pipeline. For screenshots without faces this applies the
  service's learned background upscaler (denoise + 2x super-resolution) to the whole image.
- "classical": local, offline Lanczos upscale + median denoise + unsharp mask + autocontrast.
  Deterministic signal processing, labelled as such in the UI.
"""
from PIL import Image, ImageFilter, ImageOps

from . import gfpgan_service

ENGINES = {
    "ai": "AI enhancement",
    "classical": "Classical enhancement (offline)",
}


def classical(img: Image.Image, scale: float = 2) -> Image.Image:
    img = img.filter(ImageFilter.MedianFilter(3))
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
    return ImageOps.autocontrast(img, cutoff=0.5)


def reconstruct(img: Image.Image, engine: str, scale: float = 2) -> Image.Image:
    if engine == "ai":
        return gfpgan_service.restore(img, "balanced", scale)
    if engine == "classical":
        if not 1 <= scale <= 4:
            raise gfpgan_service.RestorationError("Scale must be between 1 and 4.", 400)
        return classical(img, scale)
    raise gfpgan_service.RestorationError("Unknown engine.", 400)
