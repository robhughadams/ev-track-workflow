import logging

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_PROTEIN_MAP = {
    "CD9": "P21926", "CD63": "P08962", "CD81": "P60033", "CD82": "P27701",
    "CD151": "P48509", "CD37": "P11049", "CD53": "P19397",
    "TSG101": "Q99816", "PDCD6IP": "Q8WUM4", "VPS4A": "Q9UN37", "VPS4B": "O75351",
    "CHMP4A": "Q9BY43", "CHMP4B": "Q9H444",
    "ALIX": "Q9W710", "HGS": "O14964", "STAM1": "Q92783",
    "RAB5A": "P20339", "RAB7A": "P51149", "RAB11A": "P62491", "RAB27A": "Q14966",
    "RAB27B": "O00194", "RAB35": "Q15286", "RAB1A": "P62820", "RAB2A": "P61019",
    "RAB4A": "P20338", "RAB8A": "P61006", "RAB10": "P61026", "RAB14": "P61106",
    "ANXA1": "P04083", "ANXA2": "P07355", "ANXA4": "P09525", "ANXA5": "P08758",
    "ANXA6": "P08133", "ANXA7": "P20073", "ANXA11": "P50995",
    "HSPA8": "P11142", "HSP90AA1": "P07900", "HSP90AB1": "P08238", "HSPA1A": "P0DMV8",
    "HSPA5": "P11021", "HSPA9": "P38646", "HSPB1": "P04792", "HSPD1": "P10809",
    "ACTB": "P60709", "ACTG1": "P63261", "ACTN1": "P12814", "ACTN4": "O43707",
    "EZR": "P15311", "RDX": "P35241", "MSN": "P26038",
    "MYH9": "P35579", "MYL6": "P60660", "MYL12B": "O14950",
    "TUBB": "P07437", "TUBA1A": "Q71U36", "TUBB4B": "P68371",
    "FLNA": "P21333", "FLNB": "O75369", "VIM": "P08670",
    "CFL1": "P23528", "PFN1": "P07737",
    "GAPDH": "P04406", "PKM": "P14618", "ENO1": "P06733", "LDHA": "P00338",
    "PGK1": "P00558", "TPI1": "P60174", "PGAM1": "P18669",
    "ALDOA": "P04075", "PFKP": "Q01813", "MDH1": "P40925", "MDH2": "P40926",
    "EEF1A1": "P68104", "EEF1A2": "Q05639", "EEF2": "P13639",
    "RPS3": "P23396", "RPS6": "P62753", "RPS8": "P62241",
    "RPLP0": "P05388", "RPLP1": "P05386", "RPLP2": "P05387",
    "RPL5": "P46777", "RPL7": "P18124", "RPL11": "P62913",
    "ITGB1": "P05556", "ITGA5": "P08648", "ITGAV": "P06756",
    "ITGB3": "P05106", "ITGA2": "P17301", "ITGA6": "P23229",
    "ICAM1": "P05362", "VCAM1": "P19320",
    "CD44": "P16070", "CD47": "Q08722",
    "MFGE8": "Q08431", "SDCBP": "O00560", "BSG": "P35613",
    "SLC3A2": "P08195", "CD55": "P08174", "CD59": "P13987",
    "CD73": "P21589", "CD31": "P16284", "CD36": "P16671",
    "CD40": "P25942", "CD45": "P08575",
    "FLOT1": "O75955", "FLOT2": "Q14254",
    "CAV1": "Q03135", "CAV2": "Q51636", "CAV3": "P56539",
    "CLTC": "Q00610", "CLTA": "P09496", "CLTB": "P09497",
    "DNM2": "P50570",
    "YWHAZ": "P63104", "YWHAG": "P61981", "YWHAE": "P62258",
    "YWHAB": "P31946", "YWHAQ": "P27348", "SFN": "P31947",
    "S100A4": "P26447", "S100A6": "P06703", "S100A8": "P05109",
    "S100A9": "P06702", "S100A11": "P31949",
    "LAMP1": "P11279", "LAMP2": "P13473",
    "LGALS1": "P09382", "LGALS3": "P17931", "LGALS3BP": "Q08380",
    "FN1": "P02751", "COL1A1": "P02452", "COL6A1": "P12109",
    "GNAI2": "P04899", "GNB1": "P62873", "GNG12": "Q9UBI6",
    "ARF1": "P84077", "ARF6": "P62330",
    "RAC1": "P63000", "CDC42": "P60953", "RHOA": "P61586",
    "RAP1A": "P62834", "RAP1B": "P61224",
    "VCP": "P55072", "PSMA1": "P25786", "PSMB1": "P20618",
    "CANX": "P27824", "CALR": "P27797", "PDIA3": "P30101",
    "EEF1G": "P26641", "EIF4A1": "P60842", "EIF5A": "P63241",
}

