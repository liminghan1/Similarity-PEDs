import numpy as np
import pandas as pd
import pytest

from analysis.clustering import best_k_hierarchical, cophenetic_correlation, pca_kmeans_exploratory


@pytest.fixture
def two_cluster_matrix():
    # A,B close to each other; C,D close to each other; the two pairs far apart.
    labels = ["A", "B", "C", "D"]
    values = np.array(
        [
            [0.0, 1.0, 10.0, 11.0],
            [1.0, 0.0, 11.0, 10.0],
            [10.0, 11.0, 0.0, 1.0],
            [11.0, 10.0, 1.0, 0.0],
        ]
    )
    return pd.DataFrame(values, index=labels, columns=labels)


class TestBestKHierarchical:
    def test_recovers_two_obvious_clusters(self, two_cluster_matrix):
        k, cluster_labels, Z = best_k_hierarchical(two_cluster_matrix, k_range=range(2, 4))
        assert k == 2
        label_map = dict(zip(two_cluster_matrix.index, cluster_labels))
        assert label_map["A"] == label_map["B"]
        assert label_map["C"] == label_map["D"]
        assert label_map["A"] != label_map["C"]

    def test_linkage_matrix_has_expected_shape(self, two_cluster_matrix):
        _, _, Z = best_k_hierarchical(two_cluster_matrix, k_range=range(2, 4))
        # n-1 merge steps for n=4 objects.
        assert Z.shape == (3, 4)


class TestCopheneticCorrelation:
    def test_perfect_ultrametric_gives_correlation_near_one(self):
        # A tree-like (ultrametric) distance matrix should reproduce almost perfectly in its
        # own dendrogram.
        labels = ["A", "B", "C", "D"]
        values = np.array(
            [
                [0.0, 1.0, 5.0, 5.0],
                [1.0, 0.0, 5.0, 5.0],
                [5.0, 5.0, 0.0, 2.0],
                [5.0, 5.0, 2.0, 0.0],
            ]
        )
        matrix = pd.DataFrame(values, index=labels, columns=labels)
        _, _, Z = best_k_hierarchical(matrix, k_range=range(2, 4))
        r = cophenetic_correlation(matrix, Z)
        assert r > 0.99


class TestPcaKmeansExploratory:
    def test_returns_one_label_per_compound(self):
        descriptors = pd.DataFrame(
            {
                "mw": [100.0, 105.0, 500.0, 510.0, 300.0],
                "logp": [1.0, 1.1, 8.0, 8.2, 4.0],
                "constant_col": [1, 1, 1, 1, 1],  # zero variance -- must not crash
            },
            index=["A", "B", "C", "D", "E"],
        )
        labels = pca_kmeans_exploratory(descriptors, k=2)
        assert len(labels) == 5
