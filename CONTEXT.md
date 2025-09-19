# Project Context Snapshot

## Repository Structure
- `apps/api` – FastAPI BFF, asynchronous SQLAlchemy, Alembic-style migrations (raw SQL in `migrations/sql`).
- `apps/frontend` – Next.js 14 App Router UI with shadcn-style components and HLS preview.
- `services/` – Orchestrator and worker agents (`asr`, `translate`, `tts`, `mix`, `subs`, `textinframe`, `qc`, `yt-uploader`) built from `infrastructure/docker/python-service.Dockerfile` via `SERVICE_NAME` arg.
- `packages/` – Shared Pydantic schemas and service toolkit (DB, S3, RabbitMQ, Redis helpers).
- `infrastructure/docker` – Dockerfiles for API, frontend, generic worker, RabbitMQ, MinIO.
- `scripts/dev` – Utilities: `generate-test-video.sh`, `smoke.sh`, `init-minio.sh`.
- `railway.json` – Maps Railway services to the correct Dockerfiles/args.

## Railway Services (running infrastructure)
- **Postgres** (managed, with attached volume) – needs database `glocal_db` created manually.
- **Redis** (managed) – provides pub/sub for SSE.
- **RabbitMQ** (`rabbitmq:3.12-management` image) – credentials `glocal/glocalpass`.
- **MinIO** (`minio/minio:<latest>` image) – volume mounted at `/data`; bucket `glocal-media` must exist (run `scripts/dev/init-minio.sh`).

## Environment Variables (shared across services)
Set in Railway Shared Variables using internal hostnames:
```
APP_ENV=prod
JWT_SECRET=<random secret>
POSTGRES_DSN=postgresql://<user>:<pass>@<postgres-internal-host>:5432/glocal_db
REDIS_URL=redis://:<redis-password>@<redis-internal-host>:6379/0
RABBITMQ_URL=amqp://glocal:glocalpass@<rabbitmq-internal-host>:5672/
S3_ENDPOINT=http://<minio-internal-host>:9000
S3_PUBLIC_URL=<public MinIO URL or http://minio:9000>
S3_BUCKET=glocal-media
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
API_BASE_URL=http://api:8080
PUBLIC_API_URL=https://<api-service>.up.railway.app
NEXT_PUBLIC_API_URL=https://<api-service>.up.railway.app
NEXT_PUBLIC_MINIO_PUBLIC_URL=<public MinIO URL>
```

## Outstanding Tasks
1. **Database prep:** Create database `glocal_db` in Postgres and run migrations `migrations/sql/001_init.sql` & `002_seed.sql`.
2. **MinIO init:** Execute `scripts/dev/init-minio.sh` with `MINIO_HOST`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` pointing to Railway MinIO internal host.
3. **Deploy app services via Railway CLI** (uses `railway.json`):
   - `railway up --service api`
   - `railway up --service frontend`
   - `railway up --service orchestrator`
   - `railway up --service <each-agent>` (`asr-agent`, `translate-agent`, `tts-agent`, `mix-agent`, `subs-agent`, `textinframe-agent`, `qc-agent`, `yt-uploader`)
4. **Verify & smoke test:**
   - Check API health (`GET /healthz`).
  - Login via frontend (admin@glocal.ai / admin12345).
   - Run `scripts/dev/generate-test-video.sh` and `scripts/dev/smoke.sh` with `API_URL` & `S3_PUBLIC_URL` pointing to Railway endpoints.
   - Confirm job pipeline completes and assets are downloadable.

Keep this file updated after major changes; hand it to the next assistant session for instant context.
