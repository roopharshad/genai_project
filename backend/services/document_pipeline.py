"""Document restoration pipeline: damage detection -> model selection -> restoration -> checks.

original -> page crop -> damage detection (damage_service) -> stage plan
         -> paper normalisation (stains, fading, creases; ink protected)
         -> LaMa repair of tears/holes outside text (AI pixels recorded and marked)
         -> DocRes appearance (+ DocRes deblurring only when the text is blurred)
         -> text-preserving refinement + PaddleOCR line guard
         -> OCR-guarded speck cleanup
         -> safest stage chosen by stroke/dot preservation, then OCR agreement

Every stage is saved as PNG in `stage_dir`, plus report.json. The original upload is never
modified. OCR only measures and chooses between pixels; it never draws text. Resolution is
never changed. Pass config["fast_mode"]=True to skip DocRes and OCR.
"""
import json
import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import (damage_service, docres_service, enhance_service, lama_service, ocr_service,
               paper_restore_service as paper, text_refine_service as tr)

log = logging.getLogger("docrestore.document")


def _score(lines: list, orig_lines: list) -> tuple[float, float]:
    """Line-by-line agreement with the original reading (position matched, spaces ignored) and confidence."""
    agree = ocr_service.line_agreement(orig_lines, lines) or 0.0
    conf = float(np.mean([l["score"] for l in lines])) if lines else 0.0
    return round(agree, 4), round(conf, 4)


def _safe_quality(q: dict) -> bool:
    """Reject a candidate that erases original ink/dots or creates substantial new dark marks."""
    return (q.get("stroke_preservation") is not None
            and q["stroke_preservation"] >= 0.985
            and (q.get("dot_preservation") is None or q["dot_preservation"] >= 0.98)
            and q.get("created_ink_pct", 100) <= 0.25)


def _text_kept(pre: Image.Image, cand: Image.Image, ink: np.ndarray, text_mask: np.ndarray) -> float | None:
    """Share of original ink pixels INSIDE OCR text regions still dark in `cand` (speck check)."""
    sel = ink & text_mask
    if sel.sum() < 50:
        return None
    g0 = np.asarray(pre.convert("L"), np.float32)
    g1 = np.asarray(cand.convert("L"), np.float32)
    return round(float((g1[sel] <= g0[sel] + 25).mean()), 4)


