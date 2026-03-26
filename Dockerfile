# ============================================================
# Stage 1: Build React frontend
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: Python application
# ============================================================
FROM python:3.11-slim AS production

# System deps for lxml
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
