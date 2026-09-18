# AI Morphing Generator MVP — GPU Worker

Standalone GPU inference service for **Stable Diffusion 1.5 img2img frame repair** only.

This worker receives pre-generated morph frames, repairs artifacts with low-strength img2img, and returns deterministic PNG output. It does **not** implement auth, billing, queues, databases, or video assembly.

---

## Requirements

| Component | Version / note |
|-----------|----------------|
| OS | **Ubuntu 22.04** (Linux only) |
| Python | **3.10** |
| NVIDIA driver | Compatible with **CUDA 12.1** |
| PyTorch | **2.4.0+cu121** |
| Diffusers | **0.30.0** |
| Tested CUDA | **12.1** (cu121 wheels) |

### VRAM recommendations

| Resolution | VRAM |
|------------|------|
| 512×512 | ~6 GB minimum |
| 768×768 | ~8 GB |
| 1024×1024 | **12 GB+** recommended |
| Higher resolutions | Scale VRAM accordingly; no hard cap is enforced |

### Tested GPU models (reference)

- NVIDIA RTX 3060 12GB  
- NVIDIA RTX 3090 24GB  
- NVIDIA A10 24GB  

Use **float16**, **xFormers** (when available), and **max 1 concurrent inference** for stable long-running operation.

---

## Project layout

```
gpu_worker/
├── app/
│   ├── api/routes/inference.py   # POST /repair, GET /health/live
│   ├── core/                     # config, logging, model loader, concurrency
│   ├── services/                 # repair pipeline, I/O, resize, cleanup, timeout
│   ├── schemas/                  # request/response models
│   ├── utils/                    # validation, CUDA, timing
│   └── main.py
├── tests/
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt          # CPU-only, no-xformers — local test env, no GPU needed
├── .env.example
└── README.md
```

---

## Local testing without a GPU

`assert_cuda_available()` (`app/utils/cuda_utils.py`) makes the app refuse to boot
without a real CUDA device — that's intentional (see `CLAUDE.md`: no CPU inference
fallback), not a bug. It means you **cannot** run `uvicorn app.main:app` directly on a
machine with no NVIDIA GPU.

What you *can* do without a GPU, and should do before ever touching RunPod: exercise
every response branch of `POST /repair` — success shape, validation errors (bad MIME,
oversized image, invalid params), timeout, CUDA OOM, model-not-loaded, unexpected
failure — against the real FastAPI route, with CUDA checks and model loading stubbed
out and only the GPU call itself mocked. That's what `tests/test_repair_route.py` does,
per `.claude/rules/testing.md`'s "GPU worker calls must be mocked in unit tests" rule.
`tests/test_image_validation.py` covers the pure validation logic the same way.

### 1. Create a CPU-only venv

```bash
cd gpu_worker
python3.10 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
```

No model download, no `.env` setup, no Docker, no GPU driver needed for this path.

### 2. Run the test suite

```bash
pytest -v
```

This runs both the no-GPU validation tests and the mocked `/repair` contract tests.
Nothing here loads the real SD1.5 pipeline or touches CUDA — `ModelLoader.load()` and
`assert_cuda_available()` are monkeypatched to no-ops in `tests/test_repair_route.py`'s
`client` fixture, and the GPU call itself (`run_repair`/`run_with_timeout`) is
monkeypatched per test to return canned results or raise the specific error being
tested.

### 3. What this does *not* cover

