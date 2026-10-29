FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SQLITE_PATH=/data/app.db

# ffmpeg converts WhatsApp voice notes when a model can't read OGG/Opus directly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY web ./web
COPY examples ./examples
COPY seed ./seed

# Runs as root on purpose: Railway mounts the volume at /data owned by root, and a non-root user can't write the
# SQLite file there (Railway's volume docs). /api/health returns 503 if the database isn't writable.
RUN mkdir -p /data

EXPOSE 8000
# Keep socket peer addresses intact; PUBLIC_BASE_URL supplies the HTTPS share origin.
# Railway edge-only deployments may explicitly enable TRUST_RAILWAY_EDGE for X-Real-IP.
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --no-proxy-headers"]
