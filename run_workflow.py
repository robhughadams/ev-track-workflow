from pathlib import Path
import logging

from evtrack_workflow.scraper import scrape_evtrack_recent, download_vesiclepedia, build_cargo_profiles
from evtrack_workflow.normalizer import normalize_dataset
from evtrack_workflow.analyzer import (
    perform_pca, perform_plsda, hierarchical_clustering,
    plot_heatmap, perform_umap_combined, generate_summary,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = OUTPUT_DIR / "data"
PLOTS_DIR = OUTPUT_DIR / "plots"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Step 1: Scraping EV-TRACK for the 100 most recent studies ...")
    try:
        studies_df = scrape_evtrack_recent(n=100)
    except Exception as e:
        logger.warning("Scraping failed: %s", e)
        return

    logger.info("Step 2: Downloading Vesiclepedia cargo datasets ...")
    try:
        download_vesiclepedia(DATA_DIR)
    except Exception as e:
        logger.warning("Download failed (proceeding without remote data): %s", e)

    logger.info("Step 3: Building cargo-by-study matrices ...")
    try:
        profiles = build_cargo_profiles(studies_df, DATA_DIR)
    except Exception as e:
        logger.warning("Profile building failed: %s", e)
        return

    logger.info("Step 4: Cleaning and normalising datasets ...")
    normalized = {}
    for cargo_type in list(profiles.keys()):
        try:
            normalized[cargo_type] = normalize_dataset(profiles[cargo_type], cargo_type)
            out_path = DATA_DIR / f"{cargo_type}_normalized.csv"
            normalized[cargo_type].to_csv(out_path)
            logger.info("Saved %s", out_path)
        except Exception as e:
            logger.warning("Normalisation failed for %s: %s", cargo_type, e)

    logger.info("Step 5: Chemometric analysis ...")

    pca_results = {}
    for cargo_type in normalized:
        try:
            pca_results[cargo_type] = perform_pca(
                normalized[cargo_type], cargo_type, PLOTS_DIR
            )
        except Exception as e:
            logger.warning("PCA failed for %s: %s", cargo_type, e)

    logger.info("UMAP on combined multi-cargo profiles ...")
    umap_results = perform_umap_combined(normalized, studies_df, PLOTS_DIR)

    cluster_results = {}
    for cargo_type in normalized:
        try:
            cluster_results[cargo_type] = hierarchical_clustering(
                normalized[cargo_type], cargo_type, PLOTS_DIR
            )
        except Exception as e:
            logger.warning("Clustering failed for %s: %s", cargo_type, e)

    plsda_result = {}
    if 'protein' in normalized:
        try:
            plsda_result = perform_plsda(
                normalized['protein'], studies_df, 'protein', PLOTS_DIR
            )
        except Exception as e:
            logger.warning("PLS-DA failed: %s", e)

    logger.info("Step 6: Generating visualisations (top 200 heatmaps) ...")
    for cargo_type in normalized:
        try:
            plot_heatmap(normalized[cargo_type], cargo_type, PLOTS_DIR, top_n=200)
        except Exception as e:
            logger.warning("Heatmap failed for %s: %s", cargo_type, e)

    logger.info("Step 7: Generating summary ...")
    try:
        generate_summary(
            normalized, pca_results, cluster_results,
            plsda_result, umap_results, studies_df, OUTPUT_DIR,
        )
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)

    logger.info("Done. Output files in %s", OUTPUT_DIR)


if __name__ == '__main__':
    main()