Real model quality, real VRAM/OOM limits, and actual cold-start/inference latency
(still an open item in `docs/implementation_plan.md`'s risk table) all require a real
CUDA GPU — either a rented box or the eventual RunPod endpoint. Use the "Local launch"
section below once you have GPU access, or point a real `.env` at a RunPod sandbox
endpoint per `CLAUDE.local.md`.

---

## Local launch (Ubuntu 22.04 + GPU)

### 1. Install system deps

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip libgl1 libglib2.0-0
```

### 2. Create venv and install Python packages

```bash
cd gpu_worker
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 3. Download model (first run only)

```bash
export HF_HOME=./models
export LOCAL_FILES_ONLY=false
python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'runwayml/stable-diffusion-v1-5',
    cache_dir='./models',
    allow_patterns=[
        'model_index.json', 'scheduler/*.json', 'tokenizer/*',
        'text_encoder/*.json', 'text_encoder/*.fp16.safetensors',
        'vae/*.json', 'vae/*.fp16.safetensors',
        'unet/*.json', 'unet/*.fp16.safetensors',
        'feature_extractor/*.json',
    ],
)
"
```

fp16-variant weights only (~2GB) — the full repo is 10GB+ of redundant fp32 weights, `.ckpt` monoliths, and an unused safety-checker model. `model_loader.py` loads with `variant="fp16"`, so nothing else is ever read.

### 4. Configure environment

```bash
cp .env.example .env
# Set MODEL_CACHE_DIR and HF_HOME to ./models
# Set LOCAL_FILES_ONLY=true after download
```

### 5. Run server

```bash
export HF_HOME=./models
export MODEL_CACHE_DIR=./models
export LOCAL_FILES_ONLY=true
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Model loads **once** at startup. CPU inference is **not** supported.

---

## Docker launch

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```bash
cd gpu_worker
docker build -t ai-morphing-gpu-worker .
docker run --gpus all -p 8000:8000 --env-file .env.example ai-morphing-gpu-worker
```

The image pre-downloads `runwayml/stable-diffusion-v1-5` at **build** time. Runtime uses `local_files_only=true`.

Health check:

```bash
curl http://localhost:8000/health/live
```

Expected:

```json
{"success": true}
```

---

## API

### `POST /repair`

Multipart form fields:

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `image` | file | yes | — |
| `prompt` | string | yes | — |
| `seed` | int | yes | — |
| `negative_prompt` | string | no | built-in default |
| `strength` | float | no | `0.2` |
| `guidance_scale` | float | no | `5` |
| `num_inference_steps` | int | no | `25` |

Accepted image MIME types: `image/jpeg`, `image/png`, `image/webp`.  
Max upload: **10 MB**. No resolution cap — image is only resized to be divisible by 8 before inference.

### Example curl

```bash
curl -X POST "http://localhost:8000/repair" \
  -H "X-Request-Id: demo-001" \
  -F "image=@test_photos/photo1.jpg" \
  -F "prompt=high quality portrait, natural skin, preserve identity and pose, same composition" \
  -F "negative_prompt=blurry, distorted face, deformed, wrong identity" \
  -F "seed=42" \
  -F "strength=0.2" \
  -F "guidance_scale=5" \
  -F "num_inference_steps=25"
```

To save the result straight to a file instead of eyeballing base64, pipe the response through Python:

```bash
curl -s -X POST "http://localhost:8000/repair" \
  -H "X-Request-Id: demo-001" \
  -F "image=@test_photos/photo1.jpg" \
  -F "prompt=high quality portrait, natural skin, preserve identity and pose, same composition" \
  -F "negative_prompt=blurry, distorted face, deformed, wrong identity" \
  -F "seed=42" \
  -F "strength=0.2" \
  -F "guidance_scale=5" \
  -F "num_inference_steps=25" \
  | python -c "import sys,json,base64; d=json.load(sys.stdin); open('out.png','wb').write(base64.b64decode(d['data']['image_base64']))"
```

### Morph type variations

`scripts/generate_morph_variations.sh` drives `/repair` once per morph type against a
running server and saves each result as `out_<morph_type>.png`. Prompts and strengths
per morph type are declared as constants (`PROMPTS`, `STRENGTHS`) at the top of the
script — add a new type there and it's automatically picked up.

```bash
# All morph types, against test_photos/photo1.jpg, output in the current dir
./scripts/generate_morph_variations.sh

# Specific image / output dir / subset of morph types
./scripts/generate_morph_variations.sh test_photos/photo2.jpg out beard smile
```

Currently defined: `aging`, `angle`, `beard`, `hairstyle`, `smile`.

Success response:

```json
{
  "success": true,
  "data": {
    "image_base64": "...",
    "seed": 42,
    "duration_ms": 1234,
    "mime_type": "image/png"
  }
}
```

Error response (no stack traces):

```json
{
  "success": false,
  "error": {
    "code": "CUDA_OOM",
    "message": "GPU ran out of memory. Reduce resolution or retry later."
  }
}
```

---

## Expected GPU behavior

1. **Startup**: CUDA check → load SD 1.5 img2img once (fp16, safety checker disabled) → ready.  
2. **Per request**: validate image → resize to multiples of 8 → single GPU job (semaphore) → deterministic `torch.Generator(seed)` → PNG base64 → VRAM cleanup (`gc` + `empty_cache`).  
3. **Concurrency**: default **1** inference at a time.  
4. **Timeout**: default **120 s** per request.  
5. **Long runs**: model stays loaded; cache cleared after each inference.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| `CUDA is required` on start | No GPU / driver | Install NVIDIA driver; run with `--gpus all` in Docker |
| `MODEL_LOAD_FAILURE` | Model not in cache | Rebuild image or run snapshot_download with `LOCAL_FILES_ONLY=false` |
| `CUDA_OOM` | Resolution too high for available VRAM | Use smaller input; ensure 12GB+ for 1024² |
| `INFERENCE_TIMEOUT` | Slow GPU or high steps | Lower `num_inference_steps` or increase `INFERENCE_TIMEOUT_SECONDS` |
| `CORRUPTED_FILE` | Invalid bytes | Re-export frame as PNG/JPEG |
| xFormers warning | Wheel mismatch | Service still runs; fix torch/xformers versions per requirements |

### Run tests (no GPU required)

See "Local testing without a GPU" above for the full no-GPU setup
(`requirements-dev.txt` + `pytest -v`).

---

## Recommended server specs

- **CPU**: 4+ vCPU  
- **RAM**: 16 GB system RAM  
- **GPU**: 12 GB+ VRAM for 1024² repair at batch size 1  
- **Disk**: ~8 GB for model cache + Docker layers  
- **OS**: Ubuntu 22.04 LTS  

---

## Environment variables

See `.env.example` for all settings. Key variables:

- `MODEL_ID` — `runwayml/stable-diffusion-v1-5`  
- `HF_HOME` / `MODEL_CACHE_DIR` — Hugging Face cache path  
- `LOCAL_FILES_ONLY` — `true` in production (after model download)  
- `MAX_CONCURRENT_INFERENCE` — default `1`  
- `INFERENCE_TIMEOUT_SECONDS` — default `120`  

---

## License / usage note

This service is intended for deployment on rented GPU servers as an isolated repair stage in the morphing pipeline. It must not be exposed publicly without upstream authentication and rate limiting.
