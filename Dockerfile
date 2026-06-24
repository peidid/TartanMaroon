# One Railway image: builds the Next.js UI, then the FastAPI backend serves both
# the API and the static UI from the same origin.

# ---- Stage 1: build the frontend (static export -> /fe/out) ----
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Empty API URL => the client calls /api/... on the same origin (this server).
ENV NEXT_PUBLIC_API_URL="" NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- Stage 2: backend (advisor engine + FastAPI) ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies (+ the advisor package from src) first for layer caching.
COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
RUN uv sync --no-dev

# App code + data + the exported UI.
COPY backend ./backend
COPY data ./data
COPY --from=frontend /fe/out ./frontend_out

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/api/health || exit 1

CMD ["sh", "-c", "uv run --no-dev uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
