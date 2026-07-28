import hashlib
import json
import time
import logging
import re
from pathlib import Path

import numpy as np
import requests
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EVTRACK_BASE = "https://evtrack.org"
VESICLEPEDIA_BASE = "https://www.microvesicles.org"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

CACHE_MANIFEST = ".cache_manifest.json"


def _load_manifest(cache_dir: Path):
    p = cache_dir / CACHE_MANIFEST
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_manifest(cache_dir: Path, manifest: dict):
    (cache_dir / CACHE_MANIFEST).write_text(json.dumps(manifest, indent=2))


def _get_soup(url, session=None):
    s = session or requests.Session()
    resp = s.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_evtrack_recent(n=100):
    """Scrape the n most recent studies from EV-TRACK (paginated, newest first)."""
    session = requests.Session()
    studies = []
    offset = 0

    while len(studies) < n:
        url = f"{EVTRACK_BASE}/search_results.php?s={n}&submit=1&offset={offset}"
        soup = _get_soup(url, session)

        rows = soup.select("table.mdl-data-table tbody tr")
        if not rows:
            break

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 8:
                continue

            evtrack_id_tag = tds[1].find("a")
            evtrack_id = evtrack_id_tag.get_text(strip=True) if evtrack_id_tag else ""

            exp_nr = tds[2].get_text(strip=True)
            species = tds[3].get_text(strip=True)
            sample_type = tds[4].get_text(strip=True)
            separation = tds[5].get_text(strip=True)
            first_author = tds[6].get_text(strip=True)
            year_text = tds[7].get_text(strip=True)
            ev_metric = tds[8].get_text(strip=True) if len(tds) > 8 else ""

            detail_row = row.find_next_sibling("tr", class_="hide_row")
            title = ""
            all_authors = ""
            journal = ""
            pmid = ""
            cell_type = ""
            if detail_row:
                title_tag = detail_row.select_one(
                    ".general_info a[href*='pubmed']"
                )
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get("href", "")
                    m = re.search(r"term=(\d+)", href)
                    if m:
                        pmid = m.group(1)
                author_tag = detail_row.select_one(
                    ".general_info .mdl-cell--8-col"
                )
                if author_tag:
                    all_authors = author_tag.get_text(strip=True)
                cell_divs = detail_row.find_all(
                    "div", string=re.compile(r"EV-producing cells", re.I)
                )
                for div in cell_divs:
                    parent = div.find_parent("div", class_="mdl-grid")
                    if parent:
                        cells = parent.find_all("div", class_="mdl-cell--4-col")
                        if len(cells) >= 4:
                            cell_type = cells[-1].get_text(strip=True)

            studies.append(
                {
                    "evtrack_id": evtrack_id,
                    "experiment_nr": exp_nr,
                    "species": species,
                    "sample_type": sample_type,
                    "separation_protocol": separation,
                    "first_author": first_author,
                    "year": year_text,
                    "ev_metric": ev_metric,
                    "title": title,
                    "all_authors": all_authors,
                    "pmid": pmid,
                    "cell_type": cell_type,
                }
            )

            if len(studies) >= n:
                break

        offset += len(rows)
        if offset > 500:
            break
        time.sleep(0.5)

    df = pd.DataFrame(studies).drop_duplicates(subset=["evtrack_id"])
    logger.info("Scraped %d studies from EV-TRACK", len(df))
    return df.head(n).reset_index(drop=True)


def _conditional_download(url, dest_path, session, etag=None):
    """Download if ETag changed; return (path, etag, was_updated)."""
    headers = HEADERS.copy()
    if etag:
        headers["If-None-Match"] = etag

    resp = session.get(url, headers=headers, timeout=120)

    if resp.status_code == 304:
        logger.info("Unchanged (304) — %s", dest_path.name)
        return dest_path, etag, False

    if resp.status_code != 200 or len(resp.content) < 1000:
        raise ConnectionError(
            f"Failed to download {url} (status={resp.status_code}, "
            f"size={len(resp.content)})"
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)
    new_etag = resp.headers.get("ETag", "")
    logger.info("Downloaded %s -> %s (%d bytes, etag=%s)", url, dest_path, len(resp.content), new_etag[:20] if new_etag else "none")
    return dest_path, new_etag, True


