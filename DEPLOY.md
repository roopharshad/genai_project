# Deploying DocRestore AI

One container serves the website and the API on port `8000` (or `$PORT`).

## Server requirements

| | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB (DocRes + PaddleOCR + LaMa run on CPU) |
| CPU | 2 cores | 4+ cores (a page takes ~40–120 s on 4 cores) |
| Disk | 8 GB (image ~5 GB incl. ~380 MB of model weights) | + space for uploads |
| GPU | not needed | |

Free hosting tiers with 512 MB–1 GB RAM (e.g. Render free, Railway trial) are too small: the server
will be killed while loading the models. Use a VM (AWS EC2 `t3.large`, Azure B2ms, Google e2-standard-2,
DigitalOcean 8 GB droplet) or a paid container plan with ≥ 4 GB RAM.

## Option A: Docker (recommended)

```bash
git clone https://github.com/roopharshad/genai_project.git
cd genai_project
cp .env.example .env            # then fill in SECRET_KEY, ADMIN_PASSWORD, GEMINI_API_KEY
docker build -t docrestore-ai .
docker run -d --name docrestore -p 80:8000 --env-file .env \
  -v docrestore-data:/app/webapp/storage --restart unless-stopped docrestore-ai
```

or simply `docker compose up -d --build`.

- The build downloads the model weights (`scripts/download_models.py`).
- `docrestore-data` keeps uploads, results and the SQLite database across restarts and updates.
- Health check: `GET /api/health` → `{"status":"ok"}`.
- Generate a secret key: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Option B: directly on a Linux VM (no Docker)

```bash
sudo apt install -y python3.10-venv libgl1 libglib2.0-0 nodejs npm
python3.10 -m venv .venv && . .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pip install --no-deps basicsr==1.4.2 facexlib==0.3.0 realesrgan==0.3.0 simple-lama-inpainting==0.1.2
pip install paddlepaddle==3.3.1 && pip install --no-deps paddleocr==3.7.0 paddlex==3.7.2
pip install aiohttp aistudio-sdk chardet colorlog modelscope pandas prettytable imagesize pyclipper shapely pypdfium2 python-bidi ruamel.yaml ujson
pip install --force-reinstall --no-deps "opencv-python-headless<5" numpy==2.2.6
python scripts/download_models.py
(cd webapp/frontend && npm ci && npx vite build)
cd webapp/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run it as a service (systemd) and put Nginx or Caddy in front for HTTPS.

## Environment variables

See `.env.example`. Required in production: `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
`GEMINI_API_KEY` enables the document chat. The enhancement step stays off (`ENHANCEMENT_ENABLED=0`).

## Before going live

- Change the administrator password (`ADMIN_PASSWORD` is used only when the account is first created).
- Serve over HTTPS (Caddy does this automatically; with Nginx use Let's Encrypt).
- Back up the `docrestore-data` volume (it contains the database and all documents).
- One restoration runs at a time; further jobs queue. Jobs running during a restart are marked failed.
