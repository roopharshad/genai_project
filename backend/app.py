"""DocRestore AI backend: REST API + static frontend.

Run:  .venv\\Scripts\\python.exe -m uvicorn backend.app:app --port 8000
"""
import io
import logging
import time
import zipfile

import truststore

truststore.inject_into_ssl()  # verify TLS with the OS certificate store

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from . import config, db  # noqa: E402
from .services import asset_service, gfpgan_service, ui_service  # noqa: E402
from .services.image_utils import (  # noqa: E402
    ValidationError, cleanup_old_jobs, describe, fit_for_processing, load_image, new_job_dir, to_rgb,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("docrestore")

app = FastAPI(title="DocRestore AI", docs_url="/api/docs", redoc_url=None)


@app.on_event("startup")
def _startup():
    db.init()
    log.info("removed %d expired job folders", cleanup_old_jobs())


@app.exception_handler(ValidationError)
def _validation(_, exc: ValidationError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


@app.exception_handler(gfpgan_service.RestorationError)
def _restoration(_, exc: gfpgan_service.RestorationError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


def _file_url(job_id: str, name: str) -> str:
    return f"/api/files/{job_id}/{name}"


def _read(upload: UploadFile) -> bytes:
    data = upload.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValidationError(f"File is larger than the {config.MAX_UPLOAD_MB} MB limit.", 413)
    return data


# ---------------------------------------------------------------- info
@app.get("/api/health")
def health():
    return {"status": "ok", "ai_service": gfpgan_service.health()}


@app.get("/api/options")
def options():
    return {
        "restoration_modes": [
            {"id": k, "label": v[1], "description": v[2]} for k, v in gfpgan_service.MODES.items()
        ],
        "default_mode": gfpgan_service.DEFAULT_MODE,
        "ui_engines": [{"id": k, "label": v} for k, v in ui_service.ENGINES.items()],
        "max_upload_mb": config.MAX_UPLOAD_MB,
        "max_process_side": config.MAX_PROCESS_SIDE,
    }


# ---------------------------------------------------------------- processing
def _process_image(kind: str, file: UploadFile, run):
    data = _read(file)
    img, ext = load_image(data)
    job_id, job_dir = new_job_dir()
    original_name = f"original.{ext}"
    (job_dir / original_name).write_bytes(data)  # preserve the upload untouched
    work, resized = fit_for_processing(to_rgb(img))
    started = time.time()
    try:
        result = run(work)
    except Exception as exc:
        db.record(job_id, kind, "failed", file.filename, time.time() - started, error=str(exc))
        raise
    duration = round(time.time() - started, 1)
    result.save(job_dir / "result.png", "PNG")
    db.record(job_id, kind, "success", file.filename, duration, meta={"resized": resized})
    return {
        "job_id": job_id,
        "filename": file.filename,
        "duration": duration,
        "resized_for_processing": resized,
        "processed_size": {"width": work.width, "height": work.height},
        "original": {"url": _file_url(job_id, original_name), **describe(job_dir / original_name)},
        "result": {"url": _file_url(job_id, "result.png"), **describe(job_dir / "result.png")},
    }


@app.post("/api/restore")
def restore(file: UploadFile = File(...), mode: str = Form(gfpgan_service.DEFAULT_MODE), scale: float = Form(2)):
    return _process_image("restoration", file, lambda im: gfpgan_service.restore(im, mode, scale))


@app.post("/api/ui/reconstruct")
def reconstruct(file: UploadFile = File(...), engine: str = Form("ai"), scale: float = Form(2)):
    out = _process_image("ui_reconstruction", file, lambda im: ui_service.reconstruct(im, engine, scale))
    out["engine"] = ui_service.ENGINES.get(engine, engine)
    return out


@app.post("/api/assets/recover")
def recover(file: UploadFile = File(...)):
    data = _read(file)
    job_id, job_dir = new_job_dir()
    started = time.time()
    try:
        method, assets = asset_service.recover(data, file.filename, job_dir)
    except Exception as exc:
        db.record(job_id, "asset_recovery", "failed", file.filename, error=str(exc))
        raise
    duration = round(time.time() - started, 2)
    db.record(job_id, "asset_recovery", "success", file.filename, duration, len(assets), meta={"method": method})
    for a in assets:
        a["url"] = _file_url(job_id, a["name"])
    return {"job_id": job_id, "filename": file.filename, "method": method, "duration": duration,
            "assets": assets, "zip_url": f"/api/assets/{job_id}/zip" if assets else None}


@app.get("/api/assets/{job_id}/zip")
def assets_zip(job_id: str):
    job_dir = _job_dir(job_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(job_dir.glob("asset_*.png")):
            zf.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="assets_{job_id}.zip"'})


# ---------------------------------------------------------------- files & stats
def _job_dir(job_id: str):
    path = (config.JOBS_DIR / job_id).resolve()
    if path.parent != config.JOBS_DIR.resolve() or not path.is_dir():
        raise HTTPException(404, "Not found")
    return path


@app.get("/api/files/{job_id}/{name}")
def get_file(job_id: str, name: str, download: bool = False):
    job_dir = _job_dir(job_id)
    path = (job_dir / name).resolve()
    if path.parent != job_dir or not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, filename=f"docrestore_{job_id}_{name}" if download else None)


@app.get("/api/stats")
def stats():
    return db.stats()


@app.get("/api/history")
def history(limit: int = 50):
    return db.history(min(max(limit, 1), 200))


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