def run(original: Image.Image, stage_dir: Path, steps: list, ground_truth: str | None = None,
        config: dict | None = None, progress=None) -> tuple[Image.Image, dict]:
    config = config or {}
    notify = progress or (lambda value, label: None)
    stage_dir.mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    original = original.convert("RGB")
    original.save(stage_dir / "0_original.png")
    timings = {}

    def save(name, im):
        im.save(stage_dir / f"{name}.png")

    def tick(name, t0):
        timings[name] = round(time.time() - t0, 1)

    # 1. page crop
    pre, note = enhance_service.page_crop(original)
    if note:
        steps.append(note)
    save("1_preprocessed", pre)

    # 2. damage detection + model selection
    notify(42, "Detecting damage: blur, fading, stains, creases, tears")
    t = time.time()
    damage = damage_service.detect(pre)
    save("1b_damage_map", damage_service.overlay(pre, damage["masks"]))
    plan = damage_service.plan(damage)
    if config.get("auto_select", True) is False:
        for p in plan:  # manual mode: run everything
            p["run"], p["reason"] = True, "manual: all stages selected"
    run_stage = {p["stage"]: p["run"] for p in plan}
    tick("damage_detection_s", t)
    found = [f"{k.replace('_', ' ')} ({v['level']})" for k, v in damage["damages"].items() if v["detected"]]
    steps.append("Damage detected: " + (", ".join(found) if found else "none"))
    steps.append("Selected stages: " + ", ".join(p["stage"] for p in plan if p["run"]))

    p_mask = paper.ink_mask(pre)
    current = pre
    paper_info, paper_quality = {}, None

    # 3. LaMa repair of tears/holes outside text. Every generated pixel is recorded.
    ai_mask = np.zeros((pre.height, pre.width), np.uint8)
    lama_info = {"repaired_pixels": 0, "repaired_pct": 0.0, "regions": []}
    if run_stage.get("lama_repair") and os.getenv("LAMA_ENABLED", "1") == "1" and config.get("repair_tears", True):
        ok_lama, why_lama = lama_service.available()
        if ok_lama:
            notify(50, "LaMa: repairing tears and holes outside text")
            t = time.time()
            protect = p_mask["protect"] | p_mask["uncertain"]
            current, ai_mask, lama_info = lama_service.restore(current, protect, damage["masks"]["missing_paper"])
            tick("lama_s", t)
            if lama_info["repaired_pixels"]:
                save("2c_ai_mask", Image.fromarray(ai_mask))
                save("2d_lama_repaired", current)
                save("2e_ai_regions_marked", lama_service.mark(current, ai_mask))
                steps.append(f"LaMa reconstructed {lama_info['repaired_pct']}% of the page in "
                             f"{len(lama_info['regions'])} region(s) outside text (AI-generated, marked)")
            else:
                steps.append("LaMa: no safe tear or hole outside text to repair")
        else:
            steps.append(f"LaMa unavailable ({why_lama}); tear repair skipped")
    base_for_docres = current

    report = {"damage": damage_service.summary(damage), "plan": plan, "ocr_available": False, "stages": {},
              "timings": timings, "paper_restoration": paper_info, "paper_quality": paper_quality,
              "lama": lama_info, "ai_generated_regions": lama_info.get("regions", []),
              "ai_generated_pct": lama_info.get("repaired_pct", 0.0)}

    def paper_candidate(src: Image.Image):
        """Paper normalisation (stains, tint, creases) applied to a stage output, ink protected."""
        nonlocal paper_info, paper_quality
        if not run_stage.get("paper_normalize"):
            return None
        notify(74, "Normalising stains and paper tone (handwriting protected)")
        t0 = time.time()
        paper_stages = {}
        out, paper_info = paper.restore(src, config.get("paper_tone", "white"), paper_stages)
        for name, image in paper_stages.items():
            save(f"4c_{name}", image)
        save("4d_paper_normalized", out)
        paper_quality = paper.quality(pre, out, p_mask)
        report["paper_restoration"], report["paper_quality"] = paper_info, paper_quality
        tick("paper_s", t0)
        return out

    if config.get("fast_mode", False):
        final = paper_candidate(current) or current
        report["mode"] = "fast"
        report["final_quality"] = paper.quality(pre, final, p_mask)
        report["chosen_stage"] = "paper_normalized" if final is not current else "lama"
        return _finish(final, pre, report, stage_dir, steps, notify, timings, t_all)

    # 5. DocRes: appearance when stains/fading, deblurring only when blurred
    docres_steps = []
    t = time.time()
    if run_stage.get("docres_deblur"):
        notify(54, "DocRes: deblurring text")
        current, ds = docres_service.restore(current, "deblurring")
        docres_steps += ds
    if run_stage.get("docres_appearance"):
        notify(60, "DocRes: restoring document appearance")
        current, ds = docres_service.restore(current, "appearance")
        docres_steps += ds
    if current.size != pre.size:
        current = current.resize(pre.size, Image.LANCZOS)
    steps.extend(docres_steps)
    save("2_docres", current)
    tick("docres_s", t)
    docres_out = current

    ok, why = ocr_service.available()
    if not ok:
        steps.append(f"OCR verification unavailable ({why}); text refinement used without OCR regions")
        mask = np.ones((pre.height, pre.width), bool)
        refined, rstats = tr.refine(pre, current, mask)
        save("3_text_refined", refined)
        report["refine"] = rstats
        final = refined
        report["final_quality"] = paper.quality(pre, final, p_mask)
        return _finish(final, pre, report, stage_dir, steps, notify, timings, t_all)

    # 6. text refinement + OCR line guard (one OCR call per page, not per line)
    report["ocr_available"] = True
    notify(66, "Reading text with OCR")
    t = time.time()
    ol = ocr_service.read(pre)
    ocr_conf = float(np.mean([l["score"] for l in ol])) if ol else 0.0
    reliable = len(ol) >= 3 and ocr_conf >= float(os.getenv("OCR_RELIABLE_CONF", "0.85"))
    report["ocr_reliable"] = reliable
    report["original_lines"] = ol
    if not reliable:
        # Handwriting / heavy damage: OCR cannot verify the text, so it must not drive pixel
        # changes. Choose between DocRes and paper normalisation by ink-preservation checks.
        tick("text_and_ocr_s", t)
        steps.append(f"OCR confidence {ocr_conf:.2f} is too low to verify text (typical for handwriting); "
                     "using stroke and dot preservation checks instead")
        cands = [("docres", docres_out)]
        pc = paper_candidate(docres_out)
        if pc is not None:
            cands.append(("paper_normalized", pc))
        scored = []
        for i, (name, im) in enumerate(cands):
            q = paper.quality(pre, im, p_mask)
            scored.append((_safe_quality(q), -q.get("stain_std", 99), i, name, im, q))
            report["stages"][name] = {"safe_ink_geometry": scored[-1][0], "image_quality": q}
        pool = [s for s in scored if s[0]] or scored
        best = max(pool, key=lambda s: (s[0], s[1], s[2]))
        final, report["chosen_stage"], report["final_quality"] = best[4], best[3], best[5]
        report["final_lines"] = ol
        report["comparison"] = ocr_service.compare(ol, ol)
        steps.append(f"Output stage: {best[3]} (strokes preserved {best[5].get('stroke_preservation')}, "
                     f"dots {best[5].get('dot_preservation')})")
        return _finish(final, pre, report, stage_dir, steps, notify, timings, t_all)
    cl = ocr_service.read(docres_out)
    mask = ocr_service.text_boxes(ol, (pre.height, pre.width)) | ocr_service.text_boxes(cl, (pre.height, pre.width))
    refined, rstats = tr.refine(pre, docres_out, mask)
    refined, nsp = tr.remove_dark_specks(refined, mask, cl)
    rstats["specks_removed"] = nsp
    save("3_text_refined", refined)
    rl = ocr_service.read(refined)
    notify(72, "Verifying text and handwriting preservation")
    if _score(rl, ol) < _score(cl, ol):
        guarded, gl, reverted = tr.line_guard(pre, refined, ol, rl, ocr_service.read)
        if reverted:
            guarded, n2 = tr.remove_dark_specks(guarded, mask, gl)
            rstats["specks_removed_after_guard"] = n2
    else:
        guarded, gl, reverted = refined, rl, []
    save("4_ocr_guarded", guarded)
    tick("text_and_ocr_s", t)

    # 7. speck cleanup outside text (accepted only if every OCR text region keeps its ink)
    cleaned, cl_lines, n_bg = guarded, gl, 0
    if run_stage.get("speck_cleanup"):
        t = time.time()
        cand, n_bg = tr.remove_background_specks(guarded, mask, gl)
        kept = _text_kept(guarded, cand, p_mask["ink"], mask)
        if n_bg and (kept is None or kept >= 0.995):
            cleaned = cand
            save("4b_specks_removed", cleaned)
            steps.append(f"Removed {n_bg} specks outside text (text ink kept: {kept})")
        else:
            n_bg = 0
            steps.append("Speck cleanup skipped: it would have touched text")
        tick("speck_s", t)

    # 8. choose the safest readable stage (paper normalisation competes on OCR agreement)
    cands = [("docres", docres_out, cl), ("text_refined", refined, rl), ("ocr_guarded", guarded, gl)]
    if cleaned is not guarded:
        cands.append(("specks_removed", cleaned, cl_lines))
    pc = paper_candidate(cleaned)
    if pc is not None:
        cands.append(("paper_normalized", pc, ocr_service.read(pc)))
    scored = []
    for i, (name, im, lines) in enumerate(cands):
        q = paper.quality(pre, im, p_mask)
        safe = _safe_quality(q) or (name == "specks_removed" and q.get("stroke_preservation", 0) >= 0.95)
        scored.append((safe, _score(lines, ol), i, name, im, lines, q))
    pool = [s for s in scored if s[0]] or scored
    best = max(pool, key=lambda s: (s[0], s[1][0], s[1][1], s[2]))
    final, chosen, final_lines = best[4], best[3], best[5]
    for safe, (agree, conf), _, name, _, lines, q in scored:
        report["stages"][name] = {"agreement_with_original_reading": agree, "mean_confidence": conf,
                                  "safe_ink_geometry": safe, "image_quality": q,
                                  "text": ocr_service.joined(lines)}
    report["stages"]["original"] = {"mean_confidence": _score(ol, ol)[1], "text": ocr_service.joined(ol)}
    report["chosen_stage"] = chosen
    report["refine"] = rstats
    report["reverted_lines"] = reverted
    report["comparison"] = ocr_service.compare(ol, final_lines)
    report["final_lines"] = final_lines
    report["final_quality"] = best[6]
    if ground_truth:
        report["ground_truth"] = {
            name: {"cer": ocr_service.cer(ground_truth, d["text"]), "wer": ocr_service.wer(ground_truth, d["text"])}
            for name, d in report["stages"].items()}
    if rstats["strokes_restored"] or nsp:
        steps.append(f"Restored {rstats['strokes_restored']} faint strokes; removed {nsp} specks on letters")
    if reverted:
        steps.append(f"OCR guard: {len(reverted)} line(s) re-rendered from original strokes")
    cmp_ = report["comparison"]
    steps.append(f"OCR check: {cmp_['restored_lines']} text lines, agreement with original "
                 f"{cmp_['char_agreement']}, {len(cmp_['missing'])} missing / {len(cmp_['changed'])} changed spans "
                 f"(output stage: {chosen})")
    return _finish(final, pre, report, stage_dir, steps, notify, timings, t_all)


def _finish(final, pre, report, stage_dir, steps, notify, timings, t_all):
    notify(78, "Saving restored document")
    if final.size != pre.size:  # never ship a resized page
        raise RuntimeError(f"final size {final.size} differs from input {pre.size}")
    save_path = stage_dir / "5_final.png"
    final.save(save_path)
    ai = report.get("ai_generated_regions") or []
    if ai:
        mask = np.zeros((pre.height, pre.width), np.uint8)
        ai_png = stage_dir / "2c_ai_mask.png"
        if ai_png.exists():
            mask = np.asarray(Image.open(ai_png).convert("L"))
        lama_service.mark(final, mask).save(stage_dir / "5_final_ai_marked.png")
    timings["total_s"] = round(time.time() - t_all, 1)
    (stage_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log.info("document pipeline done in %.1fs -> %s (%s)", timings["total_s"], stage_dir, timings)
    return final, report
