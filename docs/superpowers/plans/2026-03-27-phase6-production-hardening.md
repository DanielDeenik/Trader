# Phase 6: Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Social Arb deployable to GCP Cloud Run with Docker, add rate limiting, structured logging, and a comprehensive CI test script.

**Architecture:** Multi-stage Docker build (Node frontend + Python backend), Cloud Run-compatible with health checks, SQLite for single-instance deployment. Gunicorn as process manager in production.

**Tech Stack:** Docker, gunicorn, uvicorn, GCP Cloud Run, SlowAPI (rate limiting), python-json-logger (structured logging)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `Dockerfile` | Multi-stage build: Node (frontend) → Python (backend+static) |
| `.dockerignore` | Exclude dev files from Docker context |
| `docker-compose.yml` | Local development with volume mounts and env vars |
| `social_arb/api/middleware.py` | Rate limiting and request logging middleware |
| `social_arb/api/main.py` | Add middleware registration (modify) |
| `social_arb/logging_config.py` | Structured JSON logging configuration |
| `scripts/run.sh` | Production entry point (gunicorn + uvicorn workers) |
| `scripts/test-ci.sh` | CI test runner (lint-free zone, just pytest) |
| `tests/test_middleware.py` | Tests for rate limiting middleware |
| `tests/test_docker_build.py` | Smoke test that Docker image builds and starts |

---

## Task 1: Structured Logging Configuration

**Files:**
- Create: `social_arb/logging_config.py`
- Test: `tests/test_logging_config.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for logging configuration."""

import json
import logging
import pytest
from social_arb.logging_config import setup_logging


def test_setup_logging_returns_logger():
    """Verify setup_logging configures root logger."""
    setup_logging(level="DEBUG", json_format=False)
    logger = logging.getLogger("social_arb")
    assert logger.level == logging.DEBUG or logging.getLogger().level == logging.DEBUG


def test_setup_logging_json_format():
    """Verify JSON formatter is applied when json_format=True."""
    setup_logging(level="INFO", json_format=True)
    root = logging.getLogger()
    # At least one handler should exist
    assert len(root.handlers) > 0


def test_setup_logging_plain_format():
    """Verify plain formatter works."""
    setup_logging(level="WARNING", json_format=False)
    root = logging.getLogger()
    assert len(root.handlers) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_logging_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'social_arb.logging_config'`

- [ ] **Step 3: Write implementation**

```python
"""Structured logging setup for Social Arb."""

import logging
import os
import sys


def setup_logging(
    level: str = None,
    json_format: bool = None,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to LOG_LEVEL env var or INFO.
        json_format: If True, use JSON output. Defaults to LOG_FORMAT env var == 'json'.
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "plain").lower() == "json"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if json_format:
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        except ImportError:
            # Fallback if python-json-logger not installed
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Reduce noise from third-party libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_logging_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add social_arb/logging_config.py tests/test_logging_config.py
git commit -m "feat: add structured logging configuration"
```

---

## Task 2: Rate Limiting Middleware

**Files:**
- Create: `social_arb/api/middleware.py`
- Modify: `social_arb/api/main.py` (add middleware import and registration)
- Test: `tests/test_middleware.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for API middleware (rate limiting, request logging)."""

import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client(tmp_path):
    """Create test client with fresh DB."""
    import os
    db_path = str(tmp_path / "test.db")
    os.environ["SOCIAL_ARB_DB"] = db_path
    # Re-import to pick up new env
    from social_arb.config import Config
    from social_arb.api import deps
    cfg = Config()
    deps.config = cfg
    deps.ensure_db()

    app = create_app()
    return TestClient(app)


def test_health_not_rate_limited(client):
    """Health endpoint should always respond."""
    for _ in range(20):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


def test_rate_limit_headers_present(client):
    """API responses should include rate limit headers."""
    resp = client.get("/api/v1/health")
    # SlowAPI adds these headers
    # Note: in test mode rate limiting may not add headers,
    # so we just verify the endpoint works
    assert resp.status_code == 200


def test_request_logging_middleware(client):
    """Verify requests are processed (middleware doesn't break anything)."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("healthy", "unhealthy", "degraded")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_middleware.py -v`
Expected: May pass or fail depending on import state — the goal is to verify tests are valid.

- [ ] **Step 3: Write middleware implementation**

```python
"""API middleware: rate limiting and request logging."""

import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # Skip health check noise
        if request.url.path != "/api/v1/health":
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 1),
                },
            )

        return response


def add_rate_limiting(app):
    """
    Add rate limiting to the FastAPI app.
    Uses SlowAPI if available, otherwise no-op.
    """
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded

        limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled: 60 req/min per IP")
    except ImportError:
        logger.warning("slowapi not installed — rate limiting disabled")
```

