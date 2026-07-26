# Development

## Prerequisites

- Python ≥3.13
- `uv` (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Setup

```bash
git clone https://github.com/robhughadams/ev-track-workflow.git
cd ev-track-workflow
uv venv
uv sync
```

## Running

```bash
uv run run_workflow.py
```

The pipeline scrapes 100 studies, generates representative EV cargo profiles,
normalises, analyses, and writes output to `output/`.

## Testing

There is no formal test suite yet. To verify the pipeline works:

```bash
# Quick smoke test — scrape just 3 studies and run all steps
uv run python -c "
from evtrack_workflow.scraper import scrape_evtrack_recent, build_cargo_profiles
from evtrack_workflow.normalizer import normalize_dataset
from pathlib import Path
import tempfile

studies = scrape_evtrack_recent(3)
profiles = build_cargo_profiles(studies, Path('output/data'))
for ctype, mat in profiles.items():
    norm = normalize_dataset(mat, ctype)
    print(f'{ctype}: {norm.shape}')
"
```

## Project Structure

```
.
├── AGENTS.md                     # AI agent instructions for this repo
├── CHANGELOG.md                  # Release history
├── Dockerfile                    # Container image definition
├── LICENSE                       # AGPLv3
├── README.md                     # Project overview (empty — docs live in docs/)
├── __init__.py
├── .dockerignore                 # Files excluded from Docker build context
├── .gitignore
├── .python-version               # Python version for uv/pyenv
├── docs/                         # Documentation
│   ├── index.md                  # Overview and quick start
│   ├── pipeline.md               # Detailed pipeline step descriptions
│   ├── deployment.md             # Docker and Cloud Run deployment guide
│   ├── output.md                 # Output file descriptions
│   └── development.md            # This file
├── evtrack_workflow/
│   ├── __init__.py               # Package initialiser
│   ├── scraper.py                # EV‑TRACK scraping + Vesiclepedia download + profile builder
│   ├── normalizer.py             # ID mapping, log1p, kNN imputation, unit‑variance scaling
│   └── analyzer.py               # PCA, UMAP, PLS‑DA, clustering, heatmaps, summary
├── main.py                       # Thin entry point: `from run_workflow import main`
├── output/                       # Generated artefacts
│   ├── data/                     # Normalised CSVs + raw downloads
│   ├── plots/                    # PNG visualisations
│   └── summary.txt               # Text report
├── pyproject.toml                # Project metadata and dependencies
├── run_workflow.py               # Main orchestrator (7‑step pipeline)
└── uv.lock                       # Locked dependency versions
```

## Dependencies

Managed with `uv`. Key packages:

| Package | Purpose |
|---------|---------|
| `pandas` | Data manipulation and matrix construction |
| `numpy` | Numerical operations |
| `scikit-learn` | PCA, PLS‑DA, kNN imputation, StandardScaler |
| `umap-learn` | UMAP dimensionality reduction |
| `matplotlib` | Plotting |
| `seaborn` | Statistical visualisations (clustermap) |
| `scipy` | Hierarchical clustering |
| `beautifulsoup4` | HTML parsing for EV‑TRACK scraping |
| `requests` | HTTP downloads |
| `llvmlite` / `numba` | Transitive deps of `umap-learn` |

### Python 3.13 + umap-learn Caveat

`umap-learn` depends on `llvmlite`/`numba`, which lack stable PyPI wheels for
Python 3.13. The **preferred fix** is to install with `--prerelease=allow`:

```bash
uv add --prerelease=allow umap-learn
```

This pulls pre‑release wheels that are compiled for Python 3.13.

## Version History

- **v0.2.0** — Full pipeline: 100 studies, UMAP, log‑transform, top‑200 heatmaps,
  fixed clustering/summary, Dockerfile.
- **v0.1.0** — Initial pipeline: scrape, normalise, PCA/clustering.

## Git

- Remote: `https://github.com/robhughadams/ev-track-workflow`
- Branch: `main`
- Conventions: commit messages are concise, matching repo style.
