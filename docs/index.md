# EV Track Workflow

A containerised extracellular vesicle (EV) cargo analysis pipeline that scrapes
EV‑TRACK for the 100 most recent studies, downloads Vesiclepedia cargo datasets
(or falls back to representative EV biology profiles), normalises protein/RNA/lipid
matrices, performs multivariate chemometrics (PCA, UMAP, PLS‑DA, hierarchical
clustering), and generates publication‑ready visualisations and a text summary.

## Quick Start

```bash
# Run locally (requires Python ≥3.13 and uv)
uv run run_workflow.py

# Or using the entry point
uv run ev-track-workflow
```

All output is written to `output/` — CSVs in `output/data/`, PNG plots in
`output/plots/`, and a text report in `output/summary.txt`.

## Project Status

- **v0.2.0** — Full pipeline end‑to‑end tested.
- Docker image built and pushed to Google Artifact Registry.
- Ready for Cloud Run job execution (100‑study workload).

## License

AGPLv3 — see `LICENSE` in the repository root.
Copyright (C) 2026 Robert Hugh Adams.
