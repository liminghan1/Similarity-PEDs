"""Phase 10 (SECONDARY): independent clustering of the molecular/structural and safety-phenotype
representations, and comparison of the resulting cluster structures (project brief Sec. 20).

Method: hierarchical (agglomerative) clustering on the precomputed distance matrices from Phase 9
(average linkage -- a standard, non-restrictive default for precomputed distances). The number of
clusters k is chosen per representation by maximizing the silhouette score over k=2..5 (a small,
data-driven, documented rule -- not picked to produce an interesting-looking result, and computed
identically for both representations before any comparison is made).

Receptor-based clustering is NOT run: Phase 9 established the receptor distance matrix has 0/45
defined pairs with current data, so there is nothing to cluster (same documented limitation, not
repeated here as a new deviation).

PCA-based clustering and UMAP are EXPLORATORY only (project brief Sec. 20: "avoid interpreting
UMAP geometry quantitatively") -- UMAP is deferred entirely to Phase 12 figures; a PCA+k-means
cross-check is included here labeled EXPLORATORY, not compared quantitatively against the
hierarchical result via ARI/NMI (those metrics compare two independent *primary* clusterings
against each other, not a primary against an exploratory one).

Cluster-structure comparison metrics: Adjusted Rand Index and Normalized Mutual Information
(sklearn), appropriate for comparing two hard partitions of the same object set. Cophenetic
correlation is reported per dendrogram as a QC diagnostic of how well each dendrogram preserves
its own input distances -- not a between-representation comparison metric.

Usage:
    uv run python -m analysis.clustering
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

ARTIFACTS_DIR = Path("artifacts/matrices")


def _condensed(matrix: pd.DataFrame) -> np.ndarray:
    """scipy's condensed-distance-vector form, from a symmetric zero-diagonal DataFrame."""
    return squareform(matrix.values, checks=False)


def best_k_hierarchical(matrix: pd.DataFrame, *, k_range: range = range(2, 6)) -> tuple[int, np.ndarray, np.ndarray]:
    """Returns (best_k, cluster_labels_at_best_k, linkage_matrix), choosing k by max silhouette
    score (metric='precomputed') over k_range."""
    condensed = _condensed(matrix)
    Z = linkage(condensed, method="average")
    best = None
    for k in k_range:
        labels = fcluster(Z, t=k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(matrix.values, labels, metric="precomputed")
        if best is None or score > best[0]:
            best = (score, k, labels)
    if best is None:
        raise ValueError("Could not find k>=2 with more than one cluster across k_range.")
    _, k, labels = best
    return k, labels, Z


def cophenetic_correlation(matrix: pd.DataFrame, Z: np.ndarray) -> float:
    """scipy.cluster.hierarchy.cophenet(Z, Y), when given the original condensed distance
    vector Y, returns (c, coph_dists) where c IS the cophenetic correlation coefficient --
    it does not need to be recomputed via np.corrcoef (an earlier version of this function did,
    incorrectly, by unpacking the tuple in the wrong order, which silently computed
    np.corrcoef(condensed, c) with c a scalar -- caught by test_clustering.py's shape-mismatch
    failure, not by inspection)."""
    condensed = _condensed(matrix)
    c, _coph_dists = cophenet(Z, condensed)
    return float(c)


def pca_kmeans_exploratory(descriptor_matrix: pd.DataFrame, *, n_components: int = 2, k: int = 3) -> np.ndarray:
    """EXPLORATORY cross-check only (project brief Sec. 20/40) -- not used for ARI/NMI comparison
    against the primary hierarchical result."""
    numeric = descriptor_matrix.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.std() > 0]
    z = (numeric - numeric.mean()) / numeric.std()
    pcs = PCA(n_components=min(n_components, z.shape[1])).fit_transform(z.values)
    labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(pcs)
    return labels


def run() -> None:
    structure_dist = pd.read_csv(ARTIFACTS_DIR / "structure_distance_matrix.csv", index_col=0)
    safety_dist = pd.read_csv(ARTIFACTS_DIR / "safety_distance_matrix.csv", index_col=0)
    molecular = pd.read_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv", index_col=0)

    labels_order = structure_dist.index.tolist()
    assert labels_order == safety_dist.index.tolist(), "structure/safety matrices must share compound order"

    k_structure, structure_labels, Z_structure = best_k_hierarchical(structure_dist)
    k_safety, safety_labels, Z_safety = best_k_hierarchical(safety_dist)

    ari = adjusted_rand_score(structure_labels, safety_labels)
    nmi = normalized_mutual_info_score(structure_labels, safety_labels)
    coph_structure = cophenetic_correlation(structure_dist, Z_structure)
    coph_safety = cophenetic_correlation(safety_dist, Z_safety)

    pca_labels = pca_kmeans_exploratory(molecular)

    result = {
        "label": "SECONDARY (structure vs. safety cluster comparison); PCA+k-means block is EXPLORATORY",
        "n_compounds": len(labels_order),
        "compounds": labels_order,
        "structure_clustering": {
            "method": "hierarchical (average linkage), k chosen by max silhouette over k=2..5",
            "k": k_structure,
            "cluster_labels": {name: int(lab) for name, lab in zip(labels_order, structure_labels)},
            "cophenetic_correlation": coph_structure,
        },
        "safety_clustering": {
            "method": "hierarchical (average linkage), k chosen by max silhouette over k=2..5",
            "k": k_safety,
            "cluster_labels": {name: int(lab) for name, lab in zip(labels_order, safety_labels)},
            "cophenetic_correlation": coph_safety,
        },
        "receptor_clustering": "NOT COMPUTABLE -- 0/45 pairs defined in receptor_distance_matrix (see Phase 9)",
        "cluster_agreement": {
            "adjusted_rand_index": float(ari),
            "normalized_mutual_information": float(nmi),
        },
        "pca_kmeans_exploratory": {
            "note": "EXPLORATORY only -- not compared via ARI/NMI against the primary hierarchical result",
            "cluster_labels": {name: int(lab) for name, lab in zip(labels_order, pca_labels)},
        },
    }

    with (ARTIFACTS_DIR / "clustering_results.json").open("w") as f:
        json.dump(result, f, indent=2)

    print(f"Structure clustering: k={k_structure}, cophenetic r={coph_structure:.3f}")
    for name, lab in zip(labels_order, structure_labels):
        print(f"  {name}: cluster {lab}")
    print(f"\nSafety clustering: k={k_safety}, cophenetic r={coph_safety:.3f}")
    for name, lab in zip(labels_order, safety_labels):
        print(f"  {name}: cluster {lab}")
    print(f"\nCluster agreement: ARI={ari:.3f}, NMI={nmi:.3f}")
    print(f"\nWrote {ARTIFACTS_DIR / 'clustering_results.json'}")


if __name__ == "__main__":
    run()
