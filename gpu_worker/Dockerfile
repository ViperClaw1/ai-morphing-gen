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

# Pre-download Stable Diffusion 1.5 during image build (not at runtime)
RUN mkdir -p /app/models \
    && python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download(\
    'runwayml/stable-diffusion-v1-5',\
    cache_dir='/app/models',\
    local_files_only=False,\
)"

RUN groupadd --gid 1000 worker \
    && useradd --uid 1000 --gid worker --create-home worker \
    && chown -R worker:worker /app

USER worker

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
