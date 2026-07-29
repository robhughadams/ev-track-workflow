#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export CLOUDSDK_PYTHON=/home/userland/.local/share/uv/python/cpython-3.13-linux-aarch64-gnu/bin/python3.13
GCLOUD=/home/userland/.local/google-cloud-sdk/bin/gcloud

PROJECT_ID="project-9d4cecdb-b284-47c1-917"
REGION="europe-west4"
REPO="ev-track-repo"
IMAGE="europe-west4-docker.pkg.dev/$PROJECT_ID/ev-track-repo/ev-track-workflow:latest"
JOB_NAME="ev-track-job"

echo "=== EV Track Workflow — Deploy to GCP ==="

# --------------------------------------------------
# Step 1: Check gcloud
# --------------------------------------------------
if ! $GCLOUD auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
    echo "Not authenticated. Starting auth flow..."
    echo ""
    echo "1. In Termux, run:  nc -l -p 9999 -w 5 | tee /tmp/gcloud_url.txt | xargs -r termux-open-url"
    echo "   (the pipe through tee shows the URL so you can click it manually too)"
    echo ""
    mkdir -p /tmp
    $SCRIPT_DIR/gcloud_auth.exp 2>&1
    echo ""
    if ! $GCLOUD auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
        echo "ERROR: Auth failed."
        exit 1
    fi
    echo "Authenticated as: $($GCLOUD auth list --filter=status:ACTIVE --format='value(account)')"
fi

$GCLOUD config set project "$PROJECT_ID"
$GCLOUD config set compute/region "$REGION"
echo "Project: $PROJECT_ID  Region: $REGION"

# --------------------------------------------------
# Step 2: Enable APIs
# --------------------------------------------------
echo ""
echo "--- Enabling APIs ---"
$GCLOUD services enable artifactregistry.googleapis.com run.googleapis.com cloudbuild.googleapis.com

# --------------------------------------------------
# Step 3: Artifact Registry repo
# --------------------------------------------------
echo ""
echo "--- Artifact Registry ---"
if $GCLOUD artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1; then
    echo "Repo $REPO already exists"
else
    $GCLOUD artifacts repositories create "$REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="EV Track Workflow Docker images"
    echo "Created repo $REPO"
fi

# --------------------------------------------------
# Step 4: Build and push via Cloud Build
# --------------------------------------------------
echo ""
echo "--- Building & pushing via Cloud Build ---"
cd "$PROJECT_DIR"
$GCLOUD builds submit --tag "$IMAGE" --timeout=30m

# --------------------------------------------------
# Step 5: Create / update Cloud Run job
# --------------------------------------------------
echo ""
echo "--- Cloud Run Job ---"
if $GCLOUD beta run jobs describe "$JOB_NAME" --region="$REGION" >/dev/null 2>&1; then
    echo "Updating existing job..."
    $GCLOUD beta run jobs update "$JOB_NAME" \
        --image="$IMAGE" \
        --region="$REGION" \
        --memory=4Gi \
        --cpu=2 \
        --max-retries=0 \
        --task-timeout=30m
else
    echo "Creating new job..."
    $GCLOUD beta run jobs create "$JOB_NAME" \
        --image="$IMAGE" \
        --region="$REGION" \
        --memory=4Gi \
        --cpu=2 \
        --max-retries=0 \
        --task-timeout=30m
fi

echo ""
echo "=== Deploy complete ==="
echo "Run job:  $GCLOUD beta run jobs execute $JOB_NAME --region=$REGION"
