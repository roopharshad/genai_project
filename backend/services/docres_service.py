"""DocRes (CVPR 2024) document image restoration, from the bundled DocRes-master source.

Follows DocRes-master/inference.py (same Restormer config, DTSPrompts, pre/post processing and
the end2end chain dewarping -> deshadowing -> appearance), adapted to run on CPU: the original
casts to half precision and calls .cuda(); here tensors stay float32 on the selected device.

Weights (from the official Hugging Face Space qubvel-hf/documents-restoration):
  DocRes-master/checkpoints/docres.pkl        Restormer, 6-channel input (image + prompt)
  DocRes-master/data/MBD/checkpoint/mbd.pkl   DeepLab document mask model (for dewarping)
"""
import importlib.util
import logging
import os
import sys
import threading
import time

import cv2
import numpy as np
from PIL import Image

from .. import config

log = logging.getLogger("docrestore.docres")

DOCRES_DIR = config.ROOT_DIR / "DocRes-master"
DOCRES_CKPT = DOCRES_DIR / "checkpoints" / "docres.pkl"
MBD_CKPT = DOCRES_DIR / "data" / "MBD" / "checkpoint" / "mbd.pkl"
TASKS = ("end2end", "dewarping", "deshadowing", "appearance", "deblurring", "binarization")
# inference.py uses 1600. Larger inputs are processed at this size and the result is applied
# to the full-resolution image as a shading map (same code path as the original).
# On CPU 1600 takes over 30 minutes per page; 768 takes about 1 minute. Use 1600 with a GPU.
MAX_SIZE = int(os.getenv("DOCRES_MAX_SIZE", "512"))

_lock = threading.Lock()
_state: dict = {}


def available() -> tuple[bool, str]:
    if not DOCRES_CKPT.is_file():
        return False, "missing checkpoints/docres.pkl"
    try:
        import einops  # noqa: F401
        import torch  # noqa: F401
    except ImportError as exc:
        return False, str(exc)
    return True, "ok"


def _load():
    if "model" in _state:
        return _state
    # DocRes root first (models/, data/), MBD dir after it (model/ for the mask network).
    for p in (str(DOCRES_DIR / "data" / "MBD"), str(DOCRES_DIR)):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)
    import torch
    # DocRes-master/utils.py and data/MBD/utils.py share a name; load the root one by path.
    spec = importlib.util.spec_from_file_location("docres_root_utils", DOCRES_DIR / "utils.py")
    du = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(du)
    from data.preprocess.crop_merge_image import stride_integral
    from models import restormer_arch

    torch.set_num_threads(max(1, os.cpu_count() or 1))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t = time.time()
    model = restormer_arch.Restormer(
        inp_channels=6, out_channels=3, dim=48, num_blocks=[2, 3, 3, 4], num_refinement_blocks=4,
        heads=[1, 2, 4, 8], ffn_expansion_factor=2.66, bias=False, LayerNorm_type="WithBias",
        dual_pixel_task=True)
    ckpt = torch.load(str(DOCRES_CKPT), map_location="cpu", weights_only=False)
    model.load_state_dict(du.convert_state_dict(ckpt["model_state"]))
    model.eval().to(device)
    _state.update(torch=torch, utils=du, stride_integral=stride_integral, model=model, device=device)
    log.info("DocRes model loaded on %s in %.1fs", device, time.time() - t)
    return _state


def _load_mbd():
    if "mbd" in _state:
        return _state["mbd"]
    s = _load()
    from model.deep_lab_model.deeplab import DeepLab  # DocRes-master/data/MBD/model
    t = time.time()
    seg = DeepLab(num_classes=1, backbone="resnet", output_stride=16, sync_bn=None, freeze_bn=False)
    ckpt = s["torch"].load(str(MBD_CKPT), map_location="cpu", weights_only=False)
    seg.load_state_dict({k.replace("module.", "", 1): v for k, v in ckpt["model_state"].items()})
    seg.eval().to(s["device"])
    _state["mbd"] = seg
    log.info("DocRes MBD mask model loaded in %.1fs", time.time() - t)
    return seg


# ---------------------------------------------------------------- prompts (from inference.py)
def _bg_prompt(img, keep_bg: bool):
    h, w = img.shape[:2]
    img = cv2.resize(img, (1024, 1024))
    norm_planes, bgs = [], []
    for plane in cv2.split(img):
        bg = cv2.medianBlur(cv2.dilate(plane, np.ones((7, 7), np.uint8)), 21)
        bgs.append(bg)
        diff = 255 - cv2.absdiff(plane, bg)
        norm_planes.append(cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1))
    if keep_bg:  # deshadow_prompt
        return cv2.resize(cv2.merge(bgs), (w, h))
    return cv2.resize(cv2.merge(norm_planes), (w, h))  # appearance_prompt


def _deblur_prompt(img):
    x = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 1, 0))
    y = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 0, 1))
    hf = cv2.cvtColor(cv2.addWeighted(x, 0.5, y, 0.5, 0), cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(hf, cv2.COLOR_GRAY2BGR)


def _binarization_prompt(img, du):
    result, thresh = du.SauvolaModBinarization(img)
    thresh = thresh.astype(np.uint8)
    result[result > 155] = 255
    result[result <= 155] = 0
    x = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 1, 0))
    y = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 0, 1))
    hf = cv2.cvtColor(cv2.addWeighted(x, 0.5, y, 0.5, 0), cv2.COLOR_BGR2GRAY)
    return np.concatenate((thresh[..., None], hf[..., None], result[..., None]), -1)


