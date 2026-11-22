import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1.api_router import api_router
from app.models.entities import (User, Workspace, WorkspaceMember, Project, Asset, AssetVersion,
                                 Experiment, RestorationJob)
from app.core.security import get_password_hash
from app.api.v1.endpoints.analytics import ensure_experiments_seeded
from PIL import Image, ImageDraw

def init_db_and_seed():
    """Create tables and seed initial demo user, workspace, and experiments."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Jobs cannot survive a process restart because workers are in-memory threads.
        db.query(RestorationJob).filter(RestorationJob.status.in_(("queued", "validating", "processing", "evaluating"))).update(
            {"status": "failed", "stage": "Interrupted by server restart",
             "error_message": "Please start this restoration again."}, synchronize_session=False)
        db.commit()

        # 1. Seed demo user
        user = db.query(User).filter(User.email == "demo@docrestore.ai").first()
        if not user:
            user = User(
                email="demo@docrestore.ai",
                hashed_password=get_password_hash("docrestore123"),
                full_name="Dr. Alex Vance",
                role="administrator",
                is_active=True,
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Seed workspace
        ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
        if not ws:
            ws = Workspace(
                name="Legacy OS & Enterprise Archives",
                slug="legacy-os-enterprise",
                description="Primary workspace for historical software documentation and UI asset restoration.",
                owner_id=user.id
            )
            db.add(ws)
            db.commit()
            db.refresh(ws)

            member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
            db.add(member)
            db.commit()

        # 3. Seed project
        proj = db.query(Project).filter(Project.workspace_id == ws.id).first()
        if not proj:
            proj = Project(
                workspace_id=ws.id,
                name="Windows 95 & Classic Unix Documentation",
                description="Technical user manuals and dialog box screenshots for enterprise recovery.",
                created_by=user.id
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)

        # 4. Generate and seed sample legacy UI screenshot if project has no assets
        asset_count = db.query(Asset).filter(Asset.project_id == proj.id).count()
        if asset_count == 0:
            sample_fn = "orig_legacy_win95_dialog.png"
            sample_path = settings.ORIGINALS_DIR / sample_fn
            
            # Synthesize authentic legacy UI dialog screenshot (640x480)
            img = Image.new("RGB", (640, 480), color=(192, 192, 192))
            draw = ImageDraw.Draw(img)

            # Window frame & title bar
            draw.rectangle([10, 10, 630, 470], outline=(0, 0, 0), width=2)
            draw.rectangle([14, 14, 626, 466], fill=(192, 192, 192))
            draw.rectangle([14, 14, 626, 42], fill=(0, 0, 128))
            draw.text((24, 20), "DocRestore AI — Legacy Database Connection Manager (Build 4.10)", fill=(255, 255, 255))

            # Menu bar
            draw.rectangle([14, 44, 626, 68], fill=(212, 208, 200))
            draw.text((24, 49), "File    Edit    View    Options    Tools    Help", fill=(0, 0, 0))

            # UI Component Group Box
            draw.rectangle([30, 80, 610, 390], outline=(128, 128, 128), width=1)
            draw.text((45, 73), " Connection Parameters ", fill=(0, 0, 0))

            draw.text((50, 110), "Primary Server Hostname:", fill=(0, 0, 0))
            draw.rectangle([230, 105, 580, 130], fill=(255, 255, 255), outline=(128, 128, 128))
            draw.text((238, 110), "srv-alpha01.internal.corp.net:5432", fill=(0, 0, 0))

            draw.text((50, 150), "Target Schema Namespace:", fill=(0, 0, 0))
            draw.rectangle([230, 145, 580, 170], fill=(255, 255, 255), outline=(128, 128, 128))
            draw.text((238, 150), "SYS_DOCS_ARCHIVE_1998", fill=(0, 0, 0))

            # Status Box
            draw.rectangle([50, 240, 580, 360], fill=(255, 255, 255), outline=(128, 128, 128))
            draw.text((60, 250), "[OK] Database interface driver loaded: libpq.dll v7.4", fill=(0, 128, 0))
            draw.text((60, 275), "[INFO] 14 table entities verified in schema.", fill=(0, 0, 128))
            draw.text((60, 300), "[READY] Ready for screenshot restoration and OCR preservation.", fill=(100, 40, 200))

            # Buttons
            draw.rectangle([340, 410, 440, 445], fill=(212, 208, 200), outline=(0, 0, 0))
            draw.text((362, 422), "Execute", fill=(0, 0, 0))
            draw.rectangle([460, 410, 530, 445], fill=(212, 208, 200), outline=(0, 0, 0))
            draw.text((485, 422), "OK", fill=(0, 0, 0))
            draw.rectangle([545, 410, 615, 445], fill=(212, 208, 200), outline=(0, 0, 0))
            draw.text((560, 422), "Cancel", fill=(0, 0, 0))

            img.save(sample_path, format="PNG")
            
            from app.storage.file_storage import FileStorageService
            FileStorageService.generate_thumbnail(sample_path, sample_fn)

            asset = Asset(
                project_id=proj.id,
                original_filename="legacy_win95_dialog.png",
                stored_filename=sample_fn,
                file_size=sample_path.stat().st_size,
                mime_type="image/png",
                width=640,
                height=480,
                resolution_category="standard",
                status="active",
                degradation_analysis={
                    "blur_metric_laplacian_var": 94.2,
                    "noise_standard_deviation": 11.4,
                    "edge_density_ratio": 0.084,
                    "detected_degradations": {
                        "blur_detected": True,
                        "noise_detected": True,
                        "compression_artifacts": True,
                        "heavily_degraded": False
                    },
                    "recommended_model": "residual_unet"
                }
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

            v1 = AssetVersion(
                asset_id=asset.id,
                version_number=1,
                version_type="original",
                stored_filename=sample_fn,
                file_size=asset.file_size,
                width=640,
                height=480,
                config_summary={"note": "Original baseline screenshot sample"}
            )
            db.add(v1)
            db.commit()

        # 5. Seed Experiments E1-E8
        ensure_experiments_seeded(db)

    finally:
        db.close()

# Run seed once during module load
init_db_and_seed()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DocRestore AI: Advanced AI-powered restoration platform for legacy software UI screenshots.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Storage folders for static delivery
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_PATH)), name="storage")

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve the built React UI (webapp/frontend/dist) with client-side routing fallback.
from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith(("api/", "storage/", "docs", "redoc", "openapi.json")):
        raise HTTPException(status_code=404)
    target = (FRONTEND_DIST / full_path).resolve()
    if full_path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
        return FileResponse(target)
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        return {"app": "DocRestore AI", "status": "online", "note": "Frontend not built. Run: npm run build in webapp/frontend"}
    return FileResponse(index)
