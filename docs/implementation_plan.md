# Implementation Plan — AI Morphing Generator MVP

## 0. Pre-Development Checklist (Blockers — resolve before writing code)

Full step-by-step setup path and complete environment-variable inventory: [`docs/phase0_environment_setup.md`](phase0_environment_setup.md).

- [ ] Confirm payment processor accepts KZ-registered entity + face-morph AI content category
  - Contact Payoneer Checkout support directly with product description
  - Contact Stripe (via future US LLC) support directly with product description
  - Contact TipTop Pay Kazakhstan (ex-CloudPayments) — confirm acquiring rails, prohibited list
- [ ] Benchmark real SD1.5 inference time on target GPU (RTX 3090, community cloud RunPod)
- [x] Choose landmark detection library: **MediaPipe** (Apache 2.0 — InsightFace's model zoo is non-commercial-only, a licensing risk for a paid product)
- [x] Choose identity-consistency method: **IP-Adapter FaceID** (ArcFace embeddings via InsightFace's `buffalo_l`, `app/services/face_embedding.py`) — supersedes the earlier ControlNet decision below. InsightFace's `buffalo_l` is licensed non-commercial-research-only; this is a **known, currently-unresolved legal exposure for a paid product**, not a cleared risk — see the Cross-Phase Open Risks table. Revisit with a commercial license or a swap back to ControlNet before shipping paid.
  - ~~Previously: **ControlNet** (canny/openpose) — IP-Adapter FaceID and InstantID both depend on InsightFace's non-commercial-licensed embedding models, rejected for the same reason~~ (superseded — reversed in gpu_worker without a corresponding licensing resolution)
- [x] Decide SQLite (fast start) vs Postgres (from day 1): **SQLite** for MVP, migrate in Phase 2 (per §1.1)
- [ ] Register domain, set up Vercel account, set up Railway project (web + worker services, Redis add-on, volume for SQLite)

---

## Phase 1 — MVP Core Loop (Target: 4-6 weeks)

### 1.1 Infrastructure Setup

- Railway provisioning (not local machine): one project, `web` service (FastAPI) + `worker` service (RQ) from the same repo/image, Railway Redis add-on, volume mounted for SQLite
- FastAPI backend skeleton: `app/main.py`, routers structure per original spec
  - `app/api/routes/{projects,uploads,jobs,preview,billing,settings}.py`
- RQ (Redis Queue) instead of Celery — simpler worker setup
- SQLite for MVP (migrate to Postgres in Phase 2)
- Cloudflare R2 bucket setup (free tier, 0 egress)
- `.env` config: `POSTGRES_URL` / `SQLITE_PATH`, `REDIS_URL`, `RUNPOD_API_KEY`, `STORAGE_PATH`, `PREVIEW_ENABLED`

### 1.2 GPU Worker Setup

- RunPod serverless endpoint provisioning
- `gpu-worker/worker/`: `repair_pipeline.py`, `upscale_pipeline.py`, `inference.py`, `api.py`
- Load SD 1.5 + chosen identity-consistency extension (ControlNet/IP-Adapter FaceID)
- Dockerfile for worker container, push to registry
- Test cold-start latency + inference time per frame (record actual numbers)

### 1.3 Upload & Project Flow (US-1.1 – US-1.4)

- Frontend: `UploadZone.tsx` (react-dropzone), `ImageSorter.tsx` (@dnd-kit/core)
- Backend: `POST /projects`, `POST /projects/{id}/assets`
- Validation: MIME type, file signature check, file size limit
- NSFW check integration (pre-inference gate)
- Face detection gate (reject 0-face uploads)
- Auto-delete source files after processing (privacy/GDPR-lite policy)

### 1.4 Preview Pipeline (US-2.1 – US-2.5)

- `morph_engine.py`: normalization → landmark warping → blend → easing (CPU stages)
- `POST /projects/{id}/preview` → enqueue job to `preview_gpu` queue
- Stage 3 AI repair call to RunPod worker (SD1.5 img2img, strength 0.15–0.35, fixed seed)
- Interpolation + deflicker (CPU postprocess)
- Preview config: 512px, 2 sec, 12fps, TTL 3h, limit 3/project
- `GET /jobs/{id}` polling endpoint, job states: queued/running/retrying/failed/completed
- Frontend: `ProgressBar.tsx`, `PreviewPlayer.tsx`, 1-2 fixed style presets only (no full SettingsPanel yet)

### 1.5 Payment Integration (US-3.1 – US-3.3)

- Decision from 0.1 checklist determines provider (Payoneer Checkout / Stripe / TipTop Pay)
- `POST /checkout` → hosted checkout redirect
- `POST /payments/webhook` — signature validation, idempotency check
- Order record creation on webhook success

### 1.6 Full Render Pipeline (US-4.1 – US-4.3)

- `POST /projects/{id}/render` triggered post-payment
- Stage 4 (interpolation/smoothing) + Stage 5 (cinematic layer: zoom/pan/hold/motion blur)
- FFmpeg assembly service (`ffmpeg_service.py`)
- Full render config: 6-12 sec, 24fps, 1080x1920, MP4
- Retry policy: GPU timeout retry, FFmpeg retry, transient network retry
- Dead-letter queue (`failed_jobs`) for exhausted retries

### 1.7 Result & Delivery (US-5.1 – US-5.3)

- Signed expiring download URLs (R2)
- Watermark applied programmatically on preview/free exports only
- Share button (native share + direct link) — kept in MVP scope, not deferred

### 1.8 Reliability Baseline (US-8.1 – US-8.3)

- `/health/live`, `/health/ready` endpoints
- Rate limiting middleware (`rate_limit.py`) on upload/render endpoints
- Cleanup job (scheduled) for source file deletion
- Logging: request_id, job_id, project_id (structured, to file/Sentry — no Prometheus yet)

**Phase 1 Exit Criteria:** end-to-end flow works (upload → preview → pay → full render → download), core unit economics measured, identity-consistency quality assessed against real benchmark.

---

## Phase 2 — Post-Validation Hardening (Target: after Phase 1 metrics confirm demand)

### 2.1 Data Layer

- Migrate SQLite → PostgreSQL
- Full schema: `users`, `projects`, `assets`, `jobs`, `orders`, `outputs`, `app_settings`, `audit_log`

### 2.2 Product Expansion

- Full `SettingsPanel.tsx`: additional Style/Format/Duration/Music options (US monetization hooks)
- Upsell flow: 4K upscale option, extended duration (US-6.1)
- Seasonal style packs (Phase 2/3 retention driver)

### 2.3 Retention & Growth

- Referral system: unique links, credit on referred user's first paid action (US-6.2)
- Notification system (email/push opt-in) for new styles (US-6.3)
- Consider subscription tier (N morphs/month) if usage frequency data supports it

### 2.4 Payment Localization

- Add Xendit (Indonesia + Philippines) or PayMongo (Philippines) for local methods (GCash/OVO/DANA)
- Add PayPal as secondary checkout option for US market trust signal

### 2.5 Admin Tooling (US-7.1 – US-7.2)

- `app_settings` toggle: preview enable/disable
- Configurable preview limits (count, TTL) via DB, no-deploy changes

### 2.6 GPU Cost Optimization

- Evaluate warm worker pool if traffic justifies fixed cost (~$290-360/mo) vs cold-start serverless
- Re-benchmark on cheaper GPU tier (RTX 3060/4070 12GB) if VRAM headroom confirmed unnecessary

**Phase 2 Exit Criteria:** Postgres stable in production, referral/upsell live, SEA local payment methods integrated, cost-per-video optimized based on real usage data.

---

## Phase 3 — Scaling Infrastructure

### 3.1 Observability

- Prometheus + `metrics_registry.py`, `job_tracing.py`
- Full structured logging: queue_name, gpu_worker_id, render_duration
- Metrics: render duration, queue wait time, GPU usage, failure rate

### 3.2 GPU Worker Scaling

- Multiple concurrent RunPod/Vast.ai workers
- Load balancing across `preview_gpu` / `full_gpu` queues
- Priority queue enforcement (preview > full) under load

### 3.3 Reliability Maturity

- Full dead-letter queue handling + alerting
- Automated refund/re-render flow on exhausted retries

**Phase 3 Exit Criteria:** system handles concurrent load without manual intervention, full observability dashboard live.

---

## Phase 4 — Dedicated Infrastructure

- Evaluate dedicated GPU infra vs continued serverless (cost crossover analysis)
- Evaluate SDXL migration if Phase 1-2 quality data shows SD1.5 ceiling reached (per original MVP Goals, section 20)
- Multi-region backend deployment if international scale justifies it

---

## Cross-Phase Open Risks to Track

| Risk                                                                  | Status                                                                         | Mitigation Owner |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------- |
| Payment processor rejects AI face-content category                    | Open — pending support responses                                               | Business         |
| Identity drift/flicker in SD1.5 repair                                | Open — needs ControlNet/IP-Adapter validation                                  | Engineering      |
| GPU inference time unbenchmarked (all cost estimates are projections) | Open                                                                           | Engineering      |
| KZ entity fund withdrawal friction (PayPal, general banking)          | Open                                                                           | Business         |
| Non-consensual face upload abuse                                      | Partial — NSFW+face-detection gate planned, no identity-ownership verification | Product/Legal    |
| InsightFace `buffalo_l` (IP-Adapter FaceID) is non-commercial-research-licensed; gpu_worker now depends on it in a paid product | Open — needs a commercial license or a swap back to ControlNet before shipping paid | Business/Legal |
