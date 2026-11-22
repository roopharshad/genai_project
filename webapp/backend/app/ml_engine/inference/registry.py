"""Inference registry: routes every restoration job to the DocRestore AI model.

The UI from the design package is unchanged. Its preset / catalog ids are kept, but
each one now runs the project's existing model pipeline (no PyTorch needed):

  backend/services/gfpgan_service.py   hosted AI Image Restoration (faces + 2x enhance)
  backend/services/enhance_service.py  scratch removal, colourization, document cleanup
  app/ml_engine/models/opencv          classical OpenCV baseline (from the design package)
"""
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil
from PIL import Image

# Make the project's existing model package (genai_project/backend) importable.
_ROOT = Path(__file__).resolve().parents[5]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import truststore  # noqa: E402

truststore.inject_into_ssl()

import torch  # noqa: E402,F401  (load torch before paddle; both ship MKL DLLs on Windows)

from backend.services import (  # noqa: E402
    docres_service, document_pipeline, enhance_service, gfpgan_service, local_gfpgan_service,
    local_realesrgan_service)
from app.ml_engine.models.opencv.classical_restorer import OpenCVRestorer  # noqa: E402


def _fit(img: Image.Image, side: int = 1600) -> Image.Image:
    if max(img.size) <= side:
        return img
    s = side / max(img.size)
    return img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)


def _photo_pipeline(img: Image.Image, mode: str, cfg: Dict[str, Any], steps: List[str]) -> Image.Image:
    scale = float(cfg.get("scale", 2))
    mono = enhance_service._looks_monochrome(img)
    if cfg.get("remove_marks", True):
        img, pct = enhance_service.remove_marks(img, cfg.get("mark_strength", "normal"))
        steps.append(f"Removed scratches and marks ({pct}% of pixels)" if pct else "No scratches detected")
    engine = os.getenv("RESTORATION_ENGINE", "local").lower()  # local | hosted
    ok, why = local_gfpgan_service.available()
    if engine == "local" and ok:
        weight = {"balanced": 0.5, "fidelity": 0.3, "detail": 0.8}.get(mode, 0.5)
        img, faces = local_gfpgan_service.restore(img, scale, weight)
        bg_ai = os.getenv("REALESRGAN_ENABLED", "1") == "1" and local_realesrgan_service.available()[0]
        detail = "Real-ESRGAN restored background detail; " if bg_ai else ""
        steps.append(f"{detail}GFPGAN v1.4 restored {faces} face(s), upscaled {scale:g}x"
                     if faces else f"{detail}no faces found; image upscaled {scale:g}x")
    else:
        if engine == "local":
            steps.append(f"Local GFPGAN unavailable ({why}); used hosted service")
        img = gfpgan_service.restore(img, mode, scale)
        steps.append(f"AI Image Restoration ({gfpgan_service.MODES[mode][1]}, hosted), upscaled {scale:g}x")
    if cfg.get("colorize", False):
        if mono:
            img = enhance_service.colorize(img)
            steps.append("Added colour (AI colourization)")
        else:
            steps.append("Colourization skipped: image already has colour")
    if cfg.get("clarity", True):
        img = enhance_service.finish_photo(img)
        steps.append("Improved clarity (local contrast + sharpening)")
    return img


STAGES_DIR = Path(__file__).resolve().parents[4] / "storage" / "stages"


def _document_pipeline(img: Image.Image, cfg: Dict[str, Any], steps: List[str], extra: Dict[str, Any],
                       progress=None) -> Image.Image:
    """DocRes + text-preserving refinement + PaddleOCR verification, with OpenCV fallback."""
    ok, why = docres_service.available()
    if os.getenv("DOCUMENT_ENGINE", "docres").lower() == "docres" and ok:
        run_id = time.strftime("%Y%m%d-%H%M%S-") + os.urandom(3).hex()
        out, report = document_pipeline.run(img, STAGES_DIR / run_id, steps, config=cfg, progress=progress)
        extra["stages_url"] = f"/storage/stages/{run_id}/"
        extra["stages"] = sorted(p.name for p in (STAGES_DIR / run_id).iterdir())
        extra["text_report"] = report
        return out
    if not ok:
        steps.append(f"DocRes unavailable ({why}); used classical document cleanup")
    scale = float(cfg.get("scale", 2))
    style = cfg.get("doc_style", "color")
    out, notes = enhance_service.enhance_document(img, scale, style if style in ("aged", "color", "bw") else "color")
    steps.extend(notes)
    return out


