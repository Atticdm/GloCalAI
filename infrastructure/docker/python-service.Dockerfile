ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

ARG SERVICE_NAME
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core procps curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages ./packages
COPY services/${SERVICE_NAME} ./service

WORKDIR /app/service

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/service:/app/packages

CMD ["python", "main.py"]
