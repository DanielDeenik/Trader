# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

# Don't buffer Python stdout/stderr, don't write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so the layer caches when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app (config/, docs/, .git, etc. are excluded
# by .dockerignore).
COPY . .

# Cloud Run sends traffic to whatever the container listens on at
# $PORT (default 8080). Bind to 0.0.0.0 — localhost won't be reachable.
ENV PORT=8080
EXPOSE 8080

# Production WSGI server. `server = app.server` is defined in app/app.py.
# Two workers × four threads is a reasonable default for a Dash app;
# tune via gcloud on the Cloud Run service if needed.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 app.app:server"]
