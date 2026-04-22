# -----------------------------------------------------------
# Social Arb - Google Cloud Run Deployment
# -----------------------------------------------------------
#
# Quick start:
#   make setup    - first-time GCP setup (APIs, Artifact Registry)
#   make deploy   - build and deploy to Cloud Run
#   make open     - open the live app in browser
#   make logs     - tail production logs
#   make teardown - delete everything
#
# -----------------------------------------------------------

# -- Config -------------------------------------------------
PROJECT      := delphi-449908
REGION       := europe-west1
SERVICE      := social-arb
REPO         := social-arb
IMAGE        := $(REGION)-docker.pkg.dev/$(PROJECT)/$(REPO)/api
MEMORY       := 512Mi
CPU          := 1
MIN_INST     := 0
MAX_INST     := 3

.PHONY: help setup deploy open logs logs-follow status health url build run-local teardown clean permissions registry

help: ## Show all commands
	@echo ""
	@echo "  Social Arb - Cloud Run"
	@echo "  Project: $(PROJECT) | Region: $(REGION)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

setup: permissions registry ## First-time GCP setup (APIs + Artifact Registry)
	@echo ""
	@echo "Done. Run 'make deploy' to ship it."

permissions: ## Enable required GCP APIs
	@echo "Enabling GCP APIs..."
	gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com artifactregistry.googleapis.com --project=$(PROJECT)
	@echo "APIs enabled."

registry: ## Create Artifact Registry repo
	@echo "Setting up Artifact Registry..."
	gcloud artifacts repositories describe $(REPO) --location=$(REGION) --project=$(PROJECT) 2>/dev/null \
		&& echo "Registry already exists" \
		|| gcloud artifacts repositories create $(REPO) --repository-format=docker --location=$(REGION) --project=$(PROJECT)

deploy: ## Build and deploy to Cloud Run
	@echo ""
	@echo "--- Deploying Social Arb to Cloud Run ---"
	@echo ""
	gcloud builds submit --config deploy/cloudbuild.yaml --project=$(PROJECT) --substitutions=SHORT_SHA=$$(git rev-parse --short HEAD)
	@echo ""
	@echo "LIVE: $$(gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION) --format='value(status.url)')"

build: ## Build Docker image locally
	docker build -t $(SERVICE) .

run-local: ## Run locally with docker-compose on port 8000
	docker compose up --build

open: ## Open live app in browser
	@open "$$(gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION) --format='value(status.url)')"

url: ## Print the live URL
	@gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION) --format="value(status.url)"

logs: ## Show last 50 log lines
	gcloud run services logs read $(SERVICE) --region=$(REGION) --project=$(PROJECT) --limit=50

logs-follow: ## Stream logs live
	gcloud beta run services logs tail $(SERVICE) --region=$(REGION) --project=$(PROJECT)

status: ## Show service status
	gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION)

health: ## Hit the health endpoint
	@curl -s "$$(gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION) --format='value(status.url)')/api/v1/health" | python3 -m json.tool

env-set: ## Set env var: make env-set KEY=X VAL=Y
	gcloud run services update $(SERVICE) --region=$(REGION) --project=$(PROJECT) --update-env-vars="$(KEY)=$(VAL)"

env-list: ## List current env vars
	gcloud run services describe $(SERVICE) --project=$(PROJECT) --region=$(REGION) --format="yaml(spec.template.spec.containers[0].env)"

teardown: ## Delete service + registry (destructive!)
	@echo "This will delete the Cloud Run service and Artifact Registry."
	@read -p "Type yes to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	-gcloud run services delete $(SERVICE) --region=$(REGION) --project=$(PROJECT) --quiet
	-gcloud artifacts repositories delete $(REPO) --location=$(REGION) --project=$(PROJECT) --quiet
	@echo "Teardown complete."

clean: ## Remove local Docker images
	-docker rmi $(SERVICE) 2>/dev/null
	@echo "Local images cleaned."

# -- IAM (added by deployment fix) --
PROJECT_NUM  := 358461657718
CB_SA        := $(PROJECT_NUM)@cloudbuild.gserviceaccount.com
COMPUTE_SA   := $(PROJECT_NUM)-compute@developer.gserviceaccount.com

iam: ## Grant Cloud Build IAM roles for deployment
	@echo "Granting IAM roles to Cloud Build SA..."
	gcloud projects add-iam-policy-binding $(PROJECT) --member="serviceAccount:$(CB_SA)" --role="roles/run.admin" --quiet
	gcloud projects add-iam-policy-binding $(PROJECT) --member="serviceAccount:$(CB_SA)" --role="roles/iam.serviceAccountUser" --quiet
	gcloud projects add-iam-policy-binding $(PROJECT) --member="serviceAccount:$(CB_SA)" --role="roles/artifactregistry.writer" --quiet
	gcloud projects add-iam-policy-binding $(PROJECT) --member="serviceAccount:$(CB_SA)" --role="roles/storage.admin" --quiet
	gcloud run services add-iam-policy-binding $(SERVICE) --region=$(REGION) --member="allUsers" --role="roles/run.invoker" --project=$(PROJECT) --quiet 2>/dev/null || true
	@echo "IAM roles granted."
