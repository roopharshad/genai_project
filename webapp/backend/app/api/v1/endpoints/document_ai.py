"""Document AI endpoints: damage analysis, OCR review, Gemini chat, quality, AI reconstruction.

All endpoints reuse the existing services in backend/services (damage, OCR, LaMa, quality,
Gemini). Originals are never modified; AI reconstruction is saved as a new, labelled version.
"""
import io
import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_asset_access
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import AssetVersion, DocumentText, EvaluationResult, User
from app.ml_engine.inference.registry import STAGES_DIR  # also sets sys.path for backend.services
from app.storage.file_storage import FileStorageService
from backend.services import (damage_service, gemini_service, lama_service, ocr_service,
                              paper_restore_service as paper, quality_service)

router = APIRouter()
UNREADABLE_CONF = 0.80


# ---------------------------------------------------------------- helpers
def _versions(db: Session, asset_id: str) -> list[AssetVersion]:
    return db.query(AssetVersion).filter(AssetVersion.asset_id == asset_id).order_by(AssetVersion.version_number).all()


def _pick_version(db: Session, asset, version_id: Optional[str]) -> AssetVersion:
    vs = _versions(db, asset.id)
    if version_id:
        v = next((v for v in vs if v.id == version_id), None)
        if not v:
            raise HTTPException(404, "Version not found")
        return v
    restored = [v for v in vs if v.version_type in ("restored", "ai_reconstructed", "enhanced")]
    return restored[-1] if restored else vs[0]


def _image(v: AssetVersion) -> Image.Image:
    p = FileStorageService.get_file_path(v.stored_filename)
    if not p:
        raise HTTPException(404, "Image file missing from storage")
    with Image.open(p) as im:
        return im.convert("RGB")


def _url(v: AssetVersion) -> str:
    folder = "originals" if v.version_type == "original" else "restored"
    return f"/storage/{folder}/{v.stored_filename}"


def _stage_dir(v: AssetVersion) -> Optional[Path]:
    op = ((v.config_summary or {}).get("operational") or {})
    url = op.get("stages_url") or (v.config_summary or {}).get("stages_url")
    if not url:
        return None
    d = STAGES_DIR / url.rstrip("/").split("/")[-1]
    return d if d.is_dir() else None


def _report(v: AssetVersion) -> dict:
    d = _stage_dir(v)
    if d and (d / "report.json").exists():
        return json.loads((d / "report.json").read_text(encoding="utf-8"))
    return ((v.config_summary or {}).get("operational") or {}).get("text_report") or {}


def _reference(asset, v: AssetVersion, db: Session) -> Image.Image:
    """Same-size reference for a restored version: the cropped page it was made from."""
    d = _stage_dir(v)
    if d and (d / "1_preprocessed.png").exists():
        with Image.open(d / "1_preprocessed.png") as im:
            return im.convert("RGB")
    return _image(_versions(db, asset.id)[0])


def _lines_payload(lines: list) -> list:
    return [{"text": l["text"], "score": l["score"], "box": l["box"], "unreadable": l["score"] < UNREADABLE_CONF}
            for l in lines]


def _saved_text(db: Session, asset_id: str, version_id: str) -> Optional[DocumentText]:
    return (db.query(DocumentText).filter(DocumentText.asset_id == asset_id, DocumentText.version_id == version_id)
            .order_by(DocumentText.updated_at.desc()).first())


def _approved_text(db: Session, asset_id: str) -> Optional[str]:
    t = (db.query(DocumentText).filter(DocumentText.asset_id == asset_id, DocumentText.status == "approved")
         .order_by(DocumentText.updated_at.desc()).first())
    return t.edited_text if t else None


def _temp_png(img: Image.Image, prefix: str) -> str:
    name = f"{prefix}_{uuid.uuid4().hex}.png"
    img.save(settings.TEMPORARY_DIR / name)
    return f"/storage/temporary/{name}"


# ---------------------------------------------------------------- 1. damage + model plan
@router.get("/{asset_id}/damage")
def analyze_damage(asset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id)
    img = _image(_versions(db, asset.id)[0])
    t = time.time()
    rep = damage_service.detect(img)
    plan = damage_service.plan(rep)
    return {"asset_id": asset.id, "elapsed_s": round(time.time() - t, 2), **damage_service.summary(rep),
            "plan": plan, "damage_map_url": _temp_png(damage_service.overlay(img, rep["masks"]), "damage")}


# ---------------------------------------------------------------- 2. OCR review
class OcrSave(BaseModel):
    version_id: Optional[str] = None
    lines: List[str]
    approve: bool = True


