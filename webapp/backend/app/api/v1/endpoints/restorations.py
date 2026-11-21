from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import RestorationJob, Asset, Project, User
from app.schemas.api_schemas import RestorationJobOut, JobCreateRequest
from app.ml_engine.inference.registry import ModelRegistry
from app.workers.task_runner import TaskRunner
from app.api.deps import (
    get_current_user,
    is_platform_admin,
    get_accessible_project_ids,
    verify_project_access,
    verify_asset_access,
    verify_job_access
)

router = APIRouter()

@router.get("/presets")
def get_restoration_presets():
    """Returns user-friendly restoration presets for standard users."""
    return ModelRegistry.get_presets()

@router.get("/models")
def get_available_models(
    full_catalog: bool = False,
    user: Optional[User] = Depends(get_current_user)
):
    """
    Returns restoration options.
    Normal users receive the user-friendly presets by default.
    Platform administrators can inspect the complete six-model technical catalog.
    """
    if user and is_platform_admin(user) and full_catalog:
        return ModelRegistry.get_model_catalog()
    if user and is_platform_admin(user):
        return ModelRegistry.get_model_catalog()
    # Default for normal users: return simplified presets
    return ModelRegistry.get_presets()

@router.post("/jobs", response_model=RestorationJobOut)
def create_restoration_job(
    req: JobCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and dispatch a restoration job with strict authorization and preset mapping."""
    # Verify user has access to target project and asset
    project = verify_project_access(db, user, req.project_id, require_write=True)
    asset = verify_asset_access(db, user, req.asset_id, require_write=True)

    # Resolve preset or technical model
    target_model_id, default_params = ModelRegistry.resolve_preset(req.model_id)

    # Permission check: normal users cannot bypass presets to run experimental/internal models
    if not is_platform_admin(user):
        preset_ids = [p["id"] for p in ModelRegistry.get_presets()]
        allowed_direct_models = ["residual_unet", "opencv"]
        if req.model_id not in preset_ids and target_model_id not in allowed_direct_models:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Technical model selection is restricted. Please select an approved preset (Recommended, Balanced, High Quality)."
            )

    # Verify model is registered and enabled
    catalog = ModelRegistry.get_model_catalog()
    model_meta = next((m for m in catalog if m["id"] == target_model_id), None)
    if not model_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Restoration model '{target_model_id}' is unavailable."
        )

    if not model_meta.get("is_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_meta['name']}' is temporarily disabled by administrator policy."
        )

    # Check checkpoint availability
    if not model_meta.get("checkpoint_available", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_meta['name']}' checkpoint is missing or untrained. Restoration cannot proceed."
        )

    merged_params = {**default_params, **(req.config_params or {})}

    job = RestorationJob(
        project_id=project.id,
        asset_id=asset.id,
        model_id=target_model_id,
        model_name=model_meta["name"],
        status="queued",
        progress=0,
        stage="Queued in pipeline",
        config_params=merged_params
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to background task runner
    TaskRunner.dispatch_job(job.id)

    return job

@router.get("/jobs", response_model=List[RestorationJobOut])
def list_jobs(
    project_id: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List restoration jobs strictly filtered by user's authorized projects."""
    accessible_p_ids = get_accessible_project_ids(db, user)
    if not accessible_p_ids:
        return []

    query = db.query(RestorationJob)
    if project_id:
        verify_project_access(db, user, project_id)
        query = query.filter(RestorationJob.project_id == project_id)
    else:
        query = query.filter(RestorationJob.project_id.in_(accessible_p_ids))

    if asset_id:
        verify_asset_access(db, user, asset_id)
        query = query.filter(RestorationJob.asset_id == asset_id)
    if status:
        query = query.filter(RestorationJob.status == status)

    jobs = query.order_by(RestorationJob.created_at.desc()).all()
    return jobs

@router.get("/jobs/{id}", response_model=RestorationJobOut)
def get_job(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve single restoration job with authorization check."""
    job = verify_job_access(db, user, id)
    return job