# ---------------------------------------------------------------- tasks
def _run(in_im: np.ndarray):
    s = _load()
    torch = s["torch"]
    t = torch.from_numpy((in_im / 255.0).transpose(2, 0, 1)).unsqueeze(0).float().to(s["device"])
    with torch.no_grad():
        return s["model"](t)


def _shading_task(im_org, prompt):
    s = _load()
    h, w = im_org.shape[:2]
    in_im = np.concatenate((im_org, prompt), -1)
    small = max(w, h) < MAX_SIZE
    if small:
        in_im, ph, pw = s["stride_integral"](in_im, 8)
    else:
        in_im = cv2.resize(in_im, (MAX_SIZE, MAX_SIZE))
    pred = s["torch"].clamp(_run(in_im), 0, 1)[0].permute(1, 2, 0).cpu().numpy()
    pred = (pred * 255).astype(np.uint8)
    if small:
        return pred[ph:, pw:]
    pred[pred == 0] = 1
    shadow = cv2.resize(im_org, (MAX_SIZE, MAX_SIZE)).astype(float) / pred.astype(float)
    shadow = cv2.resize(shadow, (w, h))
    shadow[shadow == 0] = 0.00001
    return np.clip(im_org.astype(float) / shadow, 0, 255).astype(np.uint8)


def deshadowing(im):
    return _shading_task(im, _bg_prompt(im, keep_bg=True))


def appearance(im):
    return _shading_task(im, _bg_prompt(im, keep_bg=False))


def deblurring(im_org):
    s = _load()
    in_im, ph, pw = s["stride_integral"](im_org, 8)
    in_im = np.concatenate((in_im, _deblur_prompt(in_im)), -1)
    pred = s["torch"].clamp(_run(in_im), 0, 1)[0].permute(1, 2, 0).cpu().numpy()
    return (pred * 255).astype(np.uint8)[ph:, pw:]


def binarization(im_org):
    s = _load()
    torch = s["torch"]
    im, ph, pw = s["stride_integral"](im_org, 8)
    h, w = im.shape[:2]
    pred = _run(np.concatenate((im, _binarization_prompt(im, s["utils"])), -1))[:, :2, :, :]
    pred = torch.max(torch.softmax(pred, 1), 1)[1][0].cpu().numpy()
    pred = cv2.resize((pred * 255).astype(np.uint8), (w, h))[ph:, pw:]
    return cv2.cvtColor(pred, cv2.COLOR_GRAY2BGR)


def _mbd_mask(img_org):
    s = _load()
    torch = s["torch"]
    seg = _load_mbd()
    h, w = img_org.shape[:2]
    img = cv2.GaussianBlur(cv2.resize(img_org, (448, 448)), (15, 15), 0, 0)
    img = s["utils"].cvimg2torch(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).to(s["device"])
    with torch.no_grad():
        pred = seg(img)
        m = torch.nn.functional.interpolate(pred[:, 0, :, :].unsqueeze(1), (h, w)).squeeze().cpu().numpy()
    m = (m * 255).astype(np.uint8)
    k = np.ones((3, 3))
    m = cv2.erode(cv2.dilate(m, k, iterations=3), k, iterations=3)
    m[m > 100] = 255
    m[m < 100] = 0
    return m


def dewarping(im_org):
    s = _load()
    torch = s["torch"]
    size = 256
    mask = _mbd_mask(im_org)
    base = s["utils"].getBasecoord(size, size) / size
    masked = im_org.copy()
    masked[mask == 0] = 0
    prompt = np.concatenate((base, np.expand_dims(cv2.resize(mask, (size, size)) / 255, -1)), -1)
    h, w = masked.shape[:2]
    x = torch.from_numpy((cv2.resize(masked, (size, size)) / 255.0).transpose(2, 0, 1)).unsqueeze(0).float()
    p = torch.from_numpy(prompt.transpose(2, 0, 1)).unsqueeze(0).float()
    with torch.no_grad():
        pred = s["model"](torch.cat((x, p), 1).to(s["device"]))[0][:2].permute(1, 2, 0).cpu().numpy() + base
    for _ in range(15):
        pred = cv2.blur(pred, (3, 3), borderType=cv2.BORDER_REPLICATE)
    pred = (cv2.resize(pred, (w, h)) * (w, h)).astype(np.float32)
    return cv2.remap(im_org, pred[:, :, 0], pred[:, :, 1], cv2.INTER_LINEAR)


def restore(img: Image.Image, task: str = "end2end", skip_dewarp: bool = False) -> tuple[Image.Image, list]:
    """Run a DocRes task. Returns (image, list of steps)."""
    ok, why = available()
    if not ok:
        raise RuntimeError(f"DocRes unavailable: {why}")
    if task not in TASKS:
        raise ValueError(f"Unknown DocRes task '{task}'")
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    steps = []
    fns = {"dewarping": dewarping, "deshadowing": deshadowing, "appearance": appearance,
           "deblurring": deblurring, "binarization": binarization}
    with _lock:
        t = time.time()
        # Dewarping is only for curled/bent pages; on flat pages it bends the text, so it is opt-in.
        dewarp = MBD_CKPT.is_file() and not skip_dewarp and os.getenv("DOCRES_DEWARP", "0") == "1"
        chain = (["dewarping"] if dewarp else []) + ["deshadowing", "appearance"] if task == "end2end" else [task]
        for name in chain:
            t1 = time.time()
            bgr = fns[name](bgr)
            steps.append(f"DocRes {name} ({time.time() - t1:.1f}s)")
        log.info("DocRes %s %dx%d in %.1fs", task, bgr.shape[1], bgr.shape[0], time.time() - t)
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), steps
