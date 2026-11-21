"""Document restoration pipeline with text preservation and OCR verification.

original -> preprocess (page crop) -> DocRes (deshadowing + appearance)
         -> text-preserving refinement (restore strokes DocRes erased, remove dust on letters)
         -> PaddleOCR line guard (lines that read worse than the original fall back to the
            original's own strokes on the clean background)
         -> final image + text-quality report

Every stage is saved as PNG in `stage_dir`. Resolution is never reduced: DocRes runs its
network at DOCRES_MAX_SIZE but applies the result to the full-resolution page.
OCR is used only to measure and to choose between existing pixels; it never draws text.
"""
import json
import logging
import os
import re
import time
from pathlib import Path

import numpy as np
from PIL import Image

from . import docres_service, enhance_service, ocr_service, text_refine_service as tr

log = logging.getLogger("docrestore.document")


def _score(lines: list, orig_lines: list) -> tuple[float, float]:
    """Line-by-line agreement with the original reading (position matched, spaces ignored) and confidence."""
    agree = ocr_service.line_agreement(orig_lines, lines) or 0.0
    conf = float(np.mean([l["score"] for l in lines])) if lines else 0.0
    return round(agree, 4), round(conf, 4)


def run(original: Image.Image, stage_dir: Path, steps: list, ground_truth: str | None = None) -> tuple[Image.Image, dict]:
    stage_dir.mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    original = original.convert("RGB")
    original.save(stage_dir / "0_original.png")
    timings = {}

    def save(name, im):
        im.save(stage_dir / f"{name}.png")

    # 1. preprocess: crop the page off its background (if a page border is found)
    pre, note = enhance_service.page_crop(original)
    if note:
        steps.append(note)
    save("1_preprocessed", pre)

    # 2. DocRes
    t = time.time()
    docres_out, ds = docres_service.restore(pre, "end2end", skip_dewarp=bool(note))
    if docres_out.size != pre.size:
        docres_out = docres_out.resize(pre.size, Image.LANCZOS)
    steps.extend(ds)
    save("2_docres", docres_out)
    timings["docres_s"] = round(time.time() - t, 1)
    current = docres_out

    report = {"ocr_available": False, "stages": {}, "timings": timings}
    ok, why = ocr_service.available()
    if not ok:
        steps.append(f"OCR verification unavailable ({why}); text refinement used without OCR regions")
        mask = np.ones((pre.height, pre.width), bool)
        refined, rstats = tr.refine(pre, current, mask)
        save("3_text_refined", refined)
        report["refine"] = rstats
        final = refined
    else:
        report["ocr_available"] = True
        t = time.time()
        ol = ocr_service.read(pre)
        cl = ocr_service.read(current)
        mask = ocr_service.text_boxes(ol, (pre.height, pre.width)) | ocr_service.text_boxes(cl, (pre.height, pre.width))

        # 3. text-preserving refinement
        refined, rstats = tr.refine(pre, current, mask)
        refined, nsp = tr.remove_dark_specks(refined, mask, cl)
        rstats["specks_removed"] = nsp
        save("3_text_refined", refined)
        rl = ocr_service.read(refined)

        # 4. OCR line guard
        guarded, gl, reverted = tr.line_guard(pre, refined, ol, rl, ocr_service.read)
        if reverted:
            guarded, n2 = tr.remove_dark_specks(guarded, mask, gl)
            rstats["specks_removed_after_guard"] = n2
            gl = ocr_service.read(guarded)
        save("4_ocr_guarded", guarded)
        timings["text_and_ocr_s"] = round(time.time() - t, 1)

        # 5. choose the output that reads most like the original (then most confident).
        #    Later stages win ties, so refinement is kept unless it measurably hurts the text.
        otext = ocr_service.joined(ol)
        cands = [("docres", current, cl), ("text_refined", refined, rl), ("ocr_guarded", guarded, gl)]
        scored = [(_score(lines, ol), i, name, im, lines) for i, (name, im, lines) in enumerate(cands)]
        best = max(scored, key=lambda s: (s[0][0], s[0][1], s[1]))
        final, chosen, final_lines = best[3], best[2], best[4]
        for (agree, conf), _, name, _, lines in scored:
            report["stages"][name] = {"agreement_with_original_reading": agree, "mean_confidence": conf,
                                      "text": ocr_service.joined(lines)}
        report["stages"]["original"] = {"mean_confidence": _score(ol, ol)[1], "text": otext}
        report["chosen_stage"] = chosen
        report["refine"] = rstats
        report["reverted_lines"] = reverted
        report["comparison"] = ocr_service.compare(ol, final_lines)
        if ground_truth:
            report["ground_truth"] = {
                name: {"cer": ocr_service.cer(ground_truth, d["text"]), "wer": ocr_service.wer(ground_truth, d["text"])}
                for name, d in report["stages"].items()}
        steps.append(f"Restored {rstats['strokes_restored']} faint strokes DocRes had erased; removed {nsp} specks on letters")
        if reverted:
            steps.append(f"OCR guard: {len(reverted)} line(s) re-rendered from original strokes")
        cmp_ = report["comparison"]
        steps.append(f"OCR check: {cmp_['restored_lines']} text lines, agreement with original "
                     f"{cmp_['char_agreement']}, {len(cmp_['missing'])} missing / {len(cmp_['changed'])} changed spans "
                     f"(output stage: {chosen})")

    save("5_final", final)
    if final.size != pre.size:  # never ship a resized page
        raise RuntimeError(f"final size {final.size} differs from input {pre.size}")
    timings["total_s"] = round(time.time() - t_all, 1)
    (stage_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("document pipeline done in %.1fs -> %s", timings["total_s"], stage_dir)
    return final, report
