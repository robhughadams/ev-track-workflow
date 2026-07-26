# Deployment

## Docker

The project includes a `Dockerfile` for containerised execution:

```dockerfile
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --prerelease=allow --no-dev --frozen
COPY . .
CMD ["uv", "run", "run_workflow.py"]
```

Key points:
- Uses `python:3.13-slim` as the base image.
- Copies `uv` from the official Astral image to avoid installing it manually.
- Dependencies are installed with `--prerelease=allow` to handle `llvmlite`/`numba`
  wheel availability for Python 3.13.
- The `.dockerignore` excludes `.venv`, `.git`, data files, and `__pycache__`
  to keep the build context small.

### Build locally

```bash
docker build -t ev-track-workflow .
```

## Google Cloud Run

### Prerequisites

- Google Cloud SDK installed and authenticated (`gcloud init` completed).
- Project with billing enabled.
- Required APIs: Artifact Registry, Cloud Run, Cloud Build.

### 1 — Enable APIs

```bash
gcloud services enable artifactregistry.googleapis.com \
  run.googleapis.com cloudbuild.googleapis.com
```

### 2 — Create Artifact Registry Repository

```bash
gcloud artifacts repositories create ev-track-repo \
  --repository-format=docker \
  --location=europe-west4 \
  --description="EV Track Workflow Docker images"
```

### 3 — Authenticate Docker

```bash
gcloud auth configure-docker europe-west4-docker.pkg.dev
```

### 4 — Build and Push

```bash
IMAGE="europe-west4-docker.pkg.dev/\$(gcloud config get-value project)/ev-track-repo/ev-track-workflow:latest"

docker build -t "$IMAGE" .
docker push "$IMAGE"
```

### 5 — Create Cloud Run Job

```bash
gcloud beta run jobs create ev-track-job \
  --image="$IMAGE" \
  --region=europe-west4 \
  --memory=4Gi \
  --cpu=2 \
  --max-retries=0 \
  --task-timeout=30m
```

### 6 — Execute

```bash
gcloud beta run jobs execute ev-track-job --region=europe-west4
```

### View Logs

```bash
gcloud beta run jobs executions list --region=europe-west4
gcloud beta run jobs logs read --region=europe-west4
```

## Project Configuration

### Google Cloud Project

- **Project ID**: `project-9d4cecdb-b284-47c1-917`
- **Default zone**: `europe-west4-a`
- **Artifact Registry repo**: `ev-track-repo` in `europe-west4`
- **Cloud Run region**: `europe-west4`