@router.get("/{asset_id}/ocr")
def get_ocr(asset_id: str, version_id: Optional[str] = None, refresh: bool = False,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id)
    v = _pick_version(db, asset, version_id)
    saved = _saved_text(db, asset.id, v.id)
    source = "saved"
    if saved and saved.ocr_lines and not refresh:
        lines = saved.ocr_lines
    else:
        rep = _report(v)
        cached = rep.get("final_lines") if v.version_type in ("restored", "enhanced") else None
        t = time.time()
        if cached and not refresh:
            lines, source = _lines_payload(cached), "restoration_report"
        else:
            ok, why = ocr_service.available()
            if not ok:
                raise HTTPException(503, f"OCR unavailable: {why}")
            lines, source = _lines_payload(ocr_service.read(_image(v))), f"ocr ({time.time() - t:.1f}s)"
        if saved:
            saved.ocr_lines = lines
        else:
            saved = DocumentText(asset_id=asset.id, version_id=v.id, ocr_lines=lines, status="draft", updated_by=user.id)
            db.add(saved)
        db.commit()
        db.refresh(saved)
    damage = damage_service.detect(_image(v))
    regions = damage["damages"]["tears_missing"].get("regions", [])
    return {"asset_id": asset.id, "version_id": v.id, "version_type": v.version_type, "image_url": _url(v),
            "width": v.width, "height": v.height, "source": source, "lines": lines,
            "unreadable_lines": sum(1 for l in lines if l["unreadable"]),
            "damaged_regions": regions, "status": saved.status, "edited_text": saved.edited_text,
            "mean_confidence": round(float(np.mean([l["score"] for l in lines])), 4) if lines else None}


@router.put("/{asset_id}/ocr")
def save_ocr(asset_id: str, body: OcrSave, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id, require_write=True)
    v = _pick_version(db, asset, body.version_id)
    saved = _saved_text(db, asset.id, v.id)
    if not saved:
        saved = DocumentText(asset_id=asset.id, version_id=v.id, ocr_lines=[], updated_by=user.id)
        db.add(saved)
    saved.edited_text = "\n".join(l.rstrip() for l in body.lines)
    saved.status = "approved" if body.approve else "draft"
    saved.updated_by = user.id
    db.commit()
    changed = sum(1 for a, b in zip(body.lines, [l["text"] for l in (saved.ocr_lines or [])]) if a.strip() != b.strip())
    return {"status": saved.status, "version_id": v.id, "lines_saved": len(body.lines), "lines_corrected": changed}


@router.get("/{asset_id}/ocr/export")
def export_text(asset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id)
    from fastapi.responses import PlainTextResponse
    text = _approved_text(db, asset.id)
    if text is None:
        raise HTTPException(404, "No approved transcription yet")
    return PlainTextResponse(text, headers={"Content-Disposition": f'attachment; filename="{asset.original_filename}.txt"'})


# ---------------------------------------------------------------- 3. Gemini chat
class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[ChatTurn] = []
    version_id: Optional[str] = None
    include_image: bool = True


@router.get("/status")
def ai_status():
    ok, why = gemini_service.available()
    return {"gemini_configured": ok, "gemini_detail": why, "gemini_models": gemini_service.models(),
            "lama_available": lama_service.available()[0], "ocr_available": ocr_service.available()[0]}


@router.post("/{asset_id}/chat")
def chat(asset_id: str, body: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id)
    if not body.question.strip():
        raise HTTPException(400, "Question is empty")
    v = _pick_version(db, asset, body.version_id)
    approved = _approved_text(db, asset.id)
    saved = _saved_text(db, asset.id, v.id)
    rep = _report(v)
    if approved:
        text, text_src = approved, "user-approved transcription"
    elif saved and saved.ocr_lines:
        text, text_src = "\n".join(l["text"] for l in saved.ocr_lines), "OCR (not reviewed)"
    elif rep.get("final_lines"):
        text, text_src = ocr_service.joined(rep["final_lines"]), "OCR (not reviewed)"
    else:
        text, text_src = "", "none"
    op = ((v.config_summary or {}).get("operational") or {})
    dmg = rep.get("damage") or {}
    damage_lines = [f"- {k}: {d['level']} ({d['evidence']})" for k, d in (dmg.get("damages") or {}).items()]
    system = (
        "You are DocRestore AI's document assistant. Answer questions about ONE historical document using the "
        "attached page image and the extracted text below. Rules: answer only from the document; if a word is "
        "unreadable or uncertain, say so and mark guesses with [?]; never invent content; when quoting, quote "
        "exactly; be concise. You can summarise, explain archaic words, give context, and translate on request.\n\n"
        f"Document: {asset.original_filename}\n"
        f"Text source: {text_src}\n--- EXTRACTED TEXT ---\n{text or '(no text extracted)'}\n--- END TEXT ---\n"
        f"Restoration steps: {'; '.join(op.get('steps', [])) or 'not restored yet'}\n"
        f"Detected damage:\n{chr(10).join(damage_lines) or '- not analysed'}\n"
        f"AI-reconstructed area: {rep.get('ai_generated_pct', 0)}% of the page (not original content)."
    )
    images = []
    if body.include_image:
        im = _image(v)
        im.thumbnail((1600, 1600))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        images.append(("image/jpeg", buf.getvalue()))
    try:
        r = gemini_service.generate(system, [h.model_dump() for h in body.history], body.question, images=images)
    except gemini_service.GeminiError as exc:
        raise HTTPException(503, str(exc))
    return {"answer": r["text"], "model": r["model"], "text_source": text_src, "version_id": v.id}


