# Pipeline

The workflow is orchestrated by `run_workflow.py` in seven sequential steps.
Each step is wrapped in try/except so a failure in one cargo type (e.g. sparse
lipid data) does not halt the entire pipeline.

## Step 1 — Scrape EV‑TRACK

**Module**: `evtrack_workflow.scraper.scrape_evtrack_recent(n=100)`

- Paginates through EV‑TRACK search results (`https://evtrack.org/search_results.php`)
  with a `User-Agent` header to avoid blocking.
- Extracts from each row: EV‑TRACK ID, experiment number, species, sample type,
  separation protocol, first author, year, EV metric.
- Expands detail rows to capture: title, all authors, PubMed ID (extracted from
  the PubMed link `term=` parameter), and EV‑producing cell type.
- Returns a DataFrame deduplicated by `evtrack_id`, limited to `n` studies.

## Step 2 — Download Vesiclepedia

**Module**: `evtrack_workflow.scraper.download_vesiclepedia(output_dir)`

- Attempts to download four dataset files from `https://www.microvesicles.org/Archive/`:
  - `VESICLEPEDIA_PROTEIN_MRNA_DETAILS_5.1.txt` → `protein_mrna.txt`
  - `VESICLEPEDIA_MIRNA_DETAILS_5.1.txt` → `mirna.txt`
  - `VESICLEPEDIA_LIPID_DETAILS_5.1.txt` → `lipid.txt`
  - `VESICLEPEDIA_EXPERIMENT_DETAILS_5.1.txt` → `experiment.txt`
- Vesiclepedia sits behind Cloudflare, so downloads often fail with a
  non‑200 status or truncated content. The pipeline logs a warning and
  continues without remote data — Step 3 will generate representative profiles.

## Step 3 — Build Cargo‑by‑Study Matrices

**Module**: `evtrack_workflow.scraper.build_cargo_profiles(studies_df, data_dir)`

Two code paths:

### Path A — Vesiclepedia files available
- Parses the experiment file, matches studies by `PUBMED ID` to Vesiclepedia
  `EXPERIMENT ID` values.
- Builds pivot tables (index = molecule identifier, columns = experiment ID,
  values = occurrence count) for protein, miRNA, and lipid datasets.
- Returns a dict of DataFrames: `{"protein": ..., "rna": ..., "lipid": ...}`.

### Path B — Representative profiles (fallback)
- Uses a curated list of 50 EV protein markers (tetraspanins CD9/CD63/CD81,
  ESCRT components TSG101/ALIX, Rab GTPases, annexins, heat‑shock proteins,
  cytoskeletal proteins, integrins, etc.).
- Uses 25 RNA markers (mRNAs and miRNAs commonly found in EVs).
- Uses 15 lipid markers (phospholipids, sphingolipids, cholesterol, etc.).
- Generates abundance values with biologically meaningful variation based on
  study metadata: cell‑culture samples get extra positives, urine samples get
  fewer positives, ultracentrifugation enriches certain markers.
- Uses a fixed random seed (`np.random.default_rng(42)`) for reproducibility.

## Step 4 — Normalise

**Module**: `evtrack_workflow.normalizer.normalize_dataset(df, cargo_type)`

Each cargo type is processed through a five‑stage pipeline:

1. **Standardise identifiers**: Maps index entries to canonical IDs
   - Protein: gene symbol → UniProt ID (`_PROTEIN_MAP`, ~120 entries)
   - RNA: miRBase name → Ensembl ID (`_RNA_MAP`, ~200 entries)
   - Lipid: common name → LIPID MAPS ID (`_LIPID_MAP`, ~30 entries)
2. **Remove duplicates**: Drops duplicate rows, keeping the first occurrence.
3. **Log transform**: Applies `log1p` (ln(1+x)) to all numeric columns.
4. **kNN impute**: Fills missing values using 5‑nearest‑neighbour imputation
   (`sklearn.impute.KNNImputer`).
5. **Unit‑variance scale**: Standardises each column to zero mean and unit
   variance (`sklearn.preprocessing.StandardScaler`).

The normalised matrix is saved to `output/data/{cargo_type}_normalized.csv`.

## Step 5 — Chemometric Analysis

### PCA

**Module**: `evtrack_workflow.analyzer.perform_pca(matrix_df, title, output_dir)`

- Transposes the matrix (studies as rows, molecules as columns).
- Computes up to 5 principal components.
- Generates two plots:
  - **Score plot**: PC1 vs PC2 with study ID annotations and variance % labels.
  - **Loadings plot**: PC1 vs PC2 with the top 10 most influential molecules
    annotated.

### UMAP (Combined Multi‑Cargo)

**Module**: `evtrack_workflow.analyzer.perform_umap_combined(normalized, metadata, output_dir)`

- For each cargo type, reduces the molecule space to top PCA scores (up to 10
  components).
- Intersects the study indices across all cargo types to find a common set.
- Concatenates the PCA score vectors and runs `umap.UMAP` (n_neighbors=10,
  min_dist=0.3).
- Saves a scatter plot with study ID annotations to `combined_umap.png`.

### PLS‑DA

**Module**: `evtrack_workflow.analyzer.perform_plsda(matrix_df, metadata, title, output_dir)`

- Merges the protein matrix with study metadata by `evtrack_id`.
- Groups studies by simplified isolation protocol (UC, SEC, Precipitation, Other).
- Fits a 2‑component `PLSRegression` model to discriminate isolation groups.
- Plots LV1 vs LV2 coloured by group and saves to `{title}_plsda_scores.png`.

### Hierarchical Clustering

**Module**: `evtrack_workflow.analyzer.hierarchical_clustering(matrix_df, title, output_dir)`

- Computes correlation distance (`pdist`) between studies.
- Performs average‑linkage hierarchical clustering (`scipy.cluster.hierarchy`).
- Saves a dendrogram to `{title}_dendrogram.png`.

## Step 6 — Heatmaps

**Module**: `evtrack_workflow.analyzer.plot_heatmap(matrix_df, title, output_dir, top_n=200)`

- Selects the top `top_n` (default 200) most variable molecules by variance.
- Generates a clustered heatmap (`seaborn.clustermap`) with z‑score
  normalisation, diverging colour map, and automatically sized figure.
- Saves to `{title}_heatmap.png`.

## Step 7 — Summary Report

**Module**: `evtrack_workflow.analyzer.generate_summary(...)`

Writes `output/summary.txt` with:

- Number of studies processed.
- Per‑cargo‑type matrix dimensions and top 3 most variable molecules.
- PCA explained variance ratios.
- UMAP embedding dimensions and cargo types combined.
- PLS‑DA discrimination results.
- Hierarchical clustering assignments with species annotation.
- Biological interpretation caveats.

## Error Handling Philosophy

Every pipeline step that operates per cargo type is wrapped in a
try/except block in `run_workflow.py`. This means:

- If the Vesiclepedia download fails, the pipeline proceeds with
  representative profiles.
- If normalisation fails for lipids (e.g. because the matrix is too sparse),
  protein and RNA analysis continue unaffected.
- If a plot cannot be generated (insufficient dimensions), the step logs a
  warning and moves on.
