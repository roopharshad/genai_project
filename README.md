# DocRestore AI: Legacy UI Asset Restorer

A web application for restoring, recovering and reconstructing visual assets from legacy software.

## Run

```powershell
.\run.ps1          # creates .venv on first run, then serves http://127.0.0.1:8000
```

Or run it manually:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The same server hosts the API and the frontend.
API docs: http://127.0.0.1:8000/api/docs

## Structure

```
backend/
  app.py                     FastAPI routes, static frontend hosting
  config.py                  environment configuration
  db.py                      SQLite job log (feeds Statistics page)
  services/
    gfpgan_service.py        AI Image Restoration (hosted GFPGAN Gradio Space)
    asset_service.py         asset extraction (archives, markup, screenshots)
    ui_service.py            UI reconstruction (AI or classical engine)
    image_utils.py           validation, limits, storage helpers
frontend/                    index.html, css/, js/app.js (no build step)
scripts/
  inspect_restoration_api.py prints the Space API via gradio_client view_api()
  smoke_test.py              end-to-end test against a running server
GFPGAN-master/               upstream GFPGAN source (reference, unmodified)
storage/                     uploads, results, sqlite db (git-ignored)
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | server + AI service availability |
| GET | /api/options | restoration modes, engines, limits |
| POST | /api/restore | `file`, `mode` (balanced/fidelity/detail), `scale` 1–4 |
| POST | /api/ui/reconstruct | `file`, `engine` (ai/classical), `scale` |
| POST | /api/assets/recover | `file` (image, docx/pptx/xlsx/odt/zip, html/css/svg) |
| GET | /api/assets/{job}/zip | all recovered assets as ZIP |
| GET | /api/files/{job}/{name}?download=true | original/result/asset files |
| GET | /api/stats, /api/history | real job metrics |

## Restoration integration (internal)

The Space `randomtable/Image-Restoration-GFPGAN` runs Gradio 3.1.7. `Client.view_api()` shows
one endpoint `/predict(input, version, rescaling_factor)`. Current `gradio_client` versions
cannot submit to Gradio 3's websocket queue, so the service posts to the Space's HTTP route
`/api/predict` with `fn_index=0`. Verified versions: `v1.4`, `v1.3`, `RestoreFormer`.
`CodeFormer` and `RealESR-General-x4v3` return empty results on this Space and are not offered.

The model restores faces; non-face regions are only upscaled/denoised by the background
upsampler. It does not restore UI elements semantically.

## Environment variables

See `.env.example`. All are optional: `RESTORATION_SPACE_URL`, `HF_TOKEN`,
`RESTORATION_TIMEOUT_SECONDS`, `MAX_UPLOAD_MB`, `MAX_PROCESS_SIDE`, `RETENTION_HOURS`, `STORAGE_DIR`.

## Notes

- TLS is verified with the Windows certificate store (`truststore`); the bundled Python CA
  list on this machine rejects the certificate chain.
- Run the test suite with the server running: `.\.venv\Scripts\python.exe scripts\smoke_test.py`
  (it creates real jobs, which appear in Statistics).
