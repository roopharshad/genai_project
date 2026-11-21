"""DocDiff (ACM MM 2023) residual-diffusion text refinement, from the official repository
https://github.com/Royalvice/DocDiff (code copied unmodified to DocDiff-main/).

Only the published *document deblurring* weights exist (checksave/init.pth + denoiser.pth,
trained on the Hradis et al. 2015 text-deblurring dataset). Inference follows
src/trainer.py Trainer.test() with conf.yml defaults: TIMESTEPS=100, linear schedule,
PRE_ORI='True' (predict x0, deterministic sampling), NATIVE_RESOLUTION via 128x128 tiles,
final = sampled high-frequency residual + coarse prediction.

The image is processed at native resolution (no resizing), so dimensions are preserved.
"""
import logging
import os
import sys
import threading
import time

import numpy as np
from PIL import Image

from .. import config

log = logging.getLogger("docrestore.docdiff")

DOCDIFF_DIR = config.ROOT_DIR / "DocDiff-main"
INIT_W = DOCDIFF_DIR / "checksave" / "init.pth"
DENOISER_W = DOCDIFF_DIR / "checksave" / "denoiser.pth"
TILE = 128
_lock = threading.Lock()
_state: dict = {}


def available() -> tuple[bool, str]:
    if not (INIT_W.is_file() and DENOISER_W.is_file()):
        return False, "missing DocDiff-main/checksave weights"
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        return False, str(exc)
    return True, "ok"


def _load():
    if "net" in _state:
        return _state
    if str(DOCDIFF_DIR) not in sys.path:
        sys.path.insert(0, str(DOCDIFF_DIR))
    import torch
    from model.DocDiff import DocDiff
    from schedule.diffusionSample import GaussianDiffusion
    from schedule.schedule import Schedule

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t = time.time()
    net = DocDiff(input_channels=6, output_channels=3, n_channels=32, ch_mults=[1, 2, 3, 4], n_blocks=1)
    net.init_predictor.load_state_dict(torch.load(str(INIT_W), map_location="cpu"))
    net.denoiser.load_state_dict(torch.load(str(DENOISER_W), map_location="cpu"))
    net.eval().to(device)
    diffusion = GaussianDiffusion(net.denoiser, 100, Schedule("linear", 100)).to(device)
    _state.update(torch=torch, net=net, diffusion=diffusion, device=device)
    log.info("DocDiff loaded on %s in %.1fs", device, time.time() - t)
    return _state


def _sample(diffusion, x_T, cond):
    """GaussianDiffusion.forward with pre_ori='True', without its per-step print()."""
    torch = _state["torch"]
    from schedule.diffusionSample import extract_
    x_t = x_T
    for step in reversed(range(diffusion.T)):
        t = x_t.new_ones([x_T.shape[0]], dtype=torch.long) * step
        if step > 0:
            ori = diffusion.model(torch.cat((x_t, cond), 1), t)
            eps = (x_t - extract_(diffusion.sqrt_gammas, t, ori.shape) * ori) / extract_(diffusion.sqrt_one_minus_gammas, t, ori.shape)
            x_t = extract_(diffusion.sqrt_gammas, t - 1, ori.shape) * ori + extract_(diffusion.sqrt_one_minus_gammas, t - 1, eps.shape) * eps
        else:
            x_t = diffusion.model(torch.cat((x_t, cond), 1), t)
    return x_t


def refine(img: Image.Image, batch: int = 16, seed: int = 0) -> Image.Image:
    ok, why = available()
    if not ok:
        raise RuntimeError(f"DocDiff unavailable: {why}")
    with _lock:
        s = _load()
        torch = s["torch"]
        arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
        h, w = arr.shape[:2]
        H, W = -(-h // TILE) * TILE, -(-w // TILE) * TILE
        pad = np.ones((H, W, 3), np.float32)  # white padding, like Trainer.test's torch.ones
        pad[:h, :w] = arr
        tiles = pad.reshape(H // TILE, TILE, W // TILE, TILE, 3).transpose(0, 2, 4, 1, 3).reshape(-1, 3, TILE, TILE)
        out = np.empty_like(tiles)
        g = torch.Generator().manual_seed(seed)
        t0 = time.time()
        with torch.no_grad():
            for i in range(0, len(tiles), batch):
                x = torch.from_numpy(tiles[i:i + batch]).to(s["device"])
                init = s["net"].init_predictor(x, 0)
                noise = torch.randn(x.shape, generator=g).to(s["device"])
                res = _sample(s["diffusion"], noise, init)
                out[i:i + batch] = (res + init).clamp(0, 1).cpu().numpy()
        full = out.reshape(H // TILE, W // TILE, 3, TILE, TILE).transpose(0, 3, 1, 4, 2).reshape(H, W, 3)[:h, :w]
        log.info("DocDiff refined %dx%d (%d tiles) in %.1fs", w, h, len(tiles), time.time() - t0)
    return Image.fromarray((full * 255 + 0.5).astype(np.uint8))
