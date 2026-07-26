# Output

After a successful run, the `output/` directory contains:

## `output/data/`

| File | Description |
|------|-------------|
| `protein_normalized.csv` | Normalised protein matrix (~300 molecules × up to 49 studies). Rows indexed by UniProt ID, columns by EV‑TRACK study ID. Values are log1p‑transformed, kNN‑imputed, and unit‑variance scaled. |
| `lipid_normalized.csv` | Normalised lipid matrix. Often sparse (2×2 in practice) because Vesiclepedia lipid data is limited and may not overlap with scraped studies. |
| `experiment.txt` | Vesiclepedia experiment details (if download succeeded). |
| `protein_mrna.txt` | Vesiclepedia protein/mRNA dataset (if download succeeded). |
| `mirna.txt` | Vesiclepedia miRNA dataset (if download succeeded). |
| `lipid.txt` | Vesiclepedia lipid dataset (if download succeeded). |

## `output/plots/`

| File | Description |
|------|-------------|
| `protein_pca_scores.png` | PC1 vs PC2 score plot for the protein matrix, with study ID annotations and variance explained labels. |
| `protein_pca_loadings.png` | PC1 vs PC2 loadings plot with the top 10 most influential molecules annotated. |
| `lipid_pca_scores.png` | Same as above for the lipid matrix (may show minimal variance if data is sparse). |
| `lipid_pca_loadings.png` | Loadings plot for the lipid PCA. |
| `protein_dendrogram.png` | Hierarchical clustering dendrogram for proteins (correlation distance, average linkage). |
| `lipid_dendrogram.png` | Dendrogram for lipids. |
| `protein_heatmap.png` | Clustered heatmap of the top 200 most variable proteins (z‑score normalised, diverging colour map). |
| `lipid_heatmap.png` | Heatmap for the top 200 lipids (may be smaller if fewer lipids in the matrix). |
| `combined_umap.png` | UMAP embedding combining PCA scores from all cargo types (protein + RNA + lipid). Shows study IDs in a 2D UMAP space. |
| `protein_plsda_scores.png` | PLS‑DA score plot discriminating studies by isolation method (UC, SEC, Precipitation, Other). |

## `output/summary.txt`

A text report containing:

- Number of studies processed.
- Matrix dimensions and top 3 most variable molecules per cargo type.
- PCA explained variance ratios per cargo type.
- UMAP embedding metadata (studies embedded, cargo types combined).
- PLS‑DA discrimination results (isolation groups identified).
- Hierarchical clustering assignments — which studies group together, with
  the most common species per cluster.
- Biological interpretation paragraph with caveats.

## Example (from a 100‑study run with representative profiles)

```
EV-TRACK Extended Cargo Analysis Summary
==================================================

Number of studies processed: 100

Cargo Type Profiles
----------------------------------------

Protein:
  Matrix dimensions: 50 molecules x 100 studies
  Top 3 most variable: CD9, CD63, ALIX

RNA:
  Matrix dimensions: 25 molecules x 100 studies
  Top 3 most variable: GAPDH, miR-21, CD63

Lipid:
  Matrix dimensions: 15 molecules x 100 studies
  Top 3 most variable: Cholesterol, Phosphatidylcholine, Sphingomyelin
```