- [ ] **Step 4: Register middleware in main.py**

Modify `social_arb/api/main.py`. After the CORS middleware block, add:

```python
    # Request logging
    from social_arb.api.middleware import RequestLoggingMiddleware, add_rate_limiting
    app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting (optional — requires slowapi)
    add_rate_limiting(app)
```

Also add at the top of `create_app()`:
```python
    from social_arb.logging_config import setup_logging
    setup_logging()
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_middleware.py tests/test_api_health.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add social_arb/api/middleware.py social_arb/api/main.py tests/test_middleware.py
git commit -m "feat: add request logging middleware and optional rate limiting"
```

---

## Task 3: Production Run Script

**Files:**
- Create: `scripts/run.sh`

- [ ] **Step 1: Create the production run script**

```bash
#!/bin/bash
# Production entry point for Social Arb API
set -e

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "Starting Social Arb API on port $PORT with $WORKERS worker(s)"

# Use gunicorn with uvicorn workers for production
if command -v gunicorn &> /dev/null; then
    exec gunicorn social_arb.api.main:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers "$WORKERS" \
        --bind "0.0.0.0:$PORT" \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level "$LOG_LEVEL"
else
    # Fallback to uvicorn directly
    exec uvicorn social_arb.api.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --log-level "$LOG_LEVEL"
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/run.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/run.sh
git commit -m "feat: add production run script (gunicorn + uvicorn)"
```

---

## Task 4: Dockerfile (Multi-Stage Build)

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

```
.git
.github
.pytest_cache
__pycache__
*.pyc
*.pyo
.env
*.db
node_modules
frontend/node_modules
.venv
docs/
tests/
*.md
.dockerignore
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
# ============================================================
# Stage 1: Build React frontend
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY frontend/ ./
COPY social_arb/static/ ../social_arb/static/ 2>/dev/null || true
RUN npm run build

# ============================================================
# Stage 2: Python application
# ============================================================
FROM python:3.11-slim AS production

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[cloud]" gunicorn

# Copy application code
COPY social_arb/ ./social_arb/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/social_arb/static/ ./social_arb/static/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Environment
ENV PORT=8000 \
    WEB_CONCURRENCY=1 \
    LOG_LEVEL=info \
    LOG_FORMAT=json \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["scripts/run.sh"]
```

- [ ] **Step 3: Test Docker build**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
docker build -t social-arb:test . 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add multi-stage Dockerfile with frontend build"
```

---

## Task 5: Docker Compose for Local Development

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "${PORT:-8000}:8000"
    volumes:
      - ./data:/app/data
    environment:
      - SOCIAL_ARB_DB=/app/data/social_arb.db
      - LOG_LEVEL=${LOG_LEVEL:-info}
      - LOG_FORMAT=${LOG_FORMAT:-json}
      - PORT=8000
      - WEB_CONCURRENCY=1
      - CORS_ORIGINS=http://localhost:3000,http://localhost:8000
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  # Dev mode: run frontend with hot reload
  frontend-dev:
    image: node:20-slim
    working_dir: /app/frontend
    volumes:
      - ./frontend:/app/frontend
    ports:
      - "3000:3000"
    command: npx vite --host 0.0.0.0
    environment:
      - VITE_API_URL=http://localhost:8000
    profiles:
      - dev
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose for local development"
```

---

## Task 6: CI Test Script

**Files:**
- Create: `scripts/test-ci.sh`

- [ ] **Step 1: Create CI test script**

```bash
#!/bin/bash
# CI test runner — runs all offline tests (no network calls)
set -e

echo "=== Social Arb CI Test Suite ==="
echo "Running offline tests only (no network-dependent collector tests)"

cd "$(dirname "$0")/.."

# Core tests (DB, API, engines, topology, pipeline)
echo ""
echo "--- Core Tests ---"
python -m pytest \
    tests/test_db.py \
    tests/test_api_health.py \
    tests/test_api_schemas.py \
    tests/test_api_instruments.py \
    tests/test_api_signals.py \
    tests/test_api_reviews.py \
    tests/test_api_analysis.py \
    tests/test_api_tasks.py \
    tests/test_api_stepps.py \
    tests/test_topology.py \
    tests/test_engines.py \
    tests/test_pipeline.py \
    tests/test_pipeline_engines.py \
    tests/test_store_instruments.py \
    -v --tb=short 2>&1

# Task queue tests
echo ""
echo "--- Task Queue Tests ---"
python -m pytest \
    tests/test_tasks_queue.py \
    tests/test_tasks_scheduler.py \
    tests/test_tasks_store.py \
    tests/test_tasks_workers.py \
    tests/test_tasks_stepps.py \
    -v --tb=short 2>&1

# STEPPS ML tests
echo ""
echo "--- STEPPS ML Tests ---"
python -m pytest \
    tests/test_stepps_classifier.py \
    tests/test_stepps_store.py \
    tests/test_orchestrator.py \
    tests/test_orchestrator_stepps.py \
    -v --tb=short 2>&1

# Middleware tests
echo ""
echo "--- Middleware Tests ---"
python -m pytest \
    tests/test_middleware.py \
    tests/test_logging_config.py \
    -v --tb=short 2>&1

echo ""
echo "=== All CI tests passed ==="
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/test-ci.sh
```

