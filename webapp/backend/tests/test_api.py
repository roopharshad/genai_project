import io
import uuid
import pytest
from fastapi import HTTPException
from app.main import root
from app.api.v1.endpoints.restorations import get_available_models, get_restoration_presets
from app.api.v1.endpoints.analytics import list_experiments
from app.api.v1.endpoints.auth import login, register, LoginRequest, RegisterRequest
from app.api.v1.endpoints.projects import list_projects, get_project_details
from app.api.v1.endpoints.admin import get_admin_models, get_admin_overview
from app.core.database import SessionLocal
from app.models.entities import User, Project
from app.api.auth_guard import get_accessible_project_ids, verify_project_access

def test_root_endpoint():
    res = root()
    assert res["app"] == "DocRestore AI"
    assert res["status"] == "online"

def test_restoration_presets_and_models():
    # Presets for standard users
    presets = get_restoration_presets()
    assert len(presets) >= 3
    preset_ids = [p["id"] for p in presets]
    assert "recommended" in preset_ids
    assert "balanced" in preset_ids
    assert "high_quality" in preset_ids
    assert "gfpgan_prior" in preset_ids

    # Calling get_available_models without admin user returns presets
    normal_models = get_available_models(user=None)
    assert len(normal_models) >= 3

    # Calling as admin user returns full technical catalogue
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "demo@docrestore.ai").first()
        admin_models = get_available_models(full_catalog=True, user=admin)
        assert len(admin_models) >= 6
        ids = [m["id"] for m in admin_models]
        assert "residual_unet" in ids
        assert "conditional_diffusion" in ids
        assert "opencv" in ids
        assert "gfpgan" in ids
    finally:
        db.close()

def test_experiments_list():
    db = SessionLocal()
    try:
        exps = list_experiments(db)
        assert len(exps) >= 8
        codes = [e.experiment_code for e in exps]
        assert "E1" in codes
        assert "E5" in codes
        assert "E8" in codes
    finally:
        db.close()

def test_authentication_and_data_isolation():
    db = SessionLocal()
    try:
        # 1. Login as Admin
        req_admin = LoginRequest(email="demo@docrestore.ai", password="docrestore123")
        res_admin = login(req_admin, db)
        assert "access_token" in res_admin
        assert res_admin["user"]["role"] in ["administrator", "platform_admin"]

        # 2. Register Account A (Normal User)
        uid = uuid.uuid4().hex[:6]
        email_a = f"user_a_{uid}@test.com"
        reg_a = RegisterRequest(
            email=email_a,
            password="securePassword123",
            confirm_password="securePassword123",
            full_name="Account A User",
            workspace_name="Workspace A"
        )
        res_a = register(reg_a, db)
        assert res_a["user"]["role"] == "standard_user"

        # 3. Register Account B (Normal User)
        email_b = f"user_b_{uid}@test.com"
        reg_b = RegisterRequest(
            email=email_b,
            password="securePassword123",
            confirm_password="securePassword123",
            full_name="Account B User",
            workspace_name="Workspace B"
        )
        res_b = register(reg_b, db)
        assert res_b["user"]["role"] == "standard_user"

        user_a = db.query(User).filter(User.email == email_a).first()
        user_b = db.query(User).filter(User.email == email_b).first()

        # Create project in Workspace A
        proj_a = Project(
            workspace_id=res_a["user"]["default_workspace_id"],
            name="Project Alpha Private",
            created_by=user_a.id
        )
        db.add(proj_a)

        # Create project in Workspace B
        proj_b = Project(
            workspace_id=res_b["user"]["default_workspace_id"],
            name="Project Beta Private",
            created_by=user_b.id
        )
        db.add(proj_b)
        db.commit()

        # 4. Test Project List Isolation
        projects_a = list_projects(workspace_id=None, user=user_a, db=db)
        projects_b = list_projects(workspace_id=None, user=user_b, db=db)

        pids_a = [p.id for p in projects_a]
        pids_b = [p.id for p in projects_b]

        assert proj_a.id in pids_a
        assert proj_a.id not in pids_b
        assert proj_b.id in pids_b
        assert proj_b.id not in pids_a

        # 5. Test IDOR prevention: User B cannot access User A's private project details
        with pytest.raises(HTTPException) as exc_info:
            get_project_details(id=proj_a.id, user=user_b, db=db)
        assert exc_info.value.status_code in [403, 404]

        # 6. Test Admin protection: Normal user cannot pass administrator authorization check
        from app.api.auth_guard import require_platform_admin
        with pytest.raises(HTTPException) as exc_admin:
            require_platform_admin(user=user_a)
        assert exc_admin.value.status_code == 403

    finally:
        db.close()