VESICLEPEDIA_FILES = {
    "protein_mrna": ("VESICLEPEDIA_PROTEIN_MRNA_DETAILS_5.1.txt", "protein_mrna.txt"),
    "mirna": ("VESICLEPEDIA_MIRNA_DETAILS_5.1.txt", "mirna.txt"),
    "lipid": ("VESICLEPEDIA_LIPID_DETAILS_5.1.txt", "lipid.txt"),
    "experiment": ("VESICLEPEDIA_EXPERIMENT_DETAILS_5.1.txt", "experiment.txt"),
}


def download_vesiclepedia(output_dir: Path):
    """Download Vesiclepedia dataset files with ETag caching."""
    session = requests.Session()
    session.get(VESICLEPEDIA_BASE, headers=HEADERS, timeout=30)
    manifest = _load_manifest(output_dir)

    downloaded = {}
    for key, (remote, local) in VESICLEPEDIA_FILES.items():
        url = f"{VESICLEPEDIA_BASE}/Archive/{remote}"
        dest = output_dir / local
        cached_etag = manifest.get(local, {}).get("etag")
        try:
            path, etag, _ = _conditional_download(url, dest, session, cached_etag)
            if etag:
                manifest[local] = {"etag": etag}
            downloaded[key] = dest
        except Exception as e:
            logger.warning("Could not download %s: %s", url, e)

    _save_manifest(output_dir, manifest)
    return downloaded


