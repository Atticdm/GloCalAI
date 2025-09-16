FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && rm -rf /var/lib/apt/lists/*

COPY packages ./packages
COPY apps/api ./apps/api

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r apps/api/requirements.txt

ENV PYTHONPATH=/app/apps/api:/app/packages

WORKDIR /app/apps/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
