import os
import shutil
import numpy as np
from PIL import Image
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Asset, AssetVersion, Project, User
from app.schemas.api_schemas import AssetOut, AssetVersionOut
from app.storage.file_storage import FileStorageService
from app.ml_engine.degradation.pipeline import DegradationPipeline, QualityAnalyzer
from app.api.deps import (
    get_current_user,
    get_accessible_project_ids,
    verify_project_access,
    verify_asset_access
)

router = APIRouter()

@router.post("/upload", response_model=AssetOut)
def upload_asset(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new UI screenshot asset, strictly checking project ownership."""
    project = verify_project_access(db, user, project_id, require_write=True)

    stored_filename, file_size, width, height, mime_type = FileStorageService.save_uploaded_original(file)

    # Analyze degradation characteristics
    original_path = FileStorageService.get_file_path(stored_filename)
    degradation_analysis = QualityAnalyzer.analyze_image(str(original_path))

    # Resolution category
    total_pixels = width * height
    res_cat = "low_res" if total_pixels < 800 * 600 else ("standard" if total_pixels < 1920 * 1080 else "high_res")

    asset = Asset(
        project_id=project.id,
        original_filename=file.filename or "screenshot.png",
        stored_filename=stored_filename,
        file_size=file_size,
        mime_type=mime_type,
        width=width,
        height=height,
        resolution_category=res_cat,
        status="active",
        degradation_analysis=degradation_analysis
    )
    db.add(asset)
    db.flush()

    # Create AssetVersion 1 (Original)
    v1 = AssetVersion(
        asset_id=asset.id,
        version_number=1,
        version_type="original",
        stored_filename=stored_filename,
        file_size=file_size,
        width=width,
        height=height,
        config_summary={"note": "Original uploaded screenshot"}
    )
    db.add(v1)
    db.commit()
    db.refresh(asset)

    return asset


@router.get("/", response_model=List[AssetOut])
def list_assets(
    project_id: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List assets strictly filtered by authorized projects."""
    accessible_p_ids = get_accessible_project_ids(db, user)
    if not accessible_p_ids:
        return []

    query = db.query(Asset)
    if project_id:
        verify_project_access(db, user, project_id)
        query = query.filter(Asset.project_id == project_id)
    else:
        query = query.filter(Asset.project_id.in_(accessible_p_ids))

    if resolution:
        query = query.filter(Asset.resolution_category == resolution)
    if search:
        query = query.filter(Asset.original_filename.ilike(f"%{search}%"))

    assets = query.order_by(Asset.created_at.desc()).all()
    return assets


@router.get("/{id}", response_model=AssetOut)
def get_asset(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve asset with strict ownership authorization."""
    asset = verify_asset_access(db, user, id)
    return asset


@router.post("/{id}/synthetic-degrade")
def create_synthetic_degraded_variant(
    id: str,
    blur_strength: float = 1.5,
    blur_type: str = "gaussian",
    noise_level: float = 15.0,
    jpeg_quality: int = 40,
    downsample_factor: float = 2.0,
    seed: int = 42,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate reproducible controlled degradation sample: Y = D(J(N(H(X))))."""
    asset = verify_asset_access(db, user, id, require_write=True)

    original_path = FileStorageService.get_file_path(asset.stored_filename)
    if not original_path or not original_path.exists():
        raise HTTPException(status_code=404, detail="Original image file not found")

    with Image.open(original_path) as pil_img:
        img_np = np.array(pil_img.convert("RGB"))

    degrade_config = {
        "blur_strength": blur_strength,
        "blur_type": blur_type,
        "noise_level": noise_level,
        "jpeg_quality": jpeg_quality,
        "downsample_factor": downsample_factor,
        "resample_back": True,
        "seed": seed
    }

    degraded_np, meta = DegradationPipeline.degrade(img_np, degrade_config)
    degraded_pil = Image.fromarray(degraded_np)
    stored_name, f_size, w, h = FileStorageService.save_restored_image(degraded_pil, format="PNG")

    v_count = db.query(AssetVersion).filter(AssetVersion.asset_id == asset.id).count()
    synthetic_version = AssetVersion(
        asset_id=asset.id,
        version_number=v_count + 1,
        version_type="synthetic_degraded",
        stored_filename=stored_name,
        file_size=f_size,
        width=w,
        height=h,
        config_summary=meta
    )
    db.add(synthetic_version)
    db.commit()
    db.refresh(synthetic_version)

    return {
        "status": "success",
        "asset_id": asset.id,
        "version_id": synthetic_version.id,
        "degradation_metadata": meta,
        "image_url": f"/storage/restored/{stored_name}"
    }


@router.delete("/{id}")
def delete_asset(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Safely delete asset and its versions with authorization check."""
    asset = verify_asset_access(db, user, id, require_write=True)
    db.delete(asset)
    db.commit()
    return {"status": "success", "deleted_asset_id": id}