_RNA_MAP = {
    "hsa-miR-21-5p": "ENSG00000199004",
    "hsa-miR-155-5p": "ENSG00000207951",
    "hsa-miR-146a-5p": "ENSG00000207985",
    "hsa-miR-122-5p": "ENSG00000207872",
    "hsa-miR-210-3p": "ENSG00000207709",
    "hsa-miR-16-5p": "ENSG00000207913",
    "hsa-miR-143-3p": "ENSG00000207906",
    "hsa-miR-145-5p": "ENSG00000207893",
    "hsa-miR-200b-3p": "ENSG00000208014",
    "hsa-miR-200c-3p": "ENSG00000207888",
    "hsa-miR-141-3p": "ENSG00000207890",
    "hsa-miR-429": "ENSG00000207997",
    "hsa-miR-92a-3p": "ENSG00000207915",
    "hsa-miR-126-3p": "ENSG00000207907",
    "hsa-miR-30a-5p": "ENSG00000207909",
    "hsa-miR-150-5p": "ENSG00000207893",
    "hsa-miR-223-3p": "ENSG00000207944",
    "hsa-miR-451a": "ENSG00000207898",
    "hsa-let-7a-5p": "ENSG00000199094",
    "hsa-let-7b-5p": "ENSG00000199091",
    "hsa-miR-1": "ENSG00000207699",
    "hsa-miR-10a-5p": "ENSG00000207975",
    "hsa-miR-10b-5p": "ENSG00000207974",
    "hsa-miR-124-3p": "ENSG00000208006",
    "hsa-miR-125a-5p": "ENSG00000207897",
    "hsa-miR-125b-5p": "ENSG00000207973",
    "hsa-miR-128-3p": "ENSG00000208005",
    "hsa-miR-132-3p": "ENSG00000207979",
    "hsa-miR-133a-3p": "ENSG00000207877",
    "hsa-miR-134-3p": "ENSG00000207879",
    "hsa-miR-137": "ENSG00000208008",
    "hsa-miR-138-5p": "ENSG00000207878",
    "hsa-miR-140-3p": "ENSG00000207720",
    "hsa-miR-142-3p": "ENSG00000207884",
    "hsa-miR-148a-3p": "ENSG00000207873",
    "hsa-miR-148b-3p": "ENSG00000207874",
    "hsa-miR-152-3p": "ENSG00000208000",
    "hsa-miR-181a-5p": "ENSG00000207885",
    "hsa-miR-181b-5p": "ENSG00000208102",
    "hsa-miR-182-5p": "ENSG00000207955",
    "hsa-miR-183-5p": "ENSG00000207954",
    "hsa-miR-185-5p": "ENSG00000208009",
    "hsa-miR-186-5p": "ENSG00000207998",
    "hsa-miR-18a-5p": "ENSG00000207982",
    "hsa-miR-191-5p": "ENSG00000207976",
    "hsa-miR-192-5p": "ENSG00000207881",
    "hsa-miR-193a-3p": "ENSG00000207983",
    "hsa-miR-194-5p": "ENSG00000208015",
    "hsa-miR-195-5p": "ENSG00000208001",
    "hsa-miR-199a-3p": "ENSG00000207969",
    "hsa-miR-200a-3p": "ENSG00000207990",
    "hsa-miR-203a-3p": "ENSG00000207996",
    "hsa-miR-204-5p": "ENSG00000208002",
    "hsa-miR-205-5p": "ENSG00000207980",
    "hsa-miR-206": "ENSG00000207999",
    "hsa-miR-20a-5p": "ENSG00000207721",
    "hsa-miR-214-3p": "ENSG00000207971",
    "hsa-miR-215-5p": "ENSG00000208011",
    "hsa-miR-218-5p": "ENSG00000207962",
    "hsa-miR-22-3p": "ENSG00000207908",
    "hsa-miR-221-3p": "ENSG00000207883",
    "hsa-miR-222-3p": "ENSG00000207910",
    "hsa-miR-23a-3p": "ENSG00000207911",
    "hsa-miR-23b-3p": "ENSG00000207912",
    "hsa-miR-24-3p": "ENSG00000207914",
    "hsa-miR-25-3p": "ENSG00000207918",
    "hsa-miR-26a-5p": "ENSG00000207916",
    "hsa-miR-26b-5p": "ENSG00000207917",
    "hsa-miR-27a-3p": "ENSG00000207919",
    "hsa-miR-27b-3p": "ENSG00000207920",
    "hsa-miR-28-5p": "ENSG00000207921",
    "hsa-miR-29a-3p": "ENSG00000207922",
    "hsa-miR-29b-3p": "ENSG00000207923",
    "hsa-miR-29c-3p": "ENSG00000207924",
    "hsa-miR-30b-5p": "ENSG00000207927",
    "hsa-miR-30c-5p": "ENSG00000207928",
    "hsa-miR-30d-5p": "ENSG00000207929",
    "hsa-miR-30e-5p": "ENSG00000207930",
    "hsa-miR-31-5p": "ENSG00000207931",
    "hsa-miR-320a": "ENSG00000207933",
    "hsa-miR-324-5p": "ENSG00000207934",
    "hsa-miR-328-3p": "ENSG00000207935",
    "hsa-miR-331-3p": "ENSG00000207937",
    "hsa-miR-335-5p": "ENSG00000207938",
    "hsa-miR-338-3p": "ENSG00000207939",
    "hsa-miR-339-5p": "ENSG00000207940",
    "hsa-miR-340-5p": "ENSG00000207941",
    "hsa-miR-342-3p": "ENSG00000207942",
    "hsa-miR-34a-5p": "ENSG00000207945",
    "hsa-miR-361-5p": "ENSG00000207946",
    "hsa-miR-362-5p": "ENSG00000207947",
    "hsa-miR-365a-3p": "ENSG00000207949",
    "hsa-miR-375": "ENSG00000207952",
    "hsa-miR-378a-3p": "ENSG00000207953",
    "hsa-miR-381-3p": "ENSG00000207956",
    "hsa-miR-382-5p": "ENSG00000207957",
    "hsa-miR-409-3p": "ENSG00000207960",
    "hsa-miR-410-3p": "ENSG00000207961",
    "hsa-miR-421": "ENSG00000207964",
    "hsa-miR-423-5p": "ENSG00000207967",
    "hsa-miR-424-5p": "ENSG00000207968",
    "hsa-miR-425-5p": "ENSG00000207970",
    "hsa-miR-484": "ENSG00000207975",
    "hsa-miR-486-5p": "ENSG00000207977",
    "hsa-miR-497-5p": "ENSG00000207988",
    "hsa-miR-532-5p": "ENSG00000208034",
    "hsa-miR-574-3p": "ENSG00000208080",
    "hsa-miR-590-3p": "ENSG00000208096",
    "hsa-miR-625-3p": "ENSG00000208133",
    "hsa-miR-652-3p": "ENSG00000208159",
    "hsa-miR-654-3p": "ENSG00000208160",
    "hsa-miR-660-5p": "ENSG00000208161",
    "hsa-miR-671-3p": "ENSG00000208162",
    "hsa-miR-708-5p": "ENSG00000208163",
    "hsa-miR-744-5p": "ENSG00000208164",
    "hsa-miR-758-3p": "ENSG00000208165",
    "hsa-miR-765": "ENSG00000208166",
    "hsa-miR-766-3p": "ENSG00000208167",
    "hsa-miR-769-5p": "ENSG00000208168",
    "hsa-miR-770-5p": "ENSG00000208169",
    "hsa-miR-873-5p": "ENSG00000208170",
    "hsa-miR-874-3p": "ENSG00000208171",
    "hsa-miR-885-5p": "ENSG00000208172",
    "hsa-miR-887-3p": "ENSG00000208173",
    "hsa-miR-888-5p": "ENSG00000208174",
    "hsa-miR-889-3p": "ENSG00000208175",
    "hsa-miR-890": "ENSG00000208176",
    "hsa-miR-891a-5p": "ENSG00000208177",
    "hsa-miR-891b": "ENSG00000208178",
    "hsa-miR-892a": "ENSG00000208179",
    "hsa-miR-892b": "ENSG00000208180",
    "hsa-miR-920": "ENSG00000208181",
    "hsa-miR-921": "ENSG00000208182",
    "hsa-miR-922": "ENSG00000208183",
    "hsa-miR-923": "ENSG00000208184",
    "hsa-miR-924": "ENSG00000208185",
    "hsa-miR-935": "ENSG00000208186",
    "hsa-miR-939-5p": "ENSG00000208187",
    "hsa-miR-940": "ENSG00000208188",
    "hsa-miR-941": "ENSG00000208189",
    "hsa-miR-942-5p": "ENSG00000208190",
    "hsa-miR-943": "ENSG00000208191",
    "hsa-miR-944": "ENSG00000208192",
    "hsa-miR-95-3p": "ENSG00000208193",
    "hsa-miR-96-5p": "ENSG00000208194",
    "hsa-miR-98-5p": "ENSG00000208195",
    "hsa-miR-99a-5p": "ENSG00000208196",
    "hsa-miR-99b-5p": "ENSG00000208197",
}

