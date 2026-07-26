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


def perform_pca(matrix_df: pd.DataFrame, title: str, output_dir: Path, n_components: int = 5) -> dict:
    matrix_t = matrix_df.T
    n = min(n_components, min(matrix_t.shape))
    if n < 2:
        logger.warning(f'{title}: insufficient dimensions for PCA with n_components={n}')
        return {'pca': None, 'scores': pd.DataFrame(), 'loadings': pd.DataFrame(), 'explained_var_ratio': []}

    pca = PCA(n_components=n)
    scores = pca.fit_transform(matrix_t)
    scores_df = pd.DataFrame(scores, index=matrix_t.index, columns=[f'PC{i+1}' for i in range(n)])
    loadings_df = pd.DataFrame(pca.components_.T, index=matrix_t.columns, columns=[f'PC{i+1}' for i in range(n)])

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(scores_df.iloc[:, 0], scores_df.iloc[:, 1], alpha=0.7)
    for label, x, y in zip(scores_df.index, scores_df.iloc[:, 0], scores_df.iloc[:, 1]):
        ax.annotate(str(label), (x, y), fontsize=6, alpha=0.8)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.set_title(f'{title} PCA Score Plot')
    fig.savefig(output_dir / f'{title}_pca_scores.png', bbox_inches='tight', dpi=120)
    plt.close('all')

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(loadings_df.iloc[:, 0], loadings_df.iloc[:, 1], alpha=0.7)
    abs_loadings = np.abs(loadings_df.iloc[:, 0]).argsort()
    top_indices = abs_loadings[-10:]
    for i in top_indices:
        ax.annotate(loadings_df.index[i], (loadings_df.iloc[i, 0], loadings_df.iloc[i, 1]), fontsize=7, alpha=0.8)
    ax.axhline(0, color='grey', linestyle='--', linewidth=0.5)
    ax.axvline(0, color='grey', linestyle='--', linewidth=0.5)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.set_title(f'{title} PCA Loadings')
    fig.savefig(output_dir / f'{title}_pca_loadings.png', bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'pca': pca,
        'scores': scores_df,
        'loadings': loadings_df,
        'explained_var_ratio': pca.explained_variance_ratio_.tolist(),
    }


def perform_plsda(matrix_df: pd.DataFrame, metadata: pd.DataFrame, title: str, output_dir: Path, n_components: int = 2) -> dict:
    matrix_t = matrix_df.T
    matrix_t.index = matrix_t.index.astype(str)
    merged = matrix_t.merge(metadata, left_index=True, right_on='evtrack_id', how='inner')

    def simplify_protocol(protocol):
        if pd.isna(protocol):
            return None
        protocol_lower = str(protocol).lower()
        if 'duc' in protocol_lower or 'ultracentrifugation' in protocol_lower:
            return 'UC'
        if 'sec' in protocol_lower:
            return 'SEC'
        if 'kit' in protocol_lower or 'precipitation' in protocol_lower:
            return 'Precipitation'
        return 'Other'

    merged['isolation_group'] = merged['separation_protocol'].apply(simplify_protocol)
    merged = merged.dropna(subset=['isolation_group'])

    if merged['isolation_group'].nunique() < 2:
        logger.warning('PLS-DA requires at least 2 isolation groups')
        return {'plsda': None, 'scores': pd.DataFrame(), 'variance_explained': {}, 'predictions': []}

    le = LabelEncoder()
    target_encoded = le.fit_transform(merged['isolation_group'])

    cargo_cols = [c for c in matrix_t.columns if c in merged.columns]
    X = merged[cargo_cols].values
    Y = target_encoded.reshape(-1, 1)

    nc = min(n_components, min(X.shape))
    plsda = PLSRegression(n_components=nc)
    plsda.fit(X, Y)
    scores = plsda.transform(X)
    scores_df = pd.DataFrame(scores, index=merged.index, columns=[f'LV{i+1}' for i in range(nc)])

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
        ax.scatter(scores_df.loc[mask, 'LV1'], scores_df.loc[mask, 'LV2'],
                   label=group, color=color, alpha=0.7, edgecolors='k', s=60)
    ax.set_xlabel(f'LV1 ({x_var[0]*100:.1f}% X variance)')
    ax.set_ylabel(f'LV2 ({x_var[1]*100:.1f}% X variance)')
    ax.set_title('PLS-DA Score Plot by Isolation Method')
    ax.legend()
    fig.savefig(output_dir / f'{title}_plsda_scores.png', bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'plsda': plsda,
        'scores': scores_df,
        'variance_explained': {
            'X_variance': x_var.tolist(),
            'Y_variance': y_var.tolist(),
        },
        'predictions': predictions.tolist(),
    }


