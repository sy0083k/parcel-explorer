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
COPY create_hash.py README.MD ./

COPY --from=frontend-builder /build/static/dist ./static/dist

RUN mkdir -p /app/data/public_download \
    && chmod +x /app/scripts/verify_vite_manifest.sh \
    && /app/scripts/verify_vite_manifest.sh

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
