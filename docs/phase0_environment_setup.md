# Phase 0 — Environment & Setup Guide

Companion to [`implementation_plan.md`](implementation_plan.md) §0. This doc turns the Pre-Development Checklist into an ordered, actionable setup path and gives the full environment-variable inventory for every service in Phase 1.

Status date: 2026-08-05.

---

## 1. Decisions Locked This Phase

| Decision | Choice | Rationale |
| --- | --- | --- |
| Landmark detection | **MediaPipe** | Apache 2.0 license (no commercial-use restriction), CPU-only, 468-point face mesh, no GPU needed for Stage 1-2 warping. |
| Identity-consistency method | **IP-Adapter FaceID** (ArcFace embeddings via InsightFace `buffalo_l`) | Supersedes the original ControlNet decision (struck through below) — reversed directly in `gpu_worker` without a documented licensing resolution. `buffalo_l` is licensed **non-commercial research only**; this is an **open, unresolved legal exposure for a paid product**, tracked in `implementation_plan.md`'s risk table, not a cleared decision. Needs a commercial license or a swap back to ControlNet before shipping paid. |
| ~~Identity-consistency method~~ | ~~**ControlNet** (canny or openpose conditioning)~~ | ~~No dependency on InsightFace's pretrained embedding models... IP-Adapter FaceID and InstantID were rejected for MVP on this basis~~ (superseded — see row above) |
| Database | **SQLite** for MVP, migrate to Postgres in Phase 2 | Already decided in plan §1.1; fastest to ship, single-file, zero ops overhead pre-launch. |
| VPS provider | **Hetzner** | Cheapest, EU-based, straightforward for a KZ-registered entity. |
| Queue | **RQ (Redis Queue)** | Simpler than Celery for a single-VPS MVP. |
| Object storage | **Cloudflare R2** | Free tier, zero egress fees — important given video output sizes. |

Still genuinely open (not blocking env-var setup, tracked separately):

| Item | Status | Next action |
| --- | --- | --- |
| Payment processor | Pending support responses | See §4 outreach checklist below |
| SD1.5 inference benchmark on RTX 3090 | Not yet run | See §5 benchmark spec below |
| Domain name | Not yet registered | Business decision, no technical blocker |

---

## 2. Step-by-Step Phase 0 Execution Order

Do these roughly in this order — each unblocks the next:

1. **Register domain** (business decision, needed for Vercel + webhook URLs later).
2. **Create Hetzner account + provision VPS** (Ubuntu 22.04, 4 vCPU / 8GB RAM minimum for backend+Redis+SQLite — this box does *not* need a GPU, the GPU worker runs separately on RunPod).
3. **Create Vercel account**, link to the (future) frontend repo — no deploy yet, just account + project shell.
4. **Create Cloudflare account → R2 bucket** (`ai-morphing-assets` or similar), generate S3-compatible API token (Account ID, Access Key ID, Secret Access Key).
5. **Install Redis** on the Hetzner VPS (or use a managed Redis add-on if budget allows) — backs the RQ job queue.
6. **Create RunPod account**, add billing, note API key — needed for the GPU worker serverless endpoint (Phase 1.2) and for the benchmark run below.
7. **Send payment processor outreach emails** (§4) — do this in parallel, it's slow (support turnaround), not code-blocking.
8. **Run the SD1.5 benchmark** on a RunPod RTX 3090 pod (§5) — de-risks all cost projections in the plan before committing to Phase 1 scope.
9. **Locally validate MediaPipe landmark extraction** on a couple of test face photos — sanity check before building the full warping pipeline.
10. **Locally validate ControlNet + SD1.5 img2img** identity preservation on a repaired frame — confirms the chosen method actually holds identity well enough before Phase 1.4 depends on it.

Steps 2, 4, 6 each produce credentials that go straight into the env var tables below.

---

## 3. Environment Variable Inventory

These are reference tables for the `.env` files each service will need. The `gpu_worker/` service already exists and has its own `.env.example` (see [`gpu_worker/README.md`](../gpu_worker/README.md) §Environment variables) — the ControlNet additions below are **new**, needed once Phase 1.2 implements the identity-consistency pipeline; they are not yet in that file.

### 3.1 Backend API (FastAPI + RQ) — `backend/.env` (service not yet scaffolded — Phase 1.1)

| Variable | Example | Notes |
| --- | --- | --- |
| `ENV` | `development` \| `production` | |
| `SQLITE_PATH` | `./data/app.db` | Becomes `POSTGRES_URL` in Phase 2 |
| `REDIS_URL` | `redis://localhost:6379/0` | RQ broker |
| `RUNPOD_API_KEY` | — | From RunPod account settings |
| `RUNPOD_ENDPOINT_ID` | — | Set once the GPU worker serverless endpoint is provisioned (1.2) |
| `STORAGE_PROVIDER` | `r2` | |
| `R2_ACCOUNT_ID` | — | Cloudflare dashboard |
| `R2_ACCESS_KEY_ID` | — | R2 API token |
| `R2_SECRET_ACCESS_KEY` | — | R2 API token |
| `R2_BUCKET_NAME` | `ai-morphing-assets` | |
| `R2_ENDPOINT` | `https://<account_id>.r2.cloudflarestorage.com` | |
| `STORAGE_PATH` | `./storage` | Local dev fallback only |
| `PREVIEW_ENABLED` | `true` | Admin-togglable in Phase 2 |
| `PREVIEW_TTL_HOURS` | `3` | |
| `PREVIEW_LIMIT_PER_PROJECT` | `3` | |
| `JWT_SECRET` / `SESSION_SECRET` | — | Generate with `openssl rand -hex 32` |
| `CORS_ALLOWED_ORIGINS` | `https://<frontend-domain>` | |
| `PAYMENT_PROVIDER` | `payoneer` \| `stripe` \| `tiptop` | **TBD — set once §4 outreach resolves** |
| `PAYONEER_API_KEY` / `PAYONEER_WEBHOOK_SECRET` | — | Only if Payoneer selected |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | — | Only if Stripe selected (needs future US LLC) |
| `TIPTOP_API_KEY` / `TIPTOP_WEBHOOK_SECRET` | — | Only if TipTop Pay selected |
| `SENTRY_DSN` | — | Error tracking, no Prometheus yet |
| `LOG_LEVEL` | `INFO` | |
| `RATE_LIMIT_UPLOAD_PER_MIN` | `5` | |
| `RATE_LIMIT_RENDER_PER_MIN` | `2` | |
| `NSFW_CHECK_PROVIDER` / `NSFW_CHECK_API_KEY` | — | Pre-inference gate, provider TBD |

