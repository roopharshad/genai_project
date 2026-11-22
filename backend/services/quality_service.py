"""Restoration quality evaluation (before vs after), honest about what each number means.

There is no clean ground-truth scan for user uploads, so:
- PSNR / SSIM are measured against the uploaded original: they show how much the image changed
  (fidelity to the original), not how close it is to a perfect document.
- Damage score before/after uses damage_service on both images (lower = less damage).
- Stroke / dot preservation come from paper_restore_service.quality (1.0 = no ink erased).
- OCR accuracy is real (1 - CER) only when a user-approved transcription exists; otherwise the
  OCR agreement between original and restored readings is reported, labelled as agreement.
Quality score (0-100) = 40 x damage reduction + 30 x ink preservation + 30 x text term.
"""
import math

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from . import damage_service, ocr_service, paper_restore_service as paper


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 100.0 if mse == 0 else round(20 * math.log10(255.0 / math.sqrt(mse)), 2)


def evaluate(reference: Image.Image, restored: Image.Image, report: dict | None = None,
             approved_text: str | None = None, restored_lines: list | None = None) -> dict:
    report = report or {}
    reference = reference.convert("RGB")
    restored = restored.convert("RGB")
    if restored.size != reference.size:
        restored = restored.resize(reference.size, Image.LANCZOS)
    a, b = np.asarray(reference), np.asarray(restored)
    psnr = _psnr(a, b)
    ssim = round(float(structural_similarity(a, b, channel_axis=2, data_range=255)), 4)

    d0, d1 = damage_service.detect(reference), damage_service.detect(restored)
    s0, s1 = d0["damage_score"], d1["damage_score"]
    reduction = max(0.0, (s0 - s1) / s0) if s0 > 0 else 0.0
    per_damage = {k: {"before": d0["damages"][k]["severity"], "after": d1["damages"][k]["severity"]}
                  for k in d0["damages"]}

    q = paper.quality(reference, restored)
    ink = min(q.get("stroke_preservation") or 0, q.get("dot_preservation") or 1)

    ocr = {}
    cmp_ = report.get("comparison") or {}
    if approved_text:
        lines = restored_lines if restored_lines is not None else ocr_service.read(restored)
        hyp = ocr_service.joined(lines)
        cer = ocr_service.cer(approved_text, hyp)
        ocr = {"kind": "accuracy_vs_approved_text", "cer": cer, "wer": ocr_service.wer(approved_text, hyp),
               "char_accuracy": round(max(0.0, 1 - cer), 4)}
        text_term = ocr["char_accuracy"]
    elif cmp_.get("char_agreement") is not None and report.get("ocr_reliable", True):
        ocr = {"kind": "agreement_with_original_reading", "char_agreement": cmp_["char_agreement"],
               "word_agreement": cmp_.get("word_agreement"),
               "confidence_before": cmp_.get("original_mean_confidence"),
               "confidence_after": cmp_.get("restored_mean_confidence")}
        text_term = cmp_["char_agreement"]
    else:
        ocr = {"kind": "unavailable", "note": "OCR could not verify this text (handwriting or low confidence). "
                                              "Approve a transcription in OCR Review to measure accuracy."}
        text_term = ink
    score = round(100 * (0.4 * reduction + 0.3 * ink + 0.3 * text_term), 1)
    return {
        "psnr_vs_original": psnr, "ssim_vs_original": ssim,
        "damage_score_before": s0, "damage_score_after": s1, "damage_reduction_pct": round(100 * reduction, 1),
        "per_damage": per_damage,
        "stroke_preservation": q.get("stroke_preservation"), "dot_preservation": q.get("dot_preservation"),
        "ink_contrast_before": paper.quality(reference, reference).get("ink_contrast"),
        "ink_contrast_after": q.get("ink_contrast"),
        "ocr": ocr, "quality_score": score,
        "ai_generated_pct": report.get("ai_generated_pct", 0.0),
        "notes": "PSNR/SSIM compare with the uploaded original (no clean reference exists); "
                 "quality score = 40% damage reduction + 30% ink preservation + 30% text accuracy/agreement.",
    }
