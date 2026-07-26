# EV Track Workflow — Agent Instructions

## Project Overview

A containerised EV cargo analysis pipeline that:

1. **Scrapes** EV‑TRACK for the 100 most recent studies (titles, PMIDs, experimental IDs).
2. **Downloads** Vesiclepedia cargo datasets (protein, RNA, lipid) — falls back to representative EV biology profiles if remote download fails (Cloudflare protection).
3. **Builds** cargo-by-study matrices (molecules × studies).
4. **Normalises** — UniProt/Ensembl/LIPID MAPS ID mapping, log1p transform, kNN imputation, unit‑variance scaling.
5. **Analyses** — PCA, UMAP (combined multi‑cargo embedding), PLS‑DA, hierarchical clustering.
6. **Visualises** — PCA scores/loadings, dendrograms, heatmaps (top 200), combined UMAP scatter.
7. **Summarises** — text report saved to `output/summary.txt`.

## Package Management

- **Always use `uv`** — never pip or conda.
  - `uv venv` to create a virtual environment.
  - `uv add <package>` to add dependencies.
  - `uv run <script.py>` to run scripts.
- The project uses **Python ≥3.13** and a locked environment (`uv.lock`).

## Debian / Docker Python Caveats

- `umap-learn` depends on `llvmlite`/`numba`, which often lack stable PyPI wheels for Python 3.13.
- **Preferred fix**: `uv add --prerelease=allow` — pre‑release wheels of `llvmlite`/`numba` are compiled for Python 3.13.
- The Dockerfile (`python:3.13-slim` base) uses `uv sync --prerelease=allow --no-dev --frozen` to handle this.

## Project Structure

```
.
├── AGENTS.md                 # This file
├── Dockerfile                # Container image (python:3.13-slim + uv)
├── .dockerignore             # Excludes .venv, .git, data, __pycache__
├── pyproject.toml            # Project config with dependencies and entry point
├── uv.lock                   # Locked dependency versions
├── run_workflow.py           # Main orchestrator (7 steps)
├── main.py                   # Thin wrapper: `from run_workflow import main`
├── evtrack_workflow/
│   ├── __init__.py
│   ├── scraper.py            # EV‑TRACK scraping + Vesiclepedia download
│   ├── normalizer.py         # ID mapping, log1p, kNN imputation, UV scaling
│   └── analyzer.py           # PCA, UMAP, PLS‑DA, clustering, heatmaps, summary
└── output/                   # Generated CSVs, PNGs, summary.txt
```

## Running Locally

```bash
uv run run_workflow.py
```

Or use the entry point:

```bash
uv run ev-track-workflow
```

## Cloud Run Deployment

1. **Build and push**:
   ```bash
   IMAGE="europe-west4-docker.pkg.dev/project-9d4cecdb-b284-47c1-917/ev-track-repo/ev-track-workflow:latest"
   docker build -t "$IMAGE" .
   docker push "$IMAGE"
   ```

2. **Create job**:
   ```bash
   gcloud beta run jobs create ev-track-job \
     --image="$IMAGE" \
     --region=europe-west4 \
     --memory=4Gi \
     --cpu=2 \
     --max-retries=0 \
     --task-timeout=30m
   ```

3. **Execute**:
   ```bash
   gcloud beta run jobs execute ev-track-job --region=europe-west4
   ```

## Key Conventions

- **Sub‑agent efficiency**: Delegate research, code writing, debugging, and review to sub‑agents (Task tool or @mentions). Keep the main loop lean.
- **Output directory**: `output/data/` for CSVs, `output/plots/` for PNGs, `output/summary.txt` for the text report.
- **Error handling**: Each pipeline step in `run_workflow.py` is wrapped in try/except so a single failed cargo type doesn't halt the whole workflow.
- **Git remote**: `https://github.com/robhughadams/ev-track-workflow`
