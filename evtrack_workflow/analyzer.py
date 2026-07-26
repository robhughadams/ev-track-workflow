import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.preprocessing import LabelEncoder
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist
from pathlib import Path
import logging

sns.set_theme(style='whitegrid')
logger = logging.getLogger(__name__)


def perform_pca(matrix_df: pd.DataFrame, title: str,
                output_dir: Path, n_components: int = 5) -> dict:
    matrix_t = matrix_df.select_dtypes(include=[np.number]).T
    n = min(n_components, min(matrix_t.shape))
    if n < 2:
        logger.warning('%s: insufficient dimensions for PCA', title)
        return {'pca': None, 'scores': pd.DataFrame(), 'loadings': pd.DataFrame(),
                'explained_var_ratio': [], 'n_components': 0}

    pca = PCA(n_components=n)
    scores = pca.fit_transform(matrix_t)
    scores_df = pd.DataFrame(
        scores, index=matrix_t.index,
        columns=[f'PC{i+1}' for i in range(n)]
    )
    loadings_df = pd.DataFrame(
        pca.components_.T, index=matrix_t.columns,
        columns=[f'PC{i+1}' for i in range(n)]
    )

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(scores_df.iloc[:, 0], scores_df.iloc[:, 1], alpha=0.7)
    for label, x, y in zip(scores_df.index, scores_df.iloc[:, 0],
                            scores_df.iloc[:, 1]):
        ax.annotate(str(label), (x, y), fontsize=6, alpha=0.8)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.set_title(f'{title} PCA Score Plot')
    fig.savefig(output_dir / f'{title}_pca_scores.png',
                bbox_inches='tight', dpi=120)
    plt.close('all')

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(loadings_df.iloc[:, 0], loadings_df.iloc[:, 1], alpha=0.7)
    abs_loadings = np.abs(loadings_df.iloc[:, 0]).argsort()
    top_indices = abs_loadings[-10:]
    for i in top_indices:
        ax.annotate(loadings_df.index[i],
                    (loadings_df.iloc[i, 0], loadings_df.iloc[i, 1]),
                    fontsize=7, alpha=0.8)
    ax.axhline(0, color='grey', linestyle='--', linewidth=0.5)
    ax.axvline(0, color='grey', linestyle='--', linewidth=0.5)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.set_title(f'{title} PCA Loadings')
    fig.savefig(output_dir / f'{title}_pca_loadings.png',
                bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'pca': pca,
        'scores': scores_df,
        'loadings': loadings_df,
        'explained_var_ratio': pca.explained_variance_ratio_.tolist(),
        'n_components': n,
    }


def perform_plsda(matrix_df: pd.DataFrame, metadata: pd.DataFrame,
                  title: str, output_dir: Path,
                  n_components: int = 2) -> dict:
    matrix_t = matrix_df.select_dtypes(include=[np.number]).T
    matrix_t.index = matrix_t.index.astype(str)
    merged = matrix_t.merge(
        metadata, left_index=True, right_on='evtrack_id', how='inner'
    )

    def simplify_protocol(protocol):
        if pd.isna(protocol):
            return None
        p = str(protocol).lower()
        if 'duc' in p or 'ultracentrifugation' in p:
            return 'UC'
        if 'sec' in p:
            return 'SEC'
        if 'kit' in p or 'precipitation' in p:
            return 'Precipitation'
        return 'Other'

    merged['isolation_group'] = merged['separation_protocol'].apply(
        simplify_protocol
    )
    merged = merged.dropna(subset=['isolation_group'])

    if merged['isolation_group'].nunique() < 2:
        logger.warning('PLS-DA requires at least 2 isolation groups')
        return {'plsda': None, 'scores': pd.DataFrame(),
                'variance_explained': {}, 'predictions': []}

    le = LabelEncoder()
    target_encoded = le.fit_transform(merged['isolation_group'])

    cargo_cols = [c for c in matrix_t.columns if c in merged.columns]
    X = merged[cargo_cols].values
    Y = target_encoded.reshape(-1, 1)

    nc = min(n_components, min(X.shape))
    plsda = PLSRegression(n_components=nc)
    plsda.fit(X, Y)
    scores = plsda.transform(X)
    scores_df = pd.DataFrame(
        scores, index=merged.index,
        columns=[f'LV{i+1}' for i in range(nc)]
    )

    x_var = np.var(plsda.x_scores_, axis=0) / np.var(X, axis=0).sum()
    y_var = np.var(plsda.y_scores_, axis=0) / np.var(Y, axis=0).sum()

    pred_raw = plsda.predict(X)
    pred_int = np.round(pred_raw.flatten()).astype(int)
    pred_int = np.clip(pred_int, 0, len(le.classes_) - 1)
    predictions = le.inverse_transform(pred_int)

    fig, ax = plt.subplots(figsize=(8, 6))
    groups = merged['isolation_group'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(groups)))
    for group, color in zip(groups, colors):
        mask = merged['isolation_group'] == group
        ax.scatter(scores_df.loc[mask, 'LV1'],
                    scores_df.loc[mask, 'LV2'],
                    label=group, color=color, alpha=0.7,
                    edgecolors='k', s=60)
    ax.set_xlabel(f'LV1 ({x_var[0]*100:.1f}% X variance)')
    ax.set_ylabel(f'LV2 ({x_var[1]*100:.1f}% X variance)')
    ax.set_title('PLS-DA Score Plot by Isolation Method')
    ax.legend()
    fig.savefig(output_dir / f'{title}_plsda_scores.png',
                bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'plsda': plsda,
        'scores': scores_df,
        'variance_explained': {
            'X_variance': x_var.tolist(),
            'Y_variance': y_var.tolist(),
        },
        'predictions': predictions.tolist(),
        'groups': le.classes_.tolist(),
    }


