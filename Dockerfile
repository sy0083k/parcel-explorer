FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend

COPY frontend/ ./
RUN npm ci
RUN npm run build


FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY scripts ./scripts
COPY data ./data
COPY seed ./seed
COPY create_hash.py README.MD ./

COPY --from=frontend-builder /build/static/dist ./static/dist

RUN mkdir -p /app/data/public_download \
    && chmod +x /app/scripts/verify_vite_manifest.sh \
    && /app/scripts/verify_vite_manifest.sh

EXPOSE 8000
# Proxy trust comes from FORWARDED_ALLOW_IPS (uvicorn default: 127.0.0.1). Set it to the proxy's
# address, or to * only where the app is reachable solely through that proxy (e.g. Railway).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
