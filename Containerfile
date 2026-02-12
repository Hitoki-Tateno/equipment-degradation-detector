# ============================================================
# Build stage: Frontend
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ============================================================
# Runtime stage
# ============================================================
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Python dependencies (uv)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

# Backend
COPY backend/ backend/

# Frontend (from build stage)
COPY --from=frontend-builder /build/build/ /usr/share/nginx/html/

# Config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Data directory
RUN mkdir -p /app/data

EXPOSE 80 8000

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
