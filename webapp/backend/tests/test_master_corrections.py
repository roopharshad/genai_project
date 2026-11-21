import uuid
import pytest
import numpy as np
from PIL import Image
from fastapi import HTTPException
from app.api.v1.endpoints.auth import register, login, RegisterRequest, LoginRequest
from app.api.v1.endpoints.projects import list_projects, create_project, get_project_details, ProjectCreate
from app.api.v1.endpoints.assets import list_assets, get_asset
from app.api.v1.endpoints.restorations import create_restoration_job, list_jobs, get_job, get_available_models, get_restoration_presets, JobCreateRequest
from app.api.v1.endpoints.admin import get_admin_models, update_model_configuration, update_user_role
from app.api.auth_guard import require_platform_admin, verify_project_access, verify_asset_access, verify_job_access
from app.core.database import SessionLocal
from app.models.entities import User, Workspace, Project, Asset, AssetVersion, RestorationJob
from app.ml_engine.inference.registry import ModelRegistry
from app.workers.task_runner import TaskRunner

def test_part1_and_part3_registration_and_role_security():
    db = SessionLocal()
    try:
        # Test: Public registration cannot create PLATFORM_ADMIN even if role is tampered with
        uid = uuid.uuid4().hex[:6]
        email = f"attacker_{uid}@test.com"
        req = RegisterRequest(
            email=email,
            password="password123",
            confirm_password="password123",
            full_name="Attacker Trying Admin",
            workspace_name="Insecure Workspace"
        )
        res = register(req, db)
        user = db.query(User).filter(User.email == email).first()
        assert user.role == "standard_user"
        assert res["user"]["role"] == "standard_user"

        # Verify normal user fails admin check
        with pytest.raises(HTTPException) as exc:
            require_platform_admin(user=user)
        assert exc.value.status_code == 403

        # Verify normal user cannot call admin role promotion
        with pytest.raises(HTTPException) as exc2:
            update_user_role(user_id=user.id, role="platform_admin", admin=user, db=db)
        assert exc2.value.status_code == 403
    finally:
        db.close()


def test_part1_three_account_data_isolation():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6]
        # Account A: Normal user
        email_a = f"account_a_{uid}@test.com"
        res_a = register(RegisterRequest(email=email_a, password="pass123", full_name="User A"), db)
        user_a = db.query(User).filter(User.email == email_a).first()

        # Account B: Another normal user
        email_b = f"account_b_{uid}@test.com"
        res_b = register(RegisterRequest(email=email_b, password="pass123", full_name="User B"), db)
        user_b = db.query(User).filter(User.email == email_b).first()

        # Account C: Platform administrator
        admin = db.query(User).filter(User.email == "demo@docrestore.ai").first()

        # Create private project for Account A
        p_a = Project(workspace_id=res_a["user"]["default_workspace_id"], name="Account A Secrets", created_by=user_a.id)
        db.add(p_a)

        # Create private project for Account B
        p_b = Project(workspace_id=res_b["user"]["default_workspace_id"], name="Account B Secrets", created_by=user_b.id)
        db.add(p_b)
        db.commit()

        # Create private asset in Account A's project
        asset_a = Asset(
            project_id=p_a.id,
            original_filename="secret_screenshot_a.png",
            stored_filename="fake_stored_a.png",
            file_size=1024,
            mime_type="image/png",
            width=256,
            height=256,
            resolution_category="standard"
        )
        db.add(asset_a)
        db.commit()

        # Verify Account A sees own projects
        projs_a = list_projects(workspace_id=None, user=user_a, db=db)
        assert p_a.id in [p.id for p in projs_a]
        assert p_b.id not in [p.id for p in projs_a]

        # Verify Account B sees own projects
        projs_b = list_projects(workspace_id=None, user=user_b, db=db)
        assert p_b.id in [p.id for p in projs_b]
        assert p_a.id not in [p.id for p in projs_b]

        # Verify IDOR: Account B cannot access Account A's asset
        with pytest.raises(HTTPException) as exc_asset:
            get_asset(id=asset_a.id, user=user_b, db=db)
        assert exc_asset.value.status_code in [403, 404]

        # Verify Account C (Platform Admin) has authorized oversight
        admin_projs = list_projects(workspace_id=None, user=admin, db=db)
        admin_pids = [p.id for p in admin_projs]
        assert p_a.id in admin_pids
        assert p_b.id in admin_pids

    finally:
        db.close()


def test_part2_and_part4_residual_unet_execution():
    # Verify Residual U-Net checkpoint loaded and active
    model_cat = ModelRegistry.get_model_catalog()
    unet_meta = next(m for m in model_cat if m["id"] == "residual_unet")
    assert unet_meta["checkpoint_available"] is True
    assert "Trained" in unet_meta["training_status"]

    # Run inference on degraded sample
    clean_sample = np.full((128, 128, 3), 210, dtype=np.uint8)
    clean_sample[30:70, 30:100] = [10, 30, 160] # Button
    clean_sample[45:55, 40:90] = [255, 255, 255] # Text line

    # Degrade it
    from app.ml_engine.degradation.pipeline import DegradationPipeline
    degraded, _ = DegradationPipeline.degrade(clean_sample, {"blur_strength": 1.6, "noise_level": 12.0})

    # Restore using UI-Aware Residual U-Net
    restored, op_metrics = ModelRegistry.run_restoration("residual_unet", degraded, {"blend_ratio": 1.0})

    # Verify visible difference and real model execution
    diff = np.abs(restored.astype(float) - degraded.astype(float))
    assert np.max(diff) > 0, "Residual U-Net produced zero modifications!"
    assert np.mean(diff) > 2.0, "Residual U-Net output is too close to degraded input!"
    assert op_metrics["model_id"] == "residual_unet"
    assert "inference_time_ms" in op_metrics
    assert op_metrics["output_resolution"] == "128x128"


def test_part5_model_visibility_and_presets():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == "standard_user").first()
        admin = db.query(User).filter(User.email == "demo@docrestore.ai").first()

        # Normal user calling /models receives only presets
        normal_options = get_available_models(full_catalog=False, user=user)
        assert len(normal_options) >= 3
        preset_ids = [p["id"] for p in normal_options]
        assert "recommended" in preset_ids
        assert "gfpgan_prior" in preset_ids
        assert "balanced" in preset_ids
        assert "high_quality" in preset_ids

        # Admin calling /models with full_catalog receives all models including GFPGAN
        admin_options = get_available_models(full_catalog=True, user=admin)
        assert len(admin_options) >= 6
        model_ids = [m["id"] for m in admin_options]
        assert "residual_unet" in model_ids
        assert "opencv" in model_ids
        assert "srcnn" in model_ids
        assert "realesrgan" in model_ids
        assert "gfpgan" in model_ids
        assert "conditional_diffusion" in model_ids
        assert "residual_diffusion" in model_ids

        # Admin can toggle model deployment status
        res = update_model_configuration(model_id="residual_unet", enabled=True, deployment_status="production", admin=admin)
        assert res["status"] == "success"
        assert res["deployment_status"] == "production"

    finally:
        db.close()

