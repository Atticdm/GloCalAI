# Glocal Ads AI

A mono-repo for the Glocal Ads AI localization platform. It ships a Next.js 14 frontend, FastAPI backend, and a fleet of Python workers that emulate the localization pipeline (ASR → Translate → TTS → Mix → Subs → Text-in-frame → QC → Pack). Services communicate via RabbitMQ, store metadata in Postgres, share progress through Redis SSE, and persist media artefacts in MinIO.

## Prerequisites

* Docker & Docker Compose
* Node.js 20 (for local Next.js development) with `pnpm`
* Python 3.11+
* FFmpeg for local smoke scripts

## Initial Setup

```bash
# install frontend dependencies and generate lockfile
cd apps/frontend
pnpm install
cd ../..

# install Python dependencies (API + services)
python3 -m pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
for req in services/*/requirements.txt; do python3 -m pip install -r "$req"; done
```

Populate a demo source clip:

```bash
scripts/dev/generate-test-video.sh
```

## Running with Docker Compose

```bash
docker compose build
docker compose up -d
```

Services exposed:

* UI — http://localhost:3000
* API docs — http://localhost:8080/docs
* MinIO console — http://localhost:9001 (minioadmin/minioadmin)
* RabbitMQ console — http://localhost:15672 (glocal/glocalpass)

Check status:

```bash
docker compose ps
```

## Smoke Test

After the stack is healthy:

```bash
bash scripts/dev/smoke.sh
```

The script logs in, uploads `assets/source.mp4`, launches a job for `es` and `pt-BR`, polls until completion, and prints download URLs.

## Local Development

### Frontend (Next.js)

```bash
cd apps/frontend
pnpm dev
```

### API (FastAPI)

```bash
cd apps/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Workers can be run individually, e.g.:

```bash
cd services/asr-agent
python main.py
```

## Scripts

* `scripts/dev/generate-test-video.sh` — generate demo video (8s, 1920×1080).
* `scripts/dev/smoke.sh` — end-to-end happy-path automation.

## Testing & Linting

```bash
# Ruff + Black + Mypy
ruff check apps/api services packages
black apps/api services packages
mypy apps/api/app

# Frontend lint
cd apps/frontend
pnpm lint
```

CI is configured in `.github/workflows/ci.yml` to execute the same checks.

## Environment Variables

The root `.env` powers Docker Compose and runtime services. Key values:

```
APP_ENV=dev
JWT_SECRET=dev_secret_key_xyz
POSTGRES_DSN=postgresql://glocal_user:strongpass123@postgres:5432/glocal_db
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://glocal:glocalpass@rabbitmq:5672/
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_URL=http://localhost:9000
S3_BUCKET=glocal-media
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
API_BASE_URL=http://api:8080
PUBLIC_API_URL=http://localhost:8080
```

Frontend build-time variables live in `apps/frontend/.env.local` and mirror the public endpoints.

## Project Structure

```
apps/
  api/               FastAPI BFF
  frontend/          Next.js App Router UI
services/            RabbitMQ worker fleet (orchestrator + agents)
packages/
  shared-schemas/    Pydantic models shared across services
  service-kit/       Shared worker utilities (DB, S3, RabbitMQ, Redis)
infrastructure/
  docker/            Dockerfiles
  k8s/               Example Kubernetes manifests
migrations/sql/      SQL migrations & seed data
scripts/dev/         Developer utilities
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deeper dive.
