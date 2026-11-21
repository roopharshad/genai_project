# DocRestore AI

Restores old photos and historical documents. React/Tailwind frontend, FastAPI backend, local models on CPU.

## Run

```powershell
.\run.ps1          # creates .venv on first run, then serves http://127.0.0.1:8000
```

Or manually:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # see install notes inside
cd webapp\backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Demo login: `demo@docrestore.ai` / `docrestore123`. Rebuild the frontend after UI changes with
`npx vite build` in `webapp/frontend` (the backend serves `frontend/dist`).

## Structure

```
webapp/
  backend/app/               FastAPI app (API, auth, jobs, SQLite at webapp/storage/docrestore.db)
    ml_engine/inference/registry.py   routes photos and documents to the models below
  frontend/                  React + Tailwind UI (Vite)
  storage/                   uploads, results, stage images (runtime data)
backend/
  config.py                  environment configuration
  services/
    local_gfpgan_service.py  photo restoration (GFPGAN v1.4, local)
    gfpgan_service.py        hosted fallback (RESTORATION_ENGINE=hosted)
    enhance_service.py       mark removal, colourization, document detection
    document_pipeline.py     DocRes -> text refinement -> OCR-verified stage selection
    docres_service.py        DocRes (deshadowing + appearance)
    text_refine_service.py   stroke recovery and line guard
    ocr_service.py           PaddleOCR verification, CER/WER
    paper_restore_service.py stain/fold/texture normalisation that protects ink (in progress)
GFPGAN-master/               GFPGAN inference code + weights
DocRes-master/               DocRes inference code + weights
models/colorization/         colourization model
samples/                     test inputs (faded_document, old_book_page, damaged_bw_photo, docs/)
scripts/                     web_doc_test.py, stage_report.py, text_eval.py, paper_test.py
docs/TEXT_PRESERVATION.md    document pipeline details and measurements
```

## Environment variables

See `.env.example` and `docs/TEXT_PRESERVATION.md`.
