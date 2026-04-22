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
    -v --tb=short

# Task queue tests
echo ""
echo "--- Task Queue Tests ---"
python -m pytest \
    tests/test_tasks_queue.py \
    tests/test_tasks_scheduler.py \
    tests/test_tasks_store.py \
    tests/test_tasks_workers.py \
    tests/test_tasks_stepps.py \
    -v --tb=short

# STEPPS ML tests
echo ""
echo "--- STEPPS ML Tests ---"
python -m pytest \
    tests/test_stepps_classifier.py \
    tests/test_stepps_store.py \
    tests/test_orchestrator.py \
    tests/test_orchestrator_stepps.py \
    -v --tb=short

# Middleware tests
echo ""
echo "--- Middleware Tests ---"
python -m pytest \
    tests/test_middleware.py \
    tests/test_logging_config.py \
    -v --tb=short

echo ""
echo "=== All CI tests passed ==="
