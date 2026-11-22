# DocRestore AI: one container serving the API and the built React UI on $PORT (default 8000).
# Build:  docker build -t docrestore-ai .
# Run:    docker run -p 8000:8000 -v docrestore-data:/app/webapp/storage --env-file .env docrestore-ai

# ---- 1. frontend build ----------------------------------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /src
COPY webapp/frontend/package.json webapp/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY webapp/frontend/ ./
RUN npx vite build

# ---- 2. runtime -----------------------------------------------------------------------------
FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True PORT=8000
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# CPU PyTorch first (the default index would pull the multi-GB CUDA build)
# The base image's old pip rejects the PyTorch index's typing_extensions wheel ("inconsistent
# Name"), so upgrade pip first and take torch's other dependencies from PyPI.
RUN pip install --upgrade pip setuptools wheel \
    && pip install torch==2.14.1 torchvision==0.29.2 \
        --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
COPY requirements.txt .
RUN pip install -r requirements.txt
# Packages installed without dependencies so they cannot replace the pinned OpenCV/NumPy/torch
RUN pip install --no-deps simple-lama-inpainting==0.1.2 \
    && pip install paddlepaddle==3.3.1 \
    && pip install --no-deps paddleocr==3.7.0 paddlex==3.7.2 \
    && pip install aiohttp aistudio-sdk chardet colorlog modelscope pandas prettytable imagesize \
                   pyclipper shapely pypdfium2 python-bidi ruamel.yaml ujson \
    && pip install --force-reinstall --no-deps "opencv-python-headless<5" "numpy==2.2.6"

COPY . .
COPY --from=frontend /src/dist ./webapp/frontend/dist
# Pretrained weights for document restoration (DocRes + LaMa). Add --all for the photo models.
RUN python scripts/download_models.py

WORKDIR /app/webapp/backend
VOLUME ["/app/webapp/storage"]
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
