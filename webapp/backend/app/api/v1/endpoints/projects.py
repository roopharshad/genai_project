from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Project, Asset, Workspace, User
from app.schemas.api_schemas import ProjectCreate, ProjectOut
from app.api.deps import (
    get_current_user,
    get_accessible_workspace_ids,
    verify_workspace_access,
    verify_project_access
)

router = APIRouter()

@router.get("/", response_model=List[ProjectOut])
def list_projects(
    workspace_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List projects strictly scoped to user's authorized workspaces."""
    accessible_ws_ids = get_accessible_workspace_ids(db, user)
    if not accessible_ws_ids:
        return []

    query = db.query(Project)
    if workspace_id:
        verify_workspace_access(db, user, workspace_id)
        query = query.filter(Project.workspace_id == workspace_id)
    else:
        query = query.filter(Project.workspace_id.in_(accessible_ws_ids))

    projects = query.order_by(Project.created_at.desc()).all()

    out = []
    for p in projects:
        a_count = db.query(Asset).filter(Asset.project_id == p.id).count()
        out.append(ProjectOut(
            id=p.id,
            workspace_id=p.workspace_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            asset_count=a_count
        ))
    return out

@router.post("/", response_model=ProjectOut)
def create_project(
    req: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project within an authorized workspace."""
    ws = verify_workspace_access(db, user, req.workspace_id, require_write=True)

    p = Project(
        workspace_id=ws.id,
        name=req.name,
        description=req.description,
        created_by=user.id
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return ProjectOut(
        id=p.id,
        workspace_id=p.workspace_id,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        asset_count=0
    )

@router.get("/{id}")
def get_project_details(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve single project with strict workspace access verification."""
    p = verify_project_access(db, user, id)
    asset_count = db.query(Asset).filter(Asset.project_id == p.id).count()
    return {
        "id": p.id,
        "workspace_id": p.workspace_id,
        "name": p.name,
        "description": p.description,
        "created_at": p.created_at,
        "asset_count": asset_count
    }
