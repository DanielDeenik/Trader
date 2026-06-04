#!/bin/bash
# Social Arb — Local Development Server
# Usage: ./run.sh
# Then open http://localhost:8000 in your browser
# Login: deenikdaniel@gmail.com / socialarb

set -e

cd "$(dirname "$0")"

echo "Social Arb — Starting..."
echo ""

# Clear stale bytecode
find social_arb -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Disable the background scheduler (prevents automatic data collection)
export DISABLE_SCHEDULER=1

echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn social_arb.api.main:app --host 127.0.0.1 --port 8000 --reload
