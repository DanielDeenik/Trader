#!/bin/bash
# Production entry point for Social Arb API
set -e

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "Starting Social Arb API on port $PORT with $WORKERS worker(s)"

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
    exec uvicorn social_arb.api.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --log-level "$LOG_LEVEL"
fi