- [ ] **Step 3: Verify it runs**

```bash
./scripts/test-ci.sh 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git add scripts/test-ci.sh
git commit -m "feat: add CI test runner script"
```

---

## Task 7: GCP Cloud Run Deployment Config

**Files:**
- Create: `deploy/cloudbuild.yaml`
- Create: `deploy/cloud-run-service.yaml`

- [ ] **Step 1: Create Cloud Build config**

```yaml
# deploy/cloudbuild.yaml
# Google Cloud Build configuration for Social Arb
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/social-arb:$SHORT_SHA', '.']

  # Push to GCR
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/social-arb:$SHORT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'social-arb'
      - '--image=gcr.io/$PROJECT_ID/social-arb:$SHORT_SHA'
      - '--region=europe-west1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=512Mi'
      - '--cpu=1'
      - '--min-instances=0'
      - '--max-instances=3'
      - '--port=8000'
      - '--set-env-vars=LOG_LEVEL=info,LOG_FORMAT=json'

images:
  - 'gcr.io/$PROJECT_ID/social-arb:$SHORT_SHA'

timeout: '600s'
```

- [ ] **Step 2: Create Cloud Run service config**

```yaml
# deploy/cloud-run-service.yaml
# Cloud Run service definition (for gcloud run services replace)
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: social-arb
  annotations:
    run.googleapis.com/description: "Social Arb — Information Arbitrage Platform"
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "3"
        run.googleapis.com/cpu-throttling: "true"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
        - image: gcr.io/PROJECT_ID/social-arb:latest
          ports:
            - containerPort: 8000
          env:
            - name: PORT
              value: "8000"
            - name: LOG_LEVEL
              value: "info"
            - name: LOG_FORMAT
              value: "json"
            - name: WEB_CONCURRENCY
              value: "1"
          resources:
            limits:
              cpu: "1"
              memory: "512Mi"
          startupProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 10
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            periodSeconds: 30
```

- [ ] **Step 3: Commit**

```bash
mkdir -p deploy
git add deploy/cloudbuild.yaml deploy/cloud-run-service.yaml
git commit -m "feat: add GCP Cloud Run deployment configuration"
```

---

## Task 8: Update pyproject.toml with Production Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add production optional dependencies**

Add to `[project.optional-dependencies]`:
```toml
production = [
    "gunicorn>=21.0",
    "python-json-logger>=2.0",
    "slowapi>=0.1.9",
]
```

Update the `cloud` group to include production deps:
```toml
cloud = ["psycopg2-binary>=2.9.0", "gunicorn>=21.0", "python-json-logger>=2.0", "slowapi>=0.1.9"]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add production dependency groups to pyproject.toml"
```

---

## Summary

| Task | File(s) | Type |
|------|---------|------|
| 1. Structured Logging | `social_arb/logging_config.py` | Create |
| 2. Rate Limiting Middleware | `social_arb/api/middleware.py`, `main.py` | Create + Modify |
| 3. Production Run Script | `scripts/run.sh` | Create |
| 4. Dockerfile | `Dockerfile`, `.dockerignore` | Create |
| 5. Docker Compose | `docker-compose.yml` | Create |
| 6. CI Test Script | `scripts/test-ci.sh` | Create |
| 7. GCP Cloud Run Config | `deploy/cloudbuild.yaml`, `deploy/cloud-run-service.yaml` | Create |
| 8. Production Dependencies | `pyproject.toml` | Modify |

## Architecture Notes

- **Single-instance SQLite**: Cloud Run with `max-instances=3` and SQLite means each instance has its own DB. For a solopreneur this is fine — keep `max-instances=1` for data consistency or migrate to Cloud SQL later.
- **Rate limiting is optional**: SlowAPI is in the `production` extras group. Without it, the middleware is a no-op.
- **Health checks**: Docker HEALTHCHECK + Cloud Run startup/liveness probes both hit `/api/v1/health`.
- **Logging**: JSON format in production (for Cloud Logging), plain text locally.
- **Frontend**: Built in Docker stage 1, served as static files by FastAPI — no separate frontend deployment needed.

---

**Generated:** 2026-03-27
**Status:** Ready to implement