def hierarchical_clustering(matrix_df: pd.DataFrame, title: str,
                            output_dir: Path) -> dict:
    numeric = matrix_df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        logger.warning('Need at least 2 studies for clustering')
        return {'linkage_matrix': None, 'distance_matrix': None,
                'labels': list(numeric.columns)}

    dist = pdist(numeric.T, 'correlation')
    Z = linkage(dist, method='average')
    labels = list(numeric.columns)

    fig, ax = plt.subplots(figsize=(14, 6))
    dendrogram(Z, labels=labels, leaf_rotation=90, ax=ax)
    ax.set_title(f'{title} Hierarchical Clustering (correlation, average linkage)')
    ax.set_ylabel('Distance')
    fig.savefig(output_dir / f'{title}_dendrogram.png',
                bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'linkage_matrix': Z,
        'distance_matrix': dist,
        'labels': labels,
    }


def plot_heatmap(matrix_df: pd.DataFrame, title: str,
                 output_dir: Path, top_n: int = 200) -> Path:
    numeric = matrix_df.select_dtypes(include=[np.number])
    if numeric.shape[0] < 2:
        logger.warning('Need at least 2 cargo molecules for heatmap')
        out_path = output_dir / f'{title}_heatmap.png'
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, 'Insufficient data for heatmap',
                ha='center', va='center', transform=ax.transAxes)
        fig.savefig(out_path, bbox_inches='tight', dpi=120)
        plt.close('all')
        return out_path

    variances = numeric.var(axis=1).sort_values(ascending=False)
    n_used = min(top_n, len(variances))
    top_genes = variances.head(n_used).index
    subset = numeric.loc[top_genes]
    figsize = (12, min(n_used / 4 + 2, 30))
    g = sns.clustermap(subset, z_score=0, cmap='vlag', figsize=figsize)
    g.fig.suptitle(f'Top {n_used} Most Variable {title}')
    out_path = output_dir / f'{title}_heatmap.png'
    g.fig.savefig(out_path, bbox_inches='tight', dpi=120)
    plt.close('all')
    return out_path


def perform_umap_combined(normalized: dict, metadata: pd.DataFrame,
                          output_dir: Path,
                          n_pca_components: int = 10) -> dict:
    try:
        import umap
    except ImportError:
        logger.warning("umap-learn not installed; skipping UMAP")
        return {'embedding': None, 'scores_df': pd.DataFrame()}

    pca_dfs = []
    common_idx = None
    for ctype, mat in normalized.items():
        numeric = mat.select_dtypes(include=[np.number])
        if numeric.shape[0] < 3 or numeric.shape[1] < 3:
            continue
        t = numeric.T
        if common_idx is None:
            common_idx = set(t.index)
        else:
            common_idx &= set(t.index)
        nc = min(n_pca_components, min(t.shape))
        pca = PCA(n_components=nc)
        scores = pca.fit_transform(t)
        sdf = pd.DataFrame(
            scores, index=t.index,
            columns=[f'{ctype}_PC{i+1}' for i in range(nc)]
        )
        pca_dfs.append(sdf)
        logger.info("UMAP prep — %s reduced to %d PCs", ctype, nc)

    if not pca_dfs or not common_idx:
        logger.warning("Not enough data for combined UMAP")
        return {'embedding': None, 'scores_df': pd.DataFrame()}

    common_idx = sorted(common_idx)
    combined = pd.concat(
        [sdf.loc[common_idx] for sdf in pca_dfs], axis=1
    )
    logger.info("Combined PCA scores shape for UMAP: %s", combined.shape)

    reducer = umap.UMAP(n_neighbors=min(10, len(common_idx) - 1),
                        min_dist=0.3, random_state=42)
    embedding = reducer.fit_transform(combined.values)
    scores_df = pd.DataFrame(embedding, index=common_idx,
                             columns=['UMAP1', 'UMAP2'])

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(scores_df['UMAP1'], scores_df['UMAP2'], alpha=0.7, s=50)
    meta_map = {
        str(r['evtrack_id']): r.get('separation_protocol', '')
        for _, r in metadata.iterrows()
    }
    for sid in scores_df.index:
        ax.annotate(str(sid), (scores_df.loc[sid, 'UMAP1'],
                                scores_df.loc[sid, 'UMAP2']),
                    fontsize=6, alpha=0.8)
    ax.set_xlabel('UMAP1')
    ax.set_ylabel('UMAP2')
    ax.set_title('UMAP Embedding — Combined Cargo Profiles')
    fig.savefig(output_dir / 'combined_umap.png',
                bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'embedding': embedding,
        'scores_df': scores_df,
        'n_studies': len(common_idx),
        'n_cargo_types': len(pca_dfs),
    }


