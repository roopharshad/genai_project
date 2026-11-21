# Document restoration with text preservation

## Pipeline (`backend/services/document_pipeline.py`)

| Stage | File saved in `webapp/storage/stages/<run>/` | What it does |
|---|---|---|
| 0 | `0_original.png` | Upload as received (the asset original in `storage/originals/` is never modified) |
| 1 | `1_preprocessed.png` | Page cropped off its background, if a page border is found |
| 2 | `2_docres.png` | DocRes deshadowing + appearance (`docres_service.py`, unchanged) |
| 2b | `2b_docdiff.png` | Optional DocDiff deblurring (`DOCDIFF_REFINE=1`, off by default) |
| 3 | `3_text_refined.png` | Strokes DocRes erased are put back from the original; dust on letters removed |
| 4 | `4_ocr_guarded.png` | Lines that read worse than the original are re-rendered from the original's strokes |
| 5 | `5_final.png` | Stage 2, 3 or 4, whichever PaddleOCR reads most like the original |
| | `report.json` | OCR text per stage, agreement, confidence, missing/changed spans |

The job's `config_summary.operational` (returned by `/api/v1/comparisons/{asset}`) contains
`steps`, `stages_url` and the full `text_report`.

Guarantees:
- **No resizing:** documents are processed at full resolution (`_fit` applies only to photos), and the run fails if the final size differs from the input page.
- **No invented text:** OCR never draws anything. It only measures, and chooses between pixels that exist in the original or the DocRes output.
- **Only finished results count:** a job is marked completed only after the final PNG is saved, as before.

## Measured results (PaddleOCR PP-OCRv5 mobile, CPU)

`samples/faded_document.jpg`, ground truth `samples/gt/faded_document.txt`:

| Stage | CER | WER |
|---|---|---|
| Original | 0.0087 | 0.0962 |
| DocRes | 0.0145 | 0.1154 |
| DocRes + text refinement (final) | **0.0029** | **0.0385** |

`samples/old_book_page.jpg` (no ground truth; agreement with the original's OCR reading):
DocRes 0.9563, refinement 0.9495, guard 0.9550. The pipeline therefore kept the DocRes output.
Refinement does not help on every page, and the selection step stops it from making a page worse.

DocDiff on the DocRes output (faded document): CER 0.0203 → 0.0203, WER 0.1538 → 0.1346, and
311 s per page on CPU. It makes strokes darker, but it did not change the number of character
errors, so it is off by default.

## DocDiff assessment

- Official weights: `checksave/init.pth` + `denoiser.pth`. These are the deblurring task only, trained on synthetic blurred text crops (Hradiš et al. 2015). The seal-removal weights do not apply here.
- Compatible: yes. It takes any RGB page in 128 px tiles at native resolution.
- One edit to the official code: `model/DocDiff.py` used `torch.tensor([0]).cuda()` as a default argument, which crashes at import on CPU-only machines. That default is never used.
- Trade-off: it costs about 5 minutes per page on CPU for no measured gain on these samples. It is likely to help genuinely blurred scans. Enable it with `DOCDIFF_REFINE=1`.

## Installation

- DocRes weights: `DocRes-master/checkpoints/docres.pkl` and `DocRes-master/data/MBD/checkpoint/mbd.pkl` (from the official Space `qubvel-hf/documents-restoration`).
- DocDiff weights: `DocDiff-main/checksave/{init,denoiser}.pth` (from github.com/Royalvice/DocDiff).
- PaddleOCR: see `requirements.txt`. Models (about 20 MB) download once to `~/.paddlex/official_models`.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `DOCRES_MAX_SIZE` | 768 | DocRes network size. Use 1600 on a GPU. |
| `DOCRES_DEWARP` | 0 | 1 = run DocRes dewarping (for curled pages only) |
| `DOCDIFF_REFINE` | 0 | 1 = add DocDiff deblurring after DocRes |
| `OCR_DEVICE` | cpu | e.g. `gpu:0` with a Paddle GPU build |
| `OCR_MKLDNN` | 0 | oneDNN kernels. They fail with Paddle 3.3 on these models. |
| `OCR_TIMEOUT_SECONDS` | 300 | OCR worker timeout |
| `OCR_IN_PROCESS` | 0 | 1 = run OCR in the server process (debug only, see below) |

## Known issues

- **OCR runs in its own process.** PyTorch and Paddle both load MKL/OpenMP DLLs, and loading both into one Windows process crashed the server with no Python error. PaddleOCR therefore runs in a worker process that is restarted automatically if it dies.
- **OpenCV check workaround.** PaddleX checks for the `opencv-contrib-python` package by name. The project uses `opencv-python-headless` 4.14, and installing a second cv2 build would conflict with it. `ocr_service.py` reports the installed cv2 to that check instead.
- **The OCR reading of the original is not ground truth.** The reported agreement is consistency with that reading. Use `scripts/stage_report.py RUN_DIR gt.txt` for real CER/WER.