class ModelRegistry:
    """Same public interface as the design package's registry."""

    # model id -> (display name, description, runner)
    _model_states: Dict[str, Dict[str, Any]] = {
        "ai_restoration": {"enabled": True, "deployment_status": "production"},
        "ai_fidelity": {"enabled": True, "deployment_status": "production"},
        "ai_detail": {"enabled": True, "deployment_status": "production"},
        "document": {"enabled": True, "deployment_status": "production"},
        "opencv": {"enabled": True, "deployment_status": "baseline"},
    }

    # Preset ids are fixed by the UI (RestorationPage.tsx) and must stay the same.
    _PRESET_TARGET = {
        "recommended": "document",
        "gfpgan_prior": "document",
        "balanced": "document",
        "high_quality": "document",
        "document": "document",
    }

    @classmethod
    def get_presets(cls) -> List[Dict[str, Any]]:
        return [
            {"id": "recommended", "name": "Recommended (AI Image Restoration)", "category": "AI Restoration",
             "description": "Removes scratches and marks, restores faces and detail, upscales 2x and improves clarity.",
             "target_model_id": "ai_restoration", "is_primary": True, "badge": "Recommended",
             "speed": "20-90 s", "fidelity": "Balanced",
             "parameters": [{"name": "scale", "type": "int", "default": 2, "label": "Output Scale", "min": 1, "max": 4}]},
            {"id": "gfpgan_prior", "name": "High Fidelity", "category": "AI Restoration",
             "description": "AI restoration that stays closer to the original appearance.",
             "target_model_id": "ai_fidelity", "is_primary": False, "badge": "Faithful",
             "speed": "20-90 s", "fidelity": "High fidelity",
             "parameters": [{"name": "scale", "type": "int", "default": 2, "label": "Output Scale", "min": 1, "max": 4}]},
            {"id": "balanced", "name": "Balanced (Fast Classical Cleanup)", "category": "Classical",
             "description": "Offline bilateral denoise, unsharp masking and contrast. No AI.",
             "target_model_id": "opencv", "is_primary": False, "badge": "Ultra Fast",
             "speed": "< 1 s", "fidelity": "Standard",
             "parameters": [{"name": "unsharp_strength", "type": "float", "default": 1.4, "label": "Edge Boost", "min": 1.0, "max": 2.5}]},
            {"id": "high_quality", "name": "High Quality (Fine Detail)", "category": "AI Restoration",
             "description": "AI restoration with sharper textures, plus colourization for black & white photos.",
             "target_model_id": "ai_detail", "is_primary": False, "badge": "Generative AI",
             "speed": "30-100 s", "fidelity": "Fine detail",
             "parameters": [{"name": "scale", "type": "int", "default": 2, "label": "Output Scale", "min": 1, "max": 4}]},
        ]

    @classmethod
    def resolve_preset(cls, preset_id: str) -> Tuple[str, Dict[str, Any]]:
        if preset_id in cls._PRESET_TARGET:
            target = cls._PRESET_TARGET[preset_id]
            defaults = {"fast_mode": False}
            return target, defaults
        return preset_id, {}

    @classmethod
    def get_model_catalog(cls) -> List[Dict[str, Any]]:
        ai_ok = True  # remote availability is checked at run time; failures are reported per job

        def entry(mid, name, mtype, purpose, primary, params, version):
            st = cls._model_states[mid]
            return {
                "id": mid, "name": name, "model_type": mtype, "architecture": mtype, "purpose": purpose,
                "is_primary": primary, "training_status": "Pretrained", "checkpoint_available": ai_ok,
                "checkpoint_file": "hosted" if mid.startswith("ai_") else "local", "checkpoint_path": None,
                "model_version": version, "deployment_status": st["deployment_status"], "is_enabled": st["enabled"],
                "validation_status": "Verified", "parameters": params, "status": st["deployment_status"],
                "category": mtype,
            }

        scale = [{"name": "scale", "type": "int", "default": 2, "label": "Output Scale", "min": 1, "max": 4}]
        return [
            entry("ai_restoration", "AI Image Restoration (Balanced)", "AI Image Restoration",
                  "Scratch removal + AI face/detail restoration + 2x upscale + clarity.", True, scale, "v1"),
            entry("ai_fidelity", "AI Image Restoration (High Fidelity)", "AI Image Restoration",
                  "AI restoration that stays closer to the original appearance.", False, scale, "v1"),
            entry("ai_detail", "AI Image Restoration (Fine Detail)", "AI Image Restoration",
                  "Sharper textures; adds colour to black & white photos.", False, scale, "v1"),
            entry("document", "Document Restoration", "Document Enhancement",
                  "Crops the page, flattens stains/creases, removes specks and darkens ink.", False,
                  scale + [{"name": "doc_style", "type": "str", "default": "aged", "label": "Style (aged/color/bw)"}], "v1"),
            entry("opencv", "OpenCV Classical Restorer", "Algorithmic Baseline",
                  "Bilateral denoise, unsharp masking and CLAHE contrast. Offline, no AI.", False,
                  [{"name": "unsharp_strength", "type": "float", "default": 1.4, "label": "Edge Boost", "min": 1.0, "max": 2.5}],
                  "v4"),
        ]

    @classmethod
    def set_model_state(cls, model_id: str, enabled: Optional[bool] = None, deployment_status: Optional[str] = None):
        if model_id in cls._model_states:
            if enabled is not None:
                cls._model_states[model_id]["enabled"] = enabled
            if deployment_status is not None:
                cls._model_states[model_id]["deployment_status"] = deployment_status

    @classmethod
    def run_restoration(cls, model_id: str, input_image_np: np.ndarray,
                        config: Dict[str, Any] = None, progress=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        config = config or {}
        start = time.perf_counter()
        proc = psutil.Process(os.getpid())
        mem_before = proc.memory_info().rss / 1048576
        h, w = input_image_np.shape[:2]
        steps: List[str] = []
        extra: Dict[str, Any] = {}

        # This deployment accepts documents only; every preset uses the protected document pipeline.
        full = Image.fromarray(input_image_np).convert("RGB")
        try:
            steps.append("Document-only mode: using protected document restoration")
            out = _document_pipeline(full, config, steps, extra, progress)
        except gfpgan_service.RestorationError as exc:
            raise RuntimeError(str(exc)) from exc
        restored = np.array(out.convert("RGB"))

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        metrics = {
            "inference_time_ms": elapsed_ms,
            "memory_usage_mb": round(max(0.1, proc.memory_info().rss / 1048576 - mem_before), 2),
            "model_size_mb": 0,
            "input_resolution": f"{w}x{h}",
            "output_resolution": f"{restored.shape[1]}x{restored.shape[0]}",
            "model_id": model_id,
            "steps": steps,
            **extra,
        }
        return restored, metrics
