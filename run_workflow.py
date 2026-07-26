from pathlib import Path
import logging

from evtrack_workflow.scraper import scrape_evtrack_recent, download_vesiclepedia, build_cargo_profiles
from evtrack_workflow.normalizer import normalize_dataset
from evtrack_workflow.analyzer import perform_pca, perform_plsda, hierarchical_clustering, plot_heatmap, generate_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = OUTPUT_DIR / "data"
PLOTS_DIR = OUTPUT_DIR / "plots"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Step 1: Scraping EV-TRACK for the 50 most recent studies ...")
    try:
        studies_df = scrape_evtrack_recent(n=50)
    except Exception as e:
        logger.warning("Scraping failed: %s", e)
        return

    logger.info("Step 2: Downloading Vesiclepedia cargo datasets ...")
    try:
        downloaded = download_vesiclepedia(DATA_DIR)
    except Exception as e:
        logger.warning("Download failed (proceeding without remote data): %s", e)
        downloaded = {}

    logger.info("Step 3: Building cargo-by-study profiles ...")
    try:
        profiles = build_cargo_profiles(studies_df, DATA_DIR)
    except Exception as e:
        logger.warning("Profile building failed: %s", e)
        return

    logger.info("Step 4: Normalising datasets ...")
    pca_results = {}
    cluster_results = {}
    for cargo_type in list(profiles.keys()):
        try:
            profile_df = profiles[cargo_type]
            normalized_df = normalize_dataset(profile_df, cargo_type)
            out_path = DATA_DIR / f"{cargo_type}_normalized.csv"
            normalized_df.to_csv(out_path)
            profiles[cargo_type] = normalized_df
        except Exception as e:
            logger.warning("Normalisation failed for %s: %s", cargo_type, e)

    logger.info("Step 5/6: Chemometric analysis and plots ...")
    for cargo_type in profiles:
        try:
            pca_results[cargo_type] = perform_pca(profiles[cargo_type], cargo_type, PLOTS_DIR)
        except Exception as e:
            logger.warning("PCA failed for %s: %s", cargo_type, e)

    for cargo_type in profiles:
        try:
            cluster_results[cargo_type] = hierarchical_clustering(
                profiles[cargo_type], cargo_type, PLOTS_DIR
            )
        except Exception as e:
            logger.warning("Hierarchical clustering failed for %s: %s", cargo_type, e)

    for cargo_type in profiles:
        try:
            plot_heatmap(profiles[cargo_type], cargo_type, PLOTS_DIR)
        except Exception as e:
            logger.warning("Heatmap failed for %s: %s", cargo_type, e)

    plsda_result = {}
    try:
        plsda_result = perform_plsda(profiles['protein'], studies_df, 'protein', PLOTS_DIR)
    except Exception as e:
        logger.warning("PLS-DA on protein profile failed: %s", e)

    logger.info("Step 7: Generating summary ...")
    try:
        generate_summary(profiles, pca_results, cluster_results, plsda_result, studies_df, OUTPUT_DIR)
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)

    logger.info("Done.")
    logger.info("Output files written to %s", OUTPUT_DIR)


if __name__ == '__main__':
    main()
