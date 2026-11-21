from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Asset, AssetVersion, EvaluationResult, User
from app.api.deps import get_current_user, verify_asset_access

router = APIRouter()

@router.get("/{asset_id}")
def get_asset_comparison(
    asset_id: str,
    original_version_id: str = Query(None),
    restored_version_id: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve side-by-side version comparison data and reference metrics
    with strict asset authorization verification.
    """
    asset = verify_asset_access(db, user, asset_id)

    versions = db.query(AssetVersion).filter(AssetVersion.asset_id == asset.id).order_by(AssetVersion.version_number.asc()).all()
    if not versions:
        raise HTTPException(status_code=404, detail="No versions found for asset")

    # Default original is version 1
    orig_v = None
    if original_version_id:
        orig_v = next((v for v in versions if v.id == original_version_id), None)
    if not orig_v:
        orig_v = versions[0]

    # Default restored is the latest restored version
    rest_v = None
    if restored_version_id:
        rest_v = next((v for v in versions if v.id == restored_version_id), None)
    if not rest_v:
        restored_list = [v for v in versions if v.version_type == "restored"]
        rest_v = restored_list[-1] if restored_list else versions[-1]

    # Retrieve evaluation results for restored version
    eval_result = None
    if rest_v:
        eval_record = db.query(EvaluationResult).filter(EvaluationResult.asset_version_id == rest_v.id).first()
        if eval_record:
            eval_result = {
                "has_reference": eval_record.has_reference,
                "psnr": eval_record.psnr,
                "ssim": eval_record.ssim,
                "lpips": eval_record.lpips,
                "ocr_word_acc": eval_record.ocr_word_acc,
                "ocr_char_acc": eval_record.ocr_char_acc,
                "edge_preservation_score": eval_record.edge_preservation_score,
                "inference_time_ms": eval_record.inference_time_ms,
                "model_memory_mb": eval_record.model_memory_mb,
                "metrics_detail": eval_record.metrics_detail
            }

    return {
        "asset": {
            "id": asset.id,
            "project_id": asset.project_id,
            "original_filename": asset.original_filename,
            "resolution_category": asset.resolution_category,
            "degradation_analysis": asset.degradation_analysis
        },
        "original_version": {
            "id": orig_v.id,
            "version_number": orig_v.version_number,
            "version_type": orig_v.version_type,
            "stored_filename": orig_v.stored_filename,
            "image_url": f"/storage/originals/{orig_v.stored_filename}",
            "width": orig_v.width,
            "height": orig_v.height,
            "file_size": orig_v.file_size
        },
        "restored_version": {
            "id": rest_v.id,
            "version_number": rest_v.version_number,
            "version_type": rest_v.version_type,
            "stored_filename": rest_v.stored_filename,
            "image_url": f"/storage/restored/{rest_v.stored_filename}",
            "width": rest_v.width,
            "height": rest_v.height,
            "file_size": rest_v.file_size,
            "model_id": rest_v.model_id,
            "config_summary": rest_v.config_summary
        } if rest_v else None,
        "available_versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "version_type": v.version_type,
                "model_id": v.model_id,
                "created_at": v.created_at
            }
            for v in versions
        ],
        "evaluation": eval_result
    }
