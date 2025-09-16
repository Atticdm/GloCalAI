# Glocal Ads AI Architecture

## Overview

The repository is a mono-repo containing a Next.js 14 frontend, a FastAPI backend, and a suite of Python worker services connected through RabbitMQ and Redis. Media assets are stored in MinIO (S3 compatible). Postgres stores relational data and Redis offers pub/sub for real-time status updates.

```
frontend (Next.js)
    ↕ REST/SSE
FastAPI BFF
    ↕ SQLAlchemy/Redis/RabbitMQ/S3
RabbitMQ (jobs exchange)  <—>  Orchestrator  <—>  Worker micro-services
Redis (pub/sub)           <—>  Frontend SSE progress
Postgres                  <—>  FastAPI + workers
MinIO (S3 bucket)         ⇄   Media ingestion & artifacts
```

## Applications

### Frontend (`apps/frontend`)
* Next.js 14 App Router with TypeScript.
* Authentication via FastAPI (`/auth/sign-in`). Token stored in local storage.
* Pages:
  * `/` — project list + creation.
  * `/projects/[id]` — asset upload to MinIO, localization job form.
  * `/jobs/[id]` — SSE-driven pipeline progress per language/stage.
  * `/results/[jobId]` — variant previews (HLS) with download & YouTube actions.
* Uses `react-hook-form`, shadcn-inspired UI primitives, `hls.js` for preview.

### API (`apps/api`)
* FastAPI + SQLAlchemy 2.0 + async Postgres (psycopg3).
* Provides auth, project & asset management, job orchestration endpoints, SSE progress stream, variant downloads, and YouTube stub.
* Integrations: Redis pub/sub, RabbitMQ (via `aio-pika`), MinIO (boto3), JWT auth, Alembic-like SQL migrations (raw SQL in `migrations/sql`).
* On startup ensures S3 bucket policy via MinIO client and seeds admin/demo data.

## Services (`services/*`)
* Shared utilities packaged in `packages/service-kit` (config, DB helpers, S3, RabbitMQ, Redis progress helper, path helpers).
* Each worker listens to a dedicated routing key (`stage.<name>`) and publishes completion/error events back (`stage.<name>.completed|failed`).
* Orchestrator sequences stages per language, updates DB, emits Redis progress, and optionally triggers YouTube uploads.
* Workers emulate the media pipeline:
  * `asr-agent`: generates dummy segments & transcript.
  * `translate-agent`: applies pseudo translation with suffix `[lang]`.
  * `tts-agent`: synthesises sine-wave speech from segments.
  * `mix-agent`: runs FFmpeg to mux original video + TTS, produces MP4 + HLS.
  * `subs-agent`: builds SRT/VTT from translated segments.
  * `textinframe-agent`: overlays localized text via FFmpeg drawtext + new HLS.
  * `qc-agent`: probes final output and writes JSON QC report.
  * `yt-uploader`: logs pseudo YouTube URL and notifies Redis.

## Messaging Flow

1. API `/jobs` inserts job + variants and publishes `job.created` message.
2. Orchestrator consumes `job.created`, sets variants to `processing`, queues first stage (`stage.asr`).
3. Each worker retrieves job/variant context from Postgres via service kit, reads/writes artifacts in MinIO, updates DB fields, and publishes progress using Redis + `stage.<stage>.completed` message.
4. Orchestrator hears completion events, queues next stage (skipping optional ones based on job options), and finally marks variant/job done.
5. Frontend subscribes via `/jobs/{id}/stream` SSE channel and renders per-stage updates.

## Storage Layout

MinIO bucket `glocal-media` stores assets:
* `raw/{projectId}/{assetId}/source.mp4`
* `jobs/{jobId}/{lang}/asr/segments.json`
* `jobs/{jobId}/{lang}/tts/track.wav`
* `jobs/{jobId}/{lang}/mix/out.mp4`
* `jobs/{jobId}/{lang}/mix/hls/...`
* `jobs/{jobId}/{lang}/subs/subtitles.(srt|vtt)`
* `jobs/{jobId}/{lang}/textinframe/out.mp4`
* `jobs/{jobId}/{lang}/qc/report.json`

Postgres tables follow schema defined in `migrations/sql/001_init.sql` (users, projects, assets, jobs, variants, voice profiles, glossaries).

## Infrastructure

* Dockerfiles live in `infrastructure/docker` for API, frontend, and generic Python services.
* `docker-compose.yml` orchestrates Postgres, Redis, RabbitMQ, MinIO (+ mc bootstrap), API, frontend, orchestrator, all agents, and migration job.
* Basic Kubernetes manifests provided under `infrastructure/k8s/` as a starting point.

## Scripts & Automation

* `scripts/dev/generate-test-video.sh` — produces an 8s synthetic demo video.
* `scripts/dev/smoke.sh` — end-to-end happy-path using FastAPI endpoints.
* GitHub Actions workflow (`ci.yml`) runs Ruff/Black/Mypy and Next.js lint.

## Notes

* SSE endpoints and variant preview/download accept either `Authorization` header or `?token=` query string for EventSource/video tags.
* Bucket policy is configured for anonymous read to support direct HLS loads.
* The architecture is modular to later swap emulators with real ML models (WhisperX, NLLB/LLM, XTTS, etc.) without changing orchestration plumbing.