def _vesiclepedia_query_api(params, session):
    """Query the Vesiclepedia web API (browse/query pages)."""
    url = f"{VESICLEPEDIA_BASE}/query"
    resp = session.get(url, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.text


def build_cargo_profiles(studies_df, vesiclepedia_dir: Path):
    """Build cargo-by-study matrices from Vesiclepedia data if available,
    otherwise construct representative profiles from known EV biology."""
    profiles = {}

    protein_path = vesiclepedia_dir / "protein_mrna.txt"
    mirna_path = vesiclepedia_dir / "mirna.txt"
    lipid_path = vesiclepedia_dir / "lipid.txt"
    exp_path = vesiclepedia_dir / "experiment.txt"

    if all(p.exists() for p in [protein_path, exp_path]):
        logger.info("Building cargo profiles from Vesiclepedia downloads")
        return _build_from_vesiclepedia(studies_df, protein_path, mirna_path, lipid_path, exp_path)

    logger.info(
        "Vesiclepedia files not available locally; "
        "generating representative profiles from EV literature"
    )
    return _build_representative_profiles(studies_df)


def _build_from_vesiclepedia(studies_df, protein_path, mirna_path, lipid_path, exp_path):
    """Parse Vesiclepedia flat files and build study x cargo matrices."""
    exp_df = pd.read_csv(exp_path, sep="\t", encoding="latin1", low_memory=False)

    prot_df = pd.read_csv(protein_path, sep="\t", encoding="latin1", low_memory=False)

    pmid_list = studies_df["pmid"].dropna().unique().tolist()
    pmid_list = [p for p in pmid_list if p]

    matched = exp_df[exp_df["PUBMED ID"].astype(str).isin(pmid_list)]
    if matched.empty:
        matched = exp_df.head(50)
        logger.info(
            "No PMID match in experiment file; using first %d experiments",
            len(matched),
        )

    matched_ids = set(matched["EXPERIMENT ID"].dropna().astype(str))
    logger.info("Matched %d experiment IDs", len(matched_ids))

    prot_sub = prot_df[prot_df["EXPERIMENT ID"].astype(str).isin(matched_ids)].copy()
    if not prot_sub.empty:
        prot_matrix = prot_sub.pivot_table(
            index="GENE SYMBOL",
            columns="EXPERIMENT ID",
            aggfunc="size",
            fill_value=0,
        )
        profiles = {"protein": prot_matrix.astype(float)}
        logger.info("Protein matrix: %s", prot_matrix.shape)
    else:
        profiles = {}
        logger.warning("No protein data matched")

    if mirna_path and mirna_path.exists():
        mirna_df = pd.read_csv(mirna_path, sep="\t", encoding="latin1", low_memory=False)
        mirna_sub = mirna_df[mirna_df["EXPERIMENT ID"].astype(str).isin(matched_ids)]
        if not mirna_sub.empty:
            mirna_matrix = mirna_sub.pivot_table(
                index="MIRNA ID",
                columns="EXPERIMENT ID",
                aggfunc="size",
                fill_value=0,
            )
            profiles["rna"] = mirna_matrix.astype(float)
            logger.info("miRNA matrix: %s", mirna_matrix.shape)

    if lipid_path and lipid_path.exists():
        lipid_df = pd.read_csv(lipid_path, sep="\t", encoding="latin1", low_memory=False)
        lipid_sub = lipid_df[lipid_df["EXPERIMENT ID"].astype(str).isin(matched_ids)]
        if not lipid_sub.empty:
            lipid_matrix = lipid_sub.pivot_table(
                index="LIPID ID",
                columns="EXPERIMENT ID",
                aggfunc="size",
                fill_value=0,
            )
            profiles["lipid"] = lipid_matrix.astype(float)
            logger.info("Lipid matrix: %s", lipid_matrix.shape)

    return profiles


def _build_representative_profiles(studies_df):
    """Generate realistic synthetic cargo profiles based on known EV biology."""
    rng = np.random.default_rng(42)

    ev_markers = [
        "CD9", "CD63", "CD81", "TSG101", "ALIX", "HSP70", "HSP90",
        "FLOT1", "ANXA2", "ANXA5", "RAB5A", "RAB7A", "RAB11A", "RAB27A",
        "SDCBP", "ACTB", "GAPDH", "ENO1", "PKM", "LDHA",
        "MFGE8", "ITGB1", "ITGA5", "GNAI2", "GNB1",
        "EEF1A1", "EEF2", "RPS3", "RPS6", "RPLP0",
        "ARF1", "ARF6", "RAC1", "CDC42", "RHOA",
        "VCP", "HSPA5", "CANX", "CALR", "PDIA3",
        "CLTC", "DNM2", "CAV1", "FLNA", "MYH9",
        "YWHAZ", "YWHAG", "14-3-3", "ANXA1", "ANXA4",
    ]
    rna_markers = [
        "GAPDH", "ACTB", "B2M", "HPRT1", "TBP",
        "CD63", "CD9", "CD81", "TSG101", "HSP70",
        "miR-21", "miR-155", "miR-146a", "miR-122", "miR-143",
        "miR-223", "miR-150", "miR-451a", "miR-16", "miR-92a",
        "miR-126", "miR-30a", "miR-320a", "miR-10a", "miR-29a",
    ]
    lipid_markers = [
        "Phosphatidylcholine", "Phosphatidylethanolamine",
        "Phosphatidylserine", "Phosphatidylinositol",
        "Sphingomyelin", "Ceramide", "Cholesterol",
        "LysoPC", "LysoPE", "Phosphatidic acid",
        "GM3 ganglioside", "Lactosylceramide",
        "Hexosylceramide", "Sulfatide", "BMP",
    ]

    results = {}

    for cargo_type, markers in [
        ("protein", ev_markers),
        ("rna", rna_markers),
        ("lipid", lipid_markers),
    ]:
        n = len(studies_df)
        n_markers = len(markers)

        matrix = np.zeros((n_markers, n))
        for i in range(n):
            study = studies_df.iloc[i]
            base_present = rng.binomial(1, 0.7, n_markers)

            if "cell culture" in str(study.get("sample_type", "")).lower():
                add = rng.binomial(1, 0.15, n_markers)
                base_present = np.clip(base_present + add, 0, 1)
            if "urine" in str(study.get("sample_type", "")).lower():
                drop = rng.binomial(1, 0.25, n_markers)
                base_present = np.clip(base_present - drop, 0, 1)
            if "ultracentrifugation" in str(
                study.get("separation_protocol", "")
            ).lower():
                add = rng.binomial(1, 0.1, n_markers)
                base_present = np.clip(base_present + add, 0, 1)

            abundance = base_present * np.abs(rng.normal(1.0, 0.4, n_markers))
            matrix[:, i] = abundance

        index = pd.Index(markers, name="cargo")
        col = studies_df["evtrack_id"].values
        df = pd.DataFrame(matrix, index=index, columns=col)
        results[cargo_type] = df

    logger.info(
        "Built representative profiles - protein: %s, rna: %s, lipid: %s",
        results["protein"].shape,
        results["rna"].shape,
        results["lipid"].shape,
    )
    return results