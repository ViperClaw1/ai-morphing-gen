# AI Morphing Generator MVP — GPU Worker
# Target: Ubuntu 22.04 + CUDA 12.1 + PyTorch 2.3.1 (cu121)

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/models \
    MODEL_CACHE_DIR=/app/models \
    LOCAL_FILES_ONLY=true \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip \
    && pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121 \
    && pip install -r /app/requirements.txt

COPY app /app/app
COPY .env.example /app/.env.example

# Pre-download Stable Diffusion 1.5 during image build (not at runtime).
# fp16-variant weights only (model_loader.py loads with variant="fp16") — the full repo
# is ~10GB+ across redundant fp32 weights, .ckpt monoliths, and the unused safety checker
# (safety_checker=None in model_loader.py); this filter cuts it to the ~2GB actually used,
# which also means a dropped connection costs minutes to retry, not hours.
RUN mkdir -p /app/models \
    && python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download(\
    'runwayml/stable-diffusion-v1-5',\
    cache_dir='/app/models',\
    local_files_only=False,\
    allow_patterns=[\
        'model_index.json',\
        'scheduler/*.json',\
        'tokenizer/*',\
        'text_encoder/*.json',\
        'text_encoder/*.fp16.safetensors',\
        'vae/*.json',\
        'vae/*.fp16.safetensors',\
        'unet/*.json',\
        'unet/*.fp16.safetensors',\
        'feature_extractor/*.json',\
    ],\
)"

# Pre-download IP-Adapter FaceID weights (identity conditioning, see
# app/core/model_loader.py) and the insightface buffalo_l face-embedding model,
# same reasoning as the SD1.5 block above: fetch once at build time, run with
# LOCAL_FILES_ONLY=true at request time.
RUN python -c "\
from huggingface_hub import hf_hub_download; \
hf_hub_download(\
    'h94/IP-Adapter-FaceID',\
    'ip-adapter-faceid_sd15.bin',\
    cache_dir='/app/models',\
)"

RUN mkdir -p /app/models/insightface \
    && python -c "\
from insightface.app import FaceAnalysis; \
app = FaceAnalysis(name='buffalo_l', root='/app/models/insightface'); \
app.prepare(ctx_id=-1)"

RUN groupadd --gid 1000 worker \
    && useradd --uid 1000 --gid worker --create-home worker \
    && chown -R worker:worker /app

USER worker

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