_LIPID_MAP = {
    "Phosphatidylcholine": "LMGP01010001",
    "Phosphatidylethanolamine": "LMGP02010001",
    "Phosphatidylserine": "LMGP03010001",
    "Phosphatidylinositol": "LMGP04010001",
    "Sphingomyelin": "LMSP03010001",
    "Ceramide": "LMSP02010001",
    "Cholesterol": "LMST01010001",
    "LysoPC": "LMGP01050001",
    "LysoPE": "LMGP02050001",
    "Phosphatidic acid": "LMGP10010001",
    "GM3 ganglioside": "LMSP06020001",
    "Lactosylceramide": "LMSP02020001",
    "Hexosylceramide": "LMSP02030001",
    "Sulfatide": "LMSP06010001",
    "BMP": "LMGP01070001",
    "Phosphatidylglycerol": "LMGP04010001",
    "Cardiolipin": "LMGP12010001",
    "Diacylglycerol": "LMGL02010001",
    "Triacylglycerol": "LMGL03010001",
    "Free fatty acid": "LMFA01010001",
    "Arachidonic acid": "LMFA03000001",
    "Ceramide-1-phosphate": "LMSP02040001",
    "Sphingosine-1-phosphate": "LMSP01050001",
    "Phytosphingosine": "LMSP01010001",
    "Dihydrosphingomyelin": "LMSP03020001",
    "Cholesteryl ester": "LMST01020001",
    "Bis(monoacylglycero)phosphate": "LMGP01070001",
    "Phosphatidylinositol 3-phosphate": "LMGP04030001",
    "Phosphatidylinositol 4-phosphate": "LMGP04030002",
    "Phosphatidylinositol 4,5-bisphosphate": "LMGP04030003",
}


