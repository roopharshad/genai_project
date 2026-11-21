import os
import psutil
try:  # PyTorch is optional: the project's model runs without it
    import torch
except ImportError:  # pragma: no cover
    torch = None
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import User, Workspace, Project, Asset, RestorationJob, EvaluationResult
from app.ml_engine.inference.registry import ModelRegistry
from app.api.deps import require_platform_admin, is_platform_admin
from app.core.config import settings

router = APIRouter()

@router.get("/overview")
def get_admin_overview(admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    """Retrieve platform-wide administration metrics."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_workspaces = db.query(Workspace).count()
    total_projects = db.query(Project).count()
    total_assets = db.query(Asset).count()
    
    total_jobs = db.query(RestorationJob).count()
    completed_jobs = db.query(RestorationJob).filter(RestorationJob.status == "completed").count()
    failed_jobs = db.query(RestorationJob).filter(RestorationJob.status == "failed").count()
    processing_jobs = db.query(RestorationJob).filter(RestorationJob.status.in_(["processing", "validating", "evaluating", "queued"])).count()

    # System resource diagnostics
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.STORAGE_PATH))

    return {
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "total_workspaces": total_workspaces,
            "total_projects": total_projects,
            "total_assets": total_assets,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "processing_jobs": processing_jobs
        },
        "system": {
            "pytorch_version": torch.__version__ if torch else "not installed",
            "cuda_available": bool(torch and torch.cuda.is_available()),
            "cpu_usage_percent": cpu_percent,
            "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "storage_path": str(settings.STORAGE_PATH)
        },
        "models": ModelRegistry.get_model_catalog()
    }


@router.get("/models")
def get_admin_models(admin: User = Depends(require_platform_admin)):
    """
    Retrieve full technical model management details for all six models:
    - Model name, description, architecture, type
    - Checkpoint availability, training status, model version
    - Deployment status (production/experimental/baseline), enabled/disabled status
    """
    return ModelRegistry.get_model_catalog()


@router.patch("/models/{model_id}")
def update_model_configuration(
    model_id: str,
    enabled: Optional[bool] = Body(None),
    deployment_status: Optional[str] = Body(None),
    admin: User = Depends(require_platform_admin)
):
    """
    Administrator control over model deployment status and availability.
    Allows enabling/disabling models and setting production or experimental status.
    """
    catalog = ModelRegistry.get_model_catalog()
    model = next((m for m in catalog if m["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    ModelRegistry.set_model_state(model_id, enabled=enabled, deployment_status=deployment_status)
    return {
        "status": "success",
        "model_id": model_id,
        "enabled": enabled if enabled is not None else model["is_enabled"],
        "deployment_status": deployment_status if deployment_status is not None else model["deployment_status"]
    }


@router.get("/users")
def list_all_users(admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    """List all platform users with roles and timestamps."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at
        }
        for u in users
    ]


@router.patch("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: str, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    """Activate or deactivate user account."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate the currently active administrator.")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = not u.is_active
    db.commit()
    return {"status": "success", "is_active": u.is_active}


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str = Body(..., embed=True),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Platform administrator promotions/demotions.
    Allowed roles: 'standard_user', 'platform_admin'.
    """
    if not is_platform_admin(admin):
        raise HTTPException(status_code=403, detail="Platform administrator privileges required.")

    if role not in ["standard_user", "platform_admin", "administrator"]:
        raise HTTPException(status_code=400, detail="Invalid platform role. Use 'standard_user' or 'platform_admin'.")

    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == admin.id and role == "standard_user":
        raise HTTPException(status_code=400, detail="Cannot demote yourself from platform administrator.")

    u.role = role
    db.commit()
    return {"status": "success", "user_id": u.id, "role": u.role}


@router.get("/jobs")
def list_all_jobs(
    status: Optional[str] = Query(None),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Platform-wide restoration jobs inspection."""
    query = db.query(RestorationJob)
    if status:
        query = query.filter(RestorationJob.status == status)
    jobs = query.order_by(RestorationJob.created_at.desc()).limit(100).all()
    return [
        {
            "id": j.id,
            "project_id": j.project_id,
            "asset_id": j.asset_id,
            "model_id": j.model_id,
            "model_name": j.model_name,
            "status": j.status,
            "progress": j.progress,
            "stage": j.stage,
            "error_message": j.error_message,
            "created_at": j.created_at,
            "completed_at": j.completed_at
        }
        for j in jobs
    ]


@router.post("/storage/clean-temp")
def clean_temporary_storage(admin: User = Depends(require_platform_admin)):
    """Clean temporary processing cache safely."""
    temp_dir = settings.TEMPORARY_DIR
    deleted_count = 0
    if temp_dir.exists():
        for f in temp_dir.glob("*"):
            if f.is_file() and f.name != ".gitkeep":
                try:
                    f.unlink()
                    deleted_count += 1
                except Exception:
                    pass
    return {"status": "success", "deleted_files": deleted_count}
