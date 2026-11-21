import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Workspace, WorkspaceMember, User
from app.schemas.api_schemas import WorkspaceCreate, WorkspaceOut
from app.api.deps import (
    get_current_user,
    is_platform_admin,
    get_accessible_workspace_ids,
    verify_workspace_access
)

router = APIRouter()

@router.get("/", response_model=List[WorkspaceOut])
def list_workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List workspaces that the user owns or is a member of."""
    ws_ids = get_accessible_workspace_ids(db, user)
    workspaces = db.query(Workspace).filter(Workspace.id.in_(ws_ids)).order_by(Workspace.created_at.desc()).all()
    
    out = []
    for ws in workspaces:
        m_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
        out.append(WorkspaceOut(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            description=ws.description,
            owner_id=ws.owner_id,
            created_at=ws.created_at,
            member_count=m_count
        ))
    return out

@router.post("/", response_model=WorkspaceOut)
def create_workspace(req: WorkspaceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new workspace with current user as owner."""
    slug = f"{req.name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    ws = Workspace(
        name=req.name,
        slug=slug,
        description=req.description,
        owner_id=user.id
    )
    db.add(ws)
    db.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(ws)

    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at,
        member_count=1
    )

@router.get("/{id}", response_model=WorkspaceOut)
def get_workspace_details(id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get single workspace with strict authorization check."""
    ws = verify_workspace_access(db, user, id)
    m_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at,
        member_count=m_count
    )