def standardize_ids(df: pd.DataFrame, mapping: dict, id_col: str,
                    cargo_type: str) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning("Empty DataFrame passed to standardize_ids for %s", cargo_type)
        return df
    df = df.copy()
    mapped = sum(1 for i in df.index if i in mapping)
    df[id_col] = df.index.map(mapping.get)
    logger.info("[%s] Mapped %d/%d entries to %s",
                cargo_type, mapped, len(df), id_col)
    return df


def standardize_protein_ids(df: pd.DataFrame) -> pd.DataFrame:
    return standardize_ids(df, _PROTEIN_MAP, "uniprot_id", "protein")


def standardize_rna_ids(df: pd.DataFrame) -> pd.DataFrame:
    return standardize_ids(df, _RNA_MAP, "ensembl_id", "rna")


def standardize_lipid_ids(df: pd.DataFrame) -> pd.DataFrame:
    return standardize_ids(df, _LIPID_MAP, "lipidmaps_id", "lipid")


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning("Empty DataFrame passed to remove_duplicates")
        return df
    before = len(df)
    df = df.drop_duplicates(keep="first")
    after = len(df)
    if after < before:
        logger.info("Removed %d duplicate row(s)", before - after)
    return df


def log_transform(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning("Empty DataFrame passed to log_transform")
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return df
    result = df.copy()
    result[numeric_cols] = np.log1p(result[numeric_cols])
    logger.info("Applied log1p transform to %d numeric column(s)", len(numeric_cols))
    return result


def knn_impute(df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning("Empty DataFrame passed to knn_impute")
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
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
    if df is None or df.empty:
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
    if df is None or df.empty:
        logger.warning("Empty DataFrame passed to normalize_dataset")
        return df

    if cargo_type == "protein":
        df = standardize_protein_ids(df)
    elif cargo_type == "rna":
        df = standardize_rna_ids(df)
    elif cargo_type == "lipid":
        df = standardize_lipid_ids(df)

    df = remove_duplicates(df)
    df = log_transform(df)
    df = knn_impute(df)
    df = unit_variance_scale(df)

    logger.info("Normalization complete for %s — shape %s", cargo_type, df.shape)
    return df