# ---------------------------------------------------------------- 4. quality evaluation
@router.get("/{asset_id}/quality")
def quality(asset_id: str, version_id: Optional[str] = None, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id)
    v = _pick_version(db, asset, version_id)
    if v.version_type == "original":
        raise HTTPException(400, "Restore the document first; there is nothing to compare yet")
    ev = db.query(EvaluationResult).filter(EvaluationResult.asset_version_id == v.id).first()
    cached = (ev.metrics_detail or {}).get("document_quality") if ev else None
    approved = _approved_text(db, asset.id)
    if cached and not approved:
        return {"version_id": v.id, **cached}
    rep = _report(v)
    t = time.time()
    res = quality_service.evaluate(_reference(asset, v, db), _image(v), rep, approved,
                                   rep.get("final_lines") if not approved else None)
    res["elapsed_s"] = round(time.time() - t, 1)
    if ev:
        ev.metrics_detail = {**(ev.metrics_detail or {}), "document_quality": res}
        db.commit()
    return {"version_id": v.id, **res}


# ---------------------------------------------------------------- 5. AI reconstruction (LaMa)
class ReconstructRequest(BaseModel):
    version_id: Optional[str] = None
    include_text_areas: bool = False  # True = also fill damage that overlaps writing (AI-invented content)


@router.post("/{asset_id}/reconstruct")
def reconstruct(asset_id: str, body: ReconstructRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    asset = verify_asset_access(db, user, asset_id, require_write=True)
    ok, why = lama_service.available()
    if not ok:
        raise HTTPException(503, f"LaMa unavailable: {why}")
    v = _pick_version(db, asset, body.version_id)
    img = _image(v)
    t = time.time()
    dmg = damage_service.detect(img)
    m = paper.ink_mask(img)
    mask = dmg["masks"]["tears_missing"].copy()
    if not body.include_text_areas:
        import cv2
        near_text = cv2.dilate(m["protect"].astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        mask &= ~near_text
    pixels = int(mask.sum())
    if pixels == 0:
        return {"status": "nothing_to_reconstruct", "message": "No tears, holes or missing regions found"
                + ("" if body.include_text_areas else " outside text") + "."}
    import cv2
    mask = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) * 255
    out = lama_service.inpaint(img, mask)
    marked = lama_service.mark(out, mask)
    regions = lama_service.regions(mask)
    stored, size, w, h = FileStorageService.save_restored_image(out, "PNG")
    marked_stored, _, _, _ = FileStorageService.save_restored_image(marked, "PNG")
    mask_name = f"aimask_{uuid.uuid4().hex}.png"
    Image.fromarray(mask).save(settings.RESTORED_DIR / mask_name)
    pct = round(100 * pixels / (img.width * img.height), 3)
    nv = AssetVersion(asset_id=asset.id, version_number=len(_versions(db, asset.id)) + 1,
                      version_type="ai_reconstructed", stored_filename=stored, file_size=size, width=w, height=h,
                      model_id="lama",
                      config_summary={"model_name": "LaMa (big-lama) reconstruction", "source_version_id": v.id,
                                      "ai_generated": True, "ai_generated_pct": pct, "ai_regions": regions,
                                      "includes_text_areas": body.include_text_areas,
                                      "marked_url": f"/storage/restored/{marked_stored}",
                                      "mask_url": f"/storage/restored/{mask_name}",
                                      "operational": {"steps": [f"LaMa reconstructed {pct}% of the page in {len(regions)} region(s)"
                                                                + (" including areas with writing: reconstructed letters are AI guesses"
                                                                   if body.include_text_areas else " outside text")],
                                                      "stages_url": ((v.config_summary or {}).get("operational") or {}).get("stages_url")}})
    db.add(nv)
    db.commit()
    return {"status": "ok", "version_id": nv.id, "elapsed_s": round(time.time() - t, 1),
            "image_url": f"/storage/restored/{stored}", "marked_url": f"/storage/restored/{marked_stored}",
            "ai_generated_pct": pct, "regions": regions, "includes_text_areas": body.include_text_areas}
