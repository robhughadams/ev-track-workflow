import logging

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_PROTEIN_MAP = {
    "CD9": "P21926",
    "CD63": "P08962",
    "CD81": "P60033",
    "TSG101": "Q99816",
    "ALIX": "Q9W710",
    "HSP70": "P0DMV8",
    "HSP90": "P07900",
    "GAPDH": "P04406",
    "ACTB": "P60709",
    "CD14": "P08571",
    "CD41": "P08514",
    "CD45": "P08575",
    "CD47": "Q08722",
    "CD55": "P08174",
    "CD59": "P13987",
    "CD73": "P21589",
    "CD82": "P27701",
    "CD9L1": "Q9H490",
    "CD151": "P48509",
    "CD1a": "P06126",
    "CD1b": "P29016",
    "CD11a": "P20701",
    "CD11b": "P11215",
    "CD11c": "P20702",
    "CD18": "P05107",
    "CD31": "P16284",
    "CD36": "P16671",
    "CD40": "P25942",
    "CD44": "P16070",
    "CD49c": "P26006",
    "CD49d": "P13612",
    "CD49e": "P08648",
    "CD49f": "P23229",
    "CD61": "P05106",
    "CD62L": "P14151",
    "CD62P": "P16109",
    "CD63L": "Q9Y3Q3",
    "CD66": "P13688",
    "CD98": "P08195",
    "CD105": "P17813",
    "CD106": "P19320",
    "CD147": "P35613",
    "CD163": "Q86VB7",
    "CD206": "P22897",
    "ACTN1": "P12814",
    "ACTN4": "O43707",
    "ANXA1": "P04083",
    "ANXA2": "P07355",
    "ANXA5": "P08758",
    "ANXA6": "P08133",
    "EEF1A1": "P68104",
    "EEF2": "P13639",
    "EZR": "P15311",
    "FLOT1": "O75955",
    "FLOT2": "Q14254",
    "RAB5A": "P20339",
    "RAB7A": "P51149",
    "RAB11A": "P62491",
    "RAB27A": "Q14966",
    "SDCBP": "O00560",
    "VPS4A": "Q9UN37",
    "VPS4B": "O75351",
    "LAMP1": "P11279",
    "LAMP2": "P13473",
    "MFGE8": "Q08431",
    "ICAM1": "P05362",
    "VCAM1": "P19320",
    "ITGB1": "P05556",
    "ITGA5": "P08648",
    "CAV1": "Q03135",
    "CAV2": "Q51636",
    "CLTC": "Q00610",
    "PDCD6IP": "Q8WUM4",
    "LGALS3BP": "Q08380",
    "LGALS1": "P09382",
    "LGALS3": "P17931",
    "FN1": "P02751",
    "MYH9": "P35579",
    "MYL6": "P60660",
    "PKM": "P14618",
    "ENO1": "P06733",
    "LDHA": "P00338",
    "PGK1": "P00558",
    "TPI1": "P60174",
    "SLC3A2": "P08195",
    "BSG": "P35613",
}

_RNA_MAP = {
    "hsa-miR-21-5p": "MIMAT0000076",
    "hsa-miR-155-5p": "MIMAT0000646",
    "hsa-miR-146a-5p": "MIMAT0000449",
    "hsa-miR-122-5p": "MIMAT0000421",
    "hsa-miR-210-3p": "MIMAT0000267",
    "hsa-miR-16-5p": "MIMAT0000069",
    "hsa-miR-143-3p": "MIMAT0000435",
    "hsa-miR-145-5p": "MIMAT0000437",
    "hsa-miR-200b-3p": "MIMAT0000318",
    "hsa-miR-200c-3p": "MIMAT0000617",
    "hsa-miR-141-3p": "MIMAT0000432",
    "hsa-miR-429": "MIMAT0001536",
    "hsa-miR-92a-3p": "MIMAT0000092",
    "hsa-miR-126-3p": "MIMAT0000445",
    "hsa-miR-30a-5p": "MIMAT0000087",
}


def standardize_protein_ids(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to standardize_protein_ids")
        return df
    if "cargo" not in df.index.names:
        logger.warning("DataFrame index does not contain 'cargo'")
        return df
    df = df.copy()
    df["uniprot_id"] = df.index.map(_PROTEIN_MAP.get)
    logger.info(
        "Added uniprot_id column with %d mapped entries",
        df["uniprot_id"].notna().sum(),
    )
    return df


def standardize_rna_ids(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to standardize_rna_ids")
        return df
    if "cargo" not in df.index.names:
        logger.warning("DataFrame index does not contain 'cargo'")
        return df
    df = df.copy()
    df["ensembl_id"] = df.index.map(_RNA_MAP.get)
    logger.info(
        "Added ensembl_id column with %d mapped entries",
        df["ensembl_id"].notna().sum(),
    )
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to remove_duplicates")
        return df
    before = len(df)
    df = df.drop_duplicates(keep="first")
    after = len(df)
    if after < before:
        logger.info("Removed %d duplicate row(s)", before - after)
    return df


def knn_impute(df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to knn_impute")
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric columns to impute")
        return df
    imputer = KNNImputer(n_neighbors=n_neighbors)
    imputed = imputer.fit_transform(df[numeric_cols])
    result = df.copy()
    result[numeric_cols] = imputed
    logger.info("Applied KNN imputation (n_neighbors=%d)", n_neighbors)
    return result


def unit_variance_scale(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to unit_variance_scale")
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric columns to scale")
        return df
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df[numeric_cols])
    result = df.copy()
    result[numeric_cols] = scaled
    logger.info("Applied unit variance scaling to %d column(s)", len(numeric_cols))
    return result


def normalize_dataset(df: pd.DataFrame, cargo_type: str) -> pd.DataFrame:
    if df.empty:
        logger.warning("Empty DataFrame passed to normalize_dataset")
        return df
    if cargo_type == "protein":
        logger.info("Step 1/4: standardize_protein_ids")
        df = standardize_protein_ids(df)
    elif cargo_type == "rna":
        logger.info("Step 1/4: standardize_rna_ids")
        df = standardize_rna_ids(df)
    else:
        logger.warning("Unknown cargo_type '%s', skipping ID standardization", cargo_type)
    logger.info("Step 2/4: remove_duplicates")
    df = remove_duplicates(df)
    logger.info("Step 3/4: knn_impute")
    df = knn_impute(df)
    logger.info("Step 4/4: unit_variance_scale")
    df = unit_variance_scale(df)
    logger.info("Normalization complete")
    return df
