from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import User, Workspace, WorkspaceMember
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
    members = []
    if workspace:
        members_records = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace.id).all()
        for m in members_records:
            u = db.query(User).filter(User.id == m.user_id).first()
            if u:
                members.append({
                    "id": m.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": m.role,
                    "joined_at": m.joined_at
                })

    return {
        "profile": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        },
        "workspace": {
            "id": workspace.id if workspace else None,
            "name": workspace.name if workspace else "Default Workspace",
            "members": members
        },
        "model_preferences": {
            "default_model": "residual_unet",
            "auto_evaluate_on_completion": True,
            "preserve_aspect_ratio": True,
            "extreme_neon_glow": True,
            "max_concurrent_jobs": 4
        },
        "system_info": {
            "version": "1.0.0-royal-spectrum",
            "framework": "OpenCV + hosted AI Image Restoration",
            "gpu_acceleration": False,
            "storage_mode": "Local / Safe-Isolated"
        }
    }


@router.patch("/profile")
def update_profile(
    full_name: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user.full_name = full_name
    db.commit()
    return {"status": "success", "full_name": user.full_name}

