import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.models.entities import User, Workspace, WorkspaceMember, UserSession
from app.schemas.api_schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.confirm_password is not None and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Always enforce standard_user role for public registration
    user = User(
        email=req.email.lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        role="standard_user",
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.flush()

    # Create default workspace
    ws_name = req.workspace_name or "Personal Workspace"
    workspace = Workspace(
        name=ws_name,
        slug=f"{ws_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        owner_id=user.id
    )
    db.add(workspace)
    db.flush()

    # Add workspace owner membership
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner"
    )
    db.add(member)

    # Generate tokens
    access_token = create_access_token(user.id, role=user.role)
    refresh_token = create_refresh_token(user.id)

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "default_workspace_id": workspace.id
        }
    }


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(user.id, role=user.role)
    refresh_token = create_refresh_token(user.id)

    # Find primary workspace
    ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "default_workspace_id": ws.id if ws else None
        }
    }


@router.get("/me")
def get_current_user_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "workspaces": [{"id": w.id, "name": w.name, "slug": w.slug} for w in workspaces]
    }

