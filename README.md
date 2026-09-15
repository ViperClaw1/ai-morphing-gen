# AI Morphing Generator

An AI-powered face-morph video generator: users upload a sequence of face photos, the
pipeline warps/blends between them and repairs artifacts with Stable Diffusion 1.5
img2img (identity-consistency via ControlNet), then assembles a short cinematic video
via FFmpeg. Users get a free low-res preview before paying for a full-resolution render.

Full product/architecture spec: [`docs/implementation_plan.md`](docs/implementation_plan.md).
Environment/setup checklist: [`docs/phase0_environment_setup.md`](docs/phase0_environment_setup.md).

**Status**: Phase 1 (MVP Core Loop), early — backend skeleton and GPU worker exist;
upload/preview/payment/render logic is not yet implemented. See
[Current Status](#current-status) below.

---

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌───────────────┐
│  Frontend    │─────▶│  Backend (FastAPI) │─────▶│  RQ / Redis    │
│  (Next.js)   │      │  backend/app/       │      │  preview_gpu   │
│  not started │◀─────│  SQLite → Postgres  │◀─────│  full_gpu      │
└─────────────┘      └──────────────────┘      └───────┬────────┘
                                                          │
                                                          ▼
                                                ┌────────────────────┐
                                                │  GPU Worker          │
                                                │  gpu_worker/app/      │
                                                │  SD 1.5 img2img repair │
                                                │  → RunPod serverless   │
                                                └────────────────────┘
```

- **Backend** enqueues jobs; it never calls the GPU synchronously in a request path.
- **GPU worker** is a standalone service (own repo folder, own README, own deploy
  target) — it only does image repair, no auth/billing/queue/DB of its own.
- **Preview jobs always take priority over full renders** — enforced today by RQ worker
  startup order (`rq worker preview_gpu full_gpu`), not by a priority field. See the
  [deep dive](deep-dive/backend-app-mvp-skeleton-2026-08-21.md#rq-priority-via-queue-draining-order-not-a-priority-field)
  for why that's a footgun worth knowing about.

## Repo layout

```
backend/       FastAPI + RQ backend — app/{api,core,models,schemas}/, tests/
gpu_worker/    Standalone SD 1.5 repair service, deployed to RunPod — see gpu_worker/README.md
frontend/      Next.js app — not yet created
docs/          Implementation plan, phase 0 setup guide
deep-dive/     AntiVibe-generated learning notes on this codebase
.claude/       Project rules Claude Code must follow (code-style, testing, API conventions)
```

## Stack

| Layer      | Choice                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| Frontend   | Next.js, TypeScript, TailwindCSS, Zustand, shadcn/ui                   |
| Backend    | Python 3.10, FastAPI, Uvicorn, RQ (Redis Queue) — not Celery           |
| DB         | SQLite (Phase 1) → PostgreSQL (Phase 2)                                |
| GPU worker | RunPod serverless, SD 1.5 + ControlNet, FFmpeg                         |
| Storage    | Cloudflare R2 (S3-compatible, zero egress)                             |
| Payments   | Payoneer Checkout / Stripe / TipTop Pay — provider TBD, see open risks |

## Current status

- ✅ `GET /settings/public` — the only fully implemented backend route.
- 🚧 Every other backend route (`/projects`, `/projects/{id}/assets`, `/projects/{id}/preview`,
  `/projects/{id}/render`, `/jobs/{id}`, `/checkout`, `/payments/webhook`) returns
  `501 NOT_IMPLEMENTED` — the schema/error-shape contract is locked in, the logic isn't built.
- ✅ GPU worker's `/repair` endpoint is fully implemented and independently runnable/testable.
- ❌ Frontend not started.
- ❌ NSFW + face-detection gate, source-photo auto-deletion, payment webhook logic — not built
  (these are hard requirements per [`CLAUDE.md`](CLAUDE.md), not yet implemented).

For a deeper walkthrough of the backend skeleton's design decisions (settings-as-singleton,
the `AppError` pattern, request-ID log correlation, etc.), see
[`deep-dive/backend-app-mvp-skeleton-2026-08-21.md`](deep-dive/backend-app-mvp-skeleton-2026-08-21.md).

## Getting started

Each service has its own setup instructions:

- [`backend/README.md`](backend/README.md) — FastAPI backend (venv, `.env`, `uvicorn`)
- [`gpu_worker/README.md`](gpu_worker/README.md) — GPU worker (Linux + NVIDIA GPU required;
  CPU inference is not supported, dev machines without a GPU cannot run this locally)

Frontend setup will be added once `frontend/` exists.

## Rules Claude Code (and contributors) must follow

Non-negotiable architecture rules live in [`CLAUDE.md`](CLAUDE.md) — queue choice (RQ, not
Celery), no synchronous GPU calls in the request path, preview-before-full queue priority,
mandatory source-photo deletion, payment webhook signature/idempotency requirements, and the
NSFW/face-detection gate. Code style, API conventions, and testing requirements are in
[`.claude/rules/`](.claude/rules/).