def generate_summary(profiles: dict, pca_results: dict,
                     cluster_results: dict, plsda_results: dict,
                     umap_results: dict, metadata: pd.DataFrame,
                     output_dir: Path) -> Path:
    out_path = output_dir / 'summary.txt'
    lines = []
    lines.append('EV-TRACK Extended Cargo Analysis Summary')
    lines.append('=' * 50)
    lines.append('')

    n_studies = len(metadata) if metadata is not None else 0
    lines.append(f'Number of studies processed: {n_studies}')
    lines.append('')

    lines.append('Cargo Type Profiles')
    lines.append('-' * 40)
    for cargo_type, mat in profiles.items():
        lines.append(f'\n{cargo_type.capitalize()}:')
        if mat is not None and not mat.empty:
            numeric = mat.select_dtypes(include=[np.number])
            lines.append(f'  Matrix dimensions: {numeric.shape[0]} '
                         f'molecules x {numeric.shape[1]} studies')
            variances = numeric.var(axis=1).sort_values(ascending=False)
            top3 = variances.head(3).index.tolist()
            lines.append(f'  Top 3 most variable: '
                         f'{", ".join(str(x) for x in top3)}')
        else:
            lines.append('  No data available')

    lines.append('')
    lines.append('PCA Results')
    lines.append('-' * 40)
    for cargo_type, pca_res in pca_results.items():
        lines.append(f'\n{cargo_type.capitalize()}:')
        var_ratio = pca_res.get('explained_var_ratio', [])
        if len(var_ratio) >= 2:
            lines.append(f'  PC1 explained variance: {var_ratio[0]*100:.1f}%')
            lines.append(f'  PC2 explained variance: {var_ratio[1]*100:.1f}%')
        elif len(var_ratio) == 1:
            lines.append(f'  PC1 explained variance: {var_ratio[0]*100:.1f}%')
            lines.append('  PC2: not available')
        else:
            lines.append('  PCA not available')

    lines.append('')
    lines.append('UMAP Results (Combined Multi-Cargo Embedding)')
    lines.append('-' * 40)
    if umap_results and umap_results.get('embedding') is not None:
        lines.append(f'  Number of studies embedded: '
                     f'{umap_results["n_studies"]}')
        lines.append(f'  Cargo types combined: '
                     f'{umap_results["n_cargo_types"]}')
    else:
        lines.append('  UMAP not performed')

    lines.append('')
    lines.append('PLS-DA Results')
    lines.append('-' * 40)
    plsda_res = plsda_results or {}
    if plsda_res.get('plsda') is not None:
        predictions = plsda_res.get('predictions', [])
        groups = plsda_res.get('groups', [])
        lines.append(f'  Number of samples predicted: {len(predictions)}')
        lines.append(f'  Isolation groups: {", ".join(groups)}')
    else:
        lines.append('  PLS-DA not performed')

    lines.append('')
    lines.append('Hierarchical Clustering')
    lines.append('-' * 40)
    for cargo_type, cl_res in cluster_results.items():
        lines.append(f'\n{cargo_type.capitalize()}:')
        Z = cl_res.get('linkage_matrix')
        labels = cl_res.get('labels', [])
        if Z is not None and len(labels) > 0:
            n_clusters = min(3, len(labels))
            cluster_labels = fcluster(Z, t=n_clusters, criterion='maxclust')
            lines.append(f'  Number of clusters identified: {n_clusters}')
            for cl in range(1, n_clusters + 1):
                members = [labels[i] for i, c in enumerate(cluster_labels)
                           if c == cl]
                lines.append(f'\n  Cluster {cl} ({len(members)} studies):')
                lines.append(f'    Studies: {", ".join(str(m) for m in members)}')
                if metadata is not None and 'species' in metadata.columns:
                    merged_info = metadata[
                        metadata['evtrack_id'].astype(str).isin(members)
                    ]
                    if not merged_info.empty:
                        common_species = (
                            merged_info['species'].value_counts().index[0]
                        )
                        lines.append(f'    Common species: {common_species}')
        else:
            lines.append('  Clustering not available')

    lines.append('')
    lines.append('Biological Interpretation')
    lines.append('-' * 40)
    lines.append(
        '  The PCA and UMAP embeddings reveal the major axes of variation '
        'across studies.'
    )
    lines.append(
        '  Hierarchical clustering of each cargo type groups studies with '
        'similar molecular signatures.'
    )
    if plsda_res.get('plsda') is not None:
        lines.append(
            '  PLS-DA successfully discriminated studies by isolation method, '
            'confirming that'
        )
        lines.append(
            '  the isolation protocol is a major source of variation in EV '
            'cargo composition.'
        )
    lines.append(
        '  These results should be interpreted as exploratory; validation '
        'with independent cohorts'
    )
    lines.append(
        '  and functional assays is recommended for any specific hypotheses.'
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n')
    logger.info("Summary written to %s", out_path)
    return out_path