### 3.2 GPU Worker — `gpu_worker/.env` (existing service — additions for Phase 1.2)

Existing vars (already in `gpu_worker/.env.example`): `MODEL_ID`, `MODEL_CACHE_DIR`, `HF_HOME`, `DEFAULT_STRENGTH`, `DEFAULT_GUIDANCE_SCALE`, `DEFAULT_NUM_INFERENCE_STEPS`, `DEFAULT_NEGATIVE_PROMPT`, `MAX_UPLOAD_BYTES`, `MAX_INFERENCE_DIMENSION`, `RESIZE_DIVISOR`, `MAX_CONCURRENT_INFERENCE`, `INFERENCE_TIMEOUT_SECONDS`, `DEVICE`, `DTYPE`, `ENABLE_XFORMERS`, `LOCAL_FILES_ONLY`.

New, to add when the ControlNet pipeline is implemented (Phase 1.2):

| Variable | Example | Notes |
| --- | --- | --- |
| `CONTROLNET_MODEL_ID` | `lllyasviel/sd-controlnet-canny` (or `-openpose`) | Pick based on which conditioning gives better identity lock in the local validation (step 10) |
| `CONTROLNET_CONDITIONING_SCALE` | `0.6` | Tune during validation |
| `LANDMARK_LIB` | `mediapipe` | Informational; MediaPipe ships as a pip package, no separate model download/cache path needed |

### 3.3 Frontend (Next.js on Vercel) — `frontend/.env.local` (service not yet scaffolded — Phase 1.3)

| Variable | Example | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `https://api.<domain>` | Backend base URL |
| `NEXT_PUBLIC_R2_PUBLIC_URL` | — | CDN base for serving previews, if R2 public bucket access is used |
| `NEXT_PUBLIC_SENTRY_DSN` | — | Client-side error tracking |
| `NEXT_PUBLIC_PAYMENT_PROVIDER` | mirrors backend `PAYMENT_PROVIDER` | Drives checkout button behavior |

### 3.4 Infra / Deploy-level Secrets (CI or host-level, not app `.env` files)

| Variable | Purpose |
| --- | --- |
| `HETZNER_API_TOKEN` | If provisioning the VPS via API/Terraform rather than manually |
| VPS SSH key | Deploy access to the Hetzner box |
| `DOCKER_REGISTRY_URL` / `DOCKER_REGISTRY_TOKEN` | Pushing the `gpu_worker` image for RunPod to pull |
| `VERCEL_TOKEN` / `VERCEL_PROJECT_ID` | Only needed if deploying via CI rather than Vercel's git integration |
| `CLOUDFLARE_API_TOKEN` | R2 bucket management via API/Terraform, separate from the R2 S3-compatible keys above |

---

## 4. Payment Processor Outreach Checklist

Business task, not code-blocking — run in parallel with everything else.

- [ ] Draft a one-paragraph product description for support inquiries: face-morphing AI video generator, user-uploaded consenting selfies only, no synthetic/deepfake-of-others content, NSFW-gated.
- [ ] Send to **Payoneer Checkout** support — confirm KZ-registered entity + AI face-content category acceptance.
- [ ] Send to **Stripe** support — note this requires the future US LLC to be in place first; track as a timeline dependency, not immediate.
- [ ] Send to **TipTop Pay Kazakhstan** (ex-CloudPayments) support — confirm acquiring rails and prohibited-content list.
- [ ] Log responses and set `PAYMENT_PROVIDER` in §3.1 once one is confirmed.

---

## 5. SD1.5 Benchmark Spec (RunPod RTX 3090)

De-risks the cost projections in the plan before Phase 1 scope is locked in.

- [ ] Provision a RunPod on-demand RTX 3090 pod.
- [ ] Run SD1.5 img2img repair at 512×512, strength 0.2, for 15 / 25 / 30 inference steps.
- [ ] Record: cold-start time, per-frame inference time at each step count, VRAM usage.
- [ ] Repeat once with ControlNet conditioning enabled, to measure the added overhead.
- [ ] Write results to `docs/benchmarks/sd15_inference.md` (create when run).

---

## 6. Cross-References

- Full phase breakdown: [`implementation_plan.md`](implementation_plan.md)
- GPU worker current implementation + its own env var docs: [`gpu_worker/README.md`](../gpu_worker/README.md)
