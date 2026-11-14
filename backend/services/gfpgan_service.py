"""AI image restoration backed by a hosted GFPGAN Gradio Space.

INTERNAL MODULE. Third-party names stay here; the public API/UI only exposes neutral
mode ids ("balanced", "fidelity", ...).

How the remote API was determined (see scripts/inspect_restoration_api.py):
  gradio_client.Client("randomtable/Image-Restoration-GFPGAN").view_api() reports a single
  endpoint "/predict" (fn_index 0) with inputs:
      input            Image  (base64 data URI)
      version          Radio  one of v1.2, v1.3, v1.4, RestoreFormer, CodeFormer, RealESR-General-x4v3
      rescaling_factor Number (default 2)
  and outputs [restored image as base64 PNG, file dict].
  The Space runs Gradio 3.1.7 (legacy "ws" queue protocol), which current gradio_client
  releases cannot submit to, so prediction uses the Space's plain HTTP route
  POST {space}/api/predict  {"data": [...], "fn_index": 0}.

The Space wraps GFPGANer (GFPGAN-master/gfpgan/utils.py) with a Real-ESRGAN background
upsampler: faces get generative restoration, the rest of the image is upscaled/denoised.
It is not a general UI-element restorer.
"""
import base64
import io
import logging
import time

import httpx
from PIL import Image

from .. import config

log = logging.getLogger("docrestore.restoration")

# Public mode id -> (remote "version" value, public label, public description).
# Only options verified against the live service are listed.
MODES = {
    "balanced": ("v1.4", "Balanced", "Recommended. Natural detail with strong noise and blur removal."),
    "fidelity": ("v1.3", "High fidelity", "Stays closer to the original appearance; softer result."),
    "detail": ("RestoreFormer", "Fine detail", "Sharper textures; may alter fine features more."),
}
DEFAULT_MODE = "balanced"


class RestorationError(RuntimeError):
    """Remote processing failed. `status` is the HTTP status to return to the client."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.HF_TOKEN}"} if config.HF_TOKEN else {}


def health(timeout: float = 10) -> dict:
    try:
        r = httpx.get(f"{config.RESTORATION_SPACE_URL}/config", headers=_headers(), timeout=timeout)
        return {"available": r.status_code == 200}
    except httpx.HTTPError:
        return {"available": False}


def restore(img: Image.Image, mode: str = DEFAULT_MODE, scale: float = 2) -> Image.Image:
    """Send an RGB image to the service and return the restored image."""
    if mode not in MODES:
        raise RestorationError("Unknown restoration mode.", 400)
    if not 1 <= scale <= 4:
        raise RestorationError("Scale must be between 1 and 4.", 400)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    payload = {
        "data": ["data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), MODES[mode][0], scale],
        "fn_index": 0,
    }
    started = time.time()
    try:
        resp = httpx.post(
            f"{config.RESTORATION_SPACE_URL}/api/predict",
            json=payload,
            headers=_headers(),
            timeout=httpx.Timeout(config.RESTORATION_TIMEOUT_SECONDS, connect=20),
        )
    except httpx.TimeoutException as exc:
        raise RestorationError("The restoration service took too long to respond. Please try again.", 504) from exc
    except httpx.HTTPError as exc:
        log.warning("restoration connect error: %s", exc)
        raise RestorationError("The restoration service is unreachable. Check your internet connection.", 503) from exc

    log.info("restoration mode=%s status=%s %.1fs", mode, resp.status_code, time.time() - started)
    if resp.status_code in (502, 503, 504):
        raise RestorationError("The restoration service is starting up or busy. Please retry in a minute.", 503)
    if resp.status_code != 200:
        log.warning("restoration bad status %s: %s", resp.status_code, resp.text[:300])
        raise RestorationError(f"The restoration service returned an error ({resp.status_code}).")

    try:
        data = resp.json().get("data") or []
        out = data[0] if data else None
    except ValueError:
        out = None
    if not out or not isinstance(out, str) or "," not in out:
        # The Space returns [None, None] when its own inference raises.
        raise RestorationError("The service could not process this image. Try a different image or mode.", 422)

    try:
        result = Image.open(io.BytesIO(base64.b64decode(out.split(",", 1)[1])))
        result.load()
    except Exception as exc:  # noqa: BLE001 - any decode failure is a bad response
        raise RestorationError("The service returned an unreadable image.") from exc
    return result