def hierarchical_clustering(matrix_df: pd.DataFrame, title: str, output_dir: Path) -> dict:
    if matrix_df.shape[1] < 2:
        logger.warning('Need at least 2 studies for clustering')
        return {'linkage_matrix': None, 'distance_matrix': None, 'labels': list(matrix_df.columns)}

    dist = pdist(matrix_df.T, 'correlation')
    Z = linkage(dist, method='average')
    labels = list(matrix_df.columns)

    fig, ax = plt.subplots(figsize=(14, 6))
    dendrogram(Z, labels=labels, leaf_rotation=90, ax=ax)
    ax.set_title(f'{title} — Hierarchical Clustering (correlation, average linkage)')
    ax.set_ylabel('Distance')
    fig.savefig(output_dir / f'{title}_dendrogram.png', bbox_inches='tight', dpi=120)
    plt.close('all')

    return {
        'linkage_matrix': Z,
        'distance_matrix': dist,
        'labels': labels,
    }


def plot_heatmap(matrix_df: pd.DataFrame, title: str, output_dir: Path, top_n: int = 100) -> Path:
    if matrix_df.shape[0] < 2:
        logger.warning('Need at least 2 cargo molecules for heatmap')
        out_path = output_dir / f'{title}_heatmap.png'
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, 'Insufficient data for heatmap', ha='center', va='center', transform=ax.transAxes)
        fig.savefig(out_path, bbox_inches='tight', dpi=120)
        plt.close('all')
        return out_path

    variances = matrix_df.var(axis=1).sort_values(ascending=False)
    n_used = min(top_n, len(variances))
    top_genes = variances.head(n_used).index
    subset = matrix_df.loc[top_genes]
    figsize = (12, min(n_used / 4 + 2, 30))
    g = sns.clustermap(subset, z_score=0, cmap='vlag', figsize=figsize)
    g.fig.suptitle(f'Top {n_used} Most Variable {title}')
    out_path = output_dir / f'{title}_heatmap.png'
    g.fig.savefig(out_path, bbox_inches='tight', dpi=120)
    plt.close('all')
    return out_path


def generate_summary(profiles: dict, pca_results: dict, cluster_results: dict,
                     plsda_results: dict, metadata: pd.DataFrame, output_dir: Path) -> Path:
    out_path = output_dir / 'summary.txt'
    lines = []
    lines.append('EV-TRACK Data Analysis Summary')
    lines.append('=' * 40)
    lines.append('')

    n_studies = len(metadata) if metadata is not None else 0
    lines.append(f'Number of studies processed: {n_studies}')
    lines.append('')

    lines.append('Cargo Type Profiles')
    lines.append('-' * 40)
    for cargo_type, mat in profiles.items():
        lines.append(f'\n{cargo_type.capitalize()}:')
        if mat is not None and not mat.empty:
            lines.append(f'  Matrix dimensions: {mat.shape[0]} cargo molecules x {mat.shape[1]} studies')
            variances = mat.var(axis=1).sort_values(ascending=False)
            top3 = variances.head(3).index.tolist()
            lines.append(f'  Top 3 most variable cargo molecules: {", ".join(str(x) for x in top3)}')
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
    lines.append('PLS-DA Results')
    lines.append('-' * 40)
    plsda_res = plsda_results or {}
    if plsda_res.get('plsda') is not None:
        predictions = plsda_res.get('predictions', [])
        lines.append(f'  Number of samples predicted: {len(predictions)}')
    else:
        lines.append('  PLS-DA not performed')

    lines.append('')
    lines.append('Hierarchical Clustering')
    lines.append('-' * 40)
    Z = cluster_results.get('linkage_matrix')
    labels = cluster_results.get('labels', [])
    if Z is not None and len(labels) > 0:
        n_clusters = min(3, len(labels))
        cluster_labels = fcluster(Z, t=n_clusters, criterion='maxclust')
        lines.append(f'  Number of clusters identified: {n_clusters}')
        for cl in range(1, n_clusters + 1):
            members = [labels[i] for i, c in enumerate(cluster_labels) if c == cl]
            lines.append(f'\n  Cluster {cl} ({len(members)} studies):')
            lines.append(f'    Studies: {", ".join(str(m) for m in members)}')
            if metadata is not None and 'species' in metadata.columns:
                merged_info = metadata[metadata['evtrack_id'].astype(str).isin(members)]
                if not merged_info.empty and 'species' in merged_info.columns:
                    common_species = merged_info['species'].value_counts().index[0]
                    lines.append(f'    Common species: {common_species}')
    else:
        lines.append('  Clustering not available')

    lines.append('')
    lines.append('Biological Interpretation')
    lines.append('-' * 40)
    if Z is not None and len(labels) > 0:
        lines.append('  Hierarchical clustering using correlation distance and average linkage reveals')
        lines.append(f'  {n_clusters} major clusters among the studies based on cargo molecule expression profiles.')
        lines.append('  These clusters may reflect differences in experimental conditions, EV isolation methods,')
        lines.append('  or biological samples. Studies within the same cluster share similar molecular cargo')
        lines.append('  signatures, suggesting potential commonalities in EV subtype composition or')
        lines.append('  functional properties across these studies.')
    else:
        lines.append('  Insufficient data for clustering-based biological interpretation.')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n')
    return out_path
