#!/bin/bash
# Deploy Social Arb to Google Cloud Run
# Usage: ./scripts/deploy-gcp.sh
set -e

PROJECT_ID="${GCP_PROJECT:-delphi-449908}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="social-arb"

echo "================================================"
echo "  Deploying Social Arb to Cloud Run"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Service: $SERVICE_NAME"
echo "================================================"

# Step 1: Ensure correct project
echo ""
echo "[1/5] Setting GCP project..."
gcloud config set project "$PROJECT_ID"

# Step 2: Enable required APIs (idempotent)
echo ""
echo "[2/5] Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

# Step 3: Create Artifact Registry repo (if it doesn't exist)
echo ""
echo "[3/5] Ensuring Artifact Registry repo exists..."
gcloud artifacts repositories create social-arb \
    --repository-format=docker \
    --location="$REGION" \
    --description="Social Arb Docker images" \
    2>/dev/null || echo "  (repo already exists)"

# Step 4: Build and deploy using Cloud Run source deploy
# This handles: build → push → deploy in one command
echo ""
echo "[4/5] Building and deploying (this takes 3-5 minutes)..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --port 8000 \
    --set-env-vars "LOG_LEVEL=info,LOG_FORMAT=json" \
    --timeout 300

# Step 5: Get the URL
echo ""
echo "[5/5] Getting service URL..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo "================================================"
echo "  DEPLOYED SUCCESSFULLY!"
echo "  URL:  $SERVICE_URL"
echo "  API:  $SERVICE_URL/api/v1/health"
echo "  Docs: $SERVICE_URL/docs"
echo "================================================"
