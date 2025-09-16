#!/usr/bin/env bash
set -euo pipefail

# Usage: MINIO_HOST=http://127.0.0.1:9000 MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin ./scripts/dev/init-minio.sh

: "${MINIO_HOST:?Set MINIO_HOST, e.g. http://minio:9000}"
: "${MINIO_ACCESS_KEY:?Set MINIO_ACCESS_KEY}"
: "${MINIO_SECRET_KEY:?Set MINIO_SECRET_KEY}"

mc alias set local "$MINIO_HOST" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc mb --ignore-existing local/glocal-media
mc anonymous set download local/glocal-media

printf "MinIO bucket glocal-media is ready at %s\n" "$MINIO_HOST"
