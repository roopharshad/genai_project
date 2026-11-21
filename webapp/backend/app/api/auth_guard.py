from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import (
    User,
    Workspace,
    WorkspaceMember,
    Project,
    Asset,
    RestorationJob,
    Notification
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Strictly authenticate user from Bearer JWT token.
    Never fall back to hardcoded, demo, or first user in database.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user record not found."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator."
        )

    return user


def is_platform_admin(user: Optional[User]) -> bool:
    """Check if user has platform-level administrator role."""
    if not user or not hasattr(user, 'role'):
        return False
    return user.role in ["platform_admin", "administrator", "PLATFORM_ADMIN"]


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Enforce platform-level administrator privilege."""
    if not is_platform_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator privileges required."
        )
    return user


def get_accessible_workspace_ids(db: Session, user: User) -> List[str]:
    """Retrieve all workspace IDs accessible to the current user."""
    if is_platform_admin(user):
        return [w.id for w in db.query(Workspace.id).all()]

    # Owned workspaces
    owned_ids = [w.id for w in db.query(Workspace.id).filter(Workspace.owner_id == user.id).all()]
    # Member workspaces
    member_ids = [
        m.workspace_id for m in db.query(WorkspaceMember.workspace_id).filter(
            WorkspaceMember.user_id == user.id
        ).all()
    ]
    return list(set(owned_ids + member_ids))


def get_accessible_project_ids(db: Session, user: User) -> List[str]:
    """Retrieve all project IDs accessible to the current user."""
    ws_ids = get_accessible_workspace_ids(db, user)
    if not ws_ids:
        return []
    return [p.id for p in db.query(Project.id).filter(Project.workspace_id.in_(ws_ids)).all()]


def verify_workspace_access(
    db: Session,
    user: User,
    workspace_id: str,
    require_write: bool = False
) -> Workspace:
    """Validate user has permission to access a specific workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    if is_platform_admin(user):
        return workspace

    if workspace.owner_id == user.id:
        return workspace

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace."
        )

    if require_write and member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify resources in this workspace."
        )

    return workspace


def verify_project_access(
    db: Session,
    user: User,
    project_id: str,
    require_write: bool = False
) -> Project:
    """Validate user has permission to access a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    verify_workspace_access(db, user, project.workspace_id, require_write=require_write)
    return project


def verify_asset_access(
    db: Session,
    user: User,
    asset_id: str,
    require_write: bool = False
) -> Asset:
    """Validate user has permission to access a specific asset."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    verify_project_access(db, user, asset.project_id, require_write=require_write)
    return asset


def verify_job_access(
    db: Session,
    user: User,
    job_id: str
) -> RestorationJob:
    """Validate user has permission to access a specific restoration job."""
    job = db.query(RestorationJob).filter(RestorationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restoration job not found")

    verify_project_access(db, user, job.project_id)
    return job

