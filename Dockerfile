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

RUN useradd --create-home appuser && mkdir -p /data && chown appuser /data
USER appuser

EXPOSE 8000
# --proxy-headers so share links use https behind Railway's proxy.
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
