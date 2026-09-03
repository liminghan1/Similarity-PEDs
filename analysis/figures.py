"""Phase 12: publication-quality figures (project brief Sec. 33), built from the real artifacts
already produced by Phases 8-11 -- no figure here computes a new statistic, only visualizes ones
already computed and tested elsewhere. Every figure states its sample size and is saved as both
PNG (300 dpi) and PDF (vector) to figures/.

Figure 2 (data-coverage heatmap) is produced by analysis/missingness_analysis.py (Phase 5), not
here. Figures 1, 3-10 are produced here.

Usage:
    uv run python -m analysis.figures
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from sklearn.decomposition import PCA

ARTIFACTS_DIR = Path("artifacts/matrices")
FIGURES_DIR = Path("figures")
DPI = 300


def _save(fig, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {FIGURES_DIR / name}.png (+.pdf)")


def _captioned_title(ax, caption: str, *, width: int = 78, fontsize: int = 9) -> None:
    ax.set_title("\n".join(textwrap.wrap(caption, width=width)), fontsize=fontsize, loc="left")


# --------------------------------------------------------------------------------------
# Figure 1: project / data-flow schematic
# --------------------------------------------------------------------------------------

def figure1_schematic() -> None:
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def box(xy, w, h, text, color):
        x, y = xy
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
            linewidth=1.2, edgecolor="#333333", facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, wrap=True)

    def arrow(xy_start, xy_end):
        ax.annotate(
            "", xy=xy_end, xytext=xy_start,
            arrowprops={"arrowstyle": "-|>", "color": "#333333", "lw": 1.4},
        )

    box((0.3, 5.3), 2.6, 1.1, "Chemical structure\n(PubChem, RDKit)\nPhase 4", "#cfe8f3")
    box((0.3, 3.6), 2.6, 1.1, "Receptor pharmacology\n(ChEMBL, BindingDB)\nPhase 5", "#cfe8f3")
    box((3.7, 4.45), 2.6, 1.1, "Molecular /\npharmacological phenotype\nPhase 8 (Rep. A)", "#a8d3e6")
    box((0.3, 1.2), 2.6, 1.1, "FAERS adverse-event\nreports\nPhase 6", "#f3d9b1")
    box((3.7, 1.2), 2.6, 1.1, "Safety phenotype\n(logROR, per category)\nPhase 8 (Rep. B)", "#e8c088")
    box((7.1, 2.8), 2.4, 1.9, "Similarity / matrix-\nassociation analysis\n(Mantel test)\nPhase 9-11", "#c9e4c5")

    arrow((2.9, 5.85), (3.7, 5.35))
    arrow((2.9, 4.15), (3.7, 4.85))
    arrow((2.9, 1.75), (3.7, 1.75))
    arrow((6.3, 5.0), (7.1, 4.2))
    arrow((6.3, 1.75), (7.1, 3.2))

    ax.text(
        5.0, 0.3,
        "Representation A (molecular/pharmacological) and Representation B (safety) are built "
        "independently and compared only via the distance-matrix association test.",
        ha="center", fontsize=8, style="italic",
    )
    ax.set_title("Figure 1. Structure-to-Safety data-flow schematic", fontsize=11, loc="left")
    _save(fig, "figure1_data_flow_schematic")


# --------------------------------------------------------------------------------------
# Figure 3: molecular phenotype PCA
# --------------------------------------------------------------------------------------

def figure3_molecular_pca() -> None:
    molecular = pd.read_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv", index_col=0)
    numeric = molecular.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.std() > 0]  # drop zero-variance columns (Phase 9 finding)
    z = (numeric - numeric.mean()) / numeric.std()

    pca = PCA(n_components=2)
    scores = pca.fit_transform(z.values)
    var_explained = pca.explained_variance_ratio_ * 100

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(scores[:, 0], scores[:, 1], s=90, color="#4477aa", edgecolor="black", zorder=3)
    for i, name in enumerate(z.index):
        ax.annotate(name, (scores[i, 0], scores[i, 1]), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}% variance explained)")
    ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}% variance explained)")
    _captioned_title(
        ax,
        f"Figure 3. Molecular phenotype PCA (n={len(z)} compounds, {z.shape[1]} RDKit descriptors, "
        "z-scored; receptor pharmacology omitted -- only 3/10 compounds have any receptor "
        "measurement, see Phase 9). EXPLORATORY visualization only.",
    )
    _save(fig, "figure3_molecular_phenotype_pca")


# --------------------------------------------------------------------------------------
# Figure 4: safety phenotype PCA
# --------------------------------------------------------------------------------------

def figure4_safety_pca() -> None:
    safety = pd.read_csv(ARTIFACTS_DIR / "safety_phenotype_matrix_logror.csv", index_col=0)
    complete_categories = safety.columns[safety.notna().all()].tolist()
    complete = safety[complete_categories]

    pca = PCA(n_components=2)
    scores = pca.fit_transform(complete.values)
    var_explained = pca.explained_variance_ratio_ * 100

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(scores[:, 0], scores[:, 1], s=90, color="#cc6677", edgecolor="black", zorder=3)
    for i, name in enumerate(complete.index):
        ax.annotate(name, (scores[i, 0], scores[i, 1]), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}% variance explained)")
    ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}% variance explained)")
    _captioned_title(
        ax,
        f"Figure 4. Safety phenotype PCA (n={len(complete)} compounds, {len(complete_categories)}/11 "
        f"research-defined AE categories with complete logROR data across all compounds: "
        f"{', '.join(complete_categories)}). EXPLORATORY visualization only.",
    )
    _save(fig, "figure4_safety_phenotype_pca")


# --------------------------------------------------------------------------------------
# Figures 5-6: similarity heatmaps
# --------------------------------------------------------------------------------------

def _similarity_heatmap(
    distance_matrix: pd.DataFrame, *, title: str, filename: str, cmap: str, vmin: float, vmax: float
) -> None:
    """`vmin`/`vmax` must match the actual possible range of `1 - distance` for the metric used:
    a min-max-normalized structural distance is bounded to [0, 1] (similarity in [0, 1]), but a
    correlation-based distance (1 - Pearson r) ranges [0, 2] since r ranges [-1, 1], so its
    similarity ranges [-1, 1] -- **not** [0, 1]. Using a fixed vmin=0 for both regardless of this
    silently clipped every strongly-anti-correlated pair (e.g. testosterone vs. every other
    compound in the safety heatmap, real r as low as ~-0.96) to the colormap floor, which for a
    dark colormap rendered as solid black -- visually indistinguishable from the actual "gray =
    undefined" missing-data color, even though the underlying data was fully defined (confirmed
    by loading the raw CSV directly: zero NaNs in that row). Found by inspecting a rendered
    figure against the known-complete data, not by inspection of the code alone.
    """
    similarity = 1.0 - distance_matrix  # NaN-safe: NaN - x = NaN
    labels = similarity.index.tolist()
    n = len(labels)

    fig, ax = plt.subplots(figsize=(8, 7))
    masked = np.ma.masked_invalid(similarity.values)
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(color="#e8e8e8")
    im = ax.imshow(masked, cmap=cmap_obj, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=8)
    midpoint = (vmin + vmax) / 2
    for i in range(n):
        for j in range(n):
            val = similarity.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=6,
                         color="white" if val > midpoint else "black")
    fig.colorbar(im, ax=ax, label="Similarity (1 - distance)")
    _captioned_title(ax, title)
    _save(fig, filename)


def figure5_structural_similarity() -> None:
    structure_dist = pd.read_csv(ARTIFACTS_DIR / "structure_distance_matrix.csv", index_col=0)
    n = len(structure_dist)
    _similarity_heatmap(
        structure_dist,
        title=f"Figure 5. Molecular structural similarity (n={n} compounds; mean of min-max-normalized "
              "Tanimoto fingerprint and Euclidean descriptor distance, bounded [0,1]; 1 - distance shown).",
        filename="figure5_structural_similarity_heatmap",
        cmap="viridis", vmin=0, vmax=1,
    )


def figure6_safety_similarity() -> None:
    safety_dist = pd.read_csv(ARTIFACTS_DIR / "safety_distance_matrix.csv", index_col=0)
    n = len(safety_dist)
    total_pairs = n * (n - 1) // 2
    defined_pairs = int(safety_dist.notna().sum().sum() / 2 - n / 2) if n else 0
    _similarity_heatmap(
        safety_dist,
        title=f"Figure 6. Safety-phenotype similarity (n={n} compounds; Pearson correlation on shared "
              "logROR categories -- similarity ranges [-1,1], NOT [0,1], since it is a correlation "
              f"coefficient; 1 - distance shown; gray = undefined, {defined_pairs}/{total_pairs} pairs "
              "have >=3 shared categories).",
        filename="figure6_safety_similarity_heatmap",
        cmap="RdBu_r", vmin=-1, vmax=1,
    )


# --------------------------------------------------------------------------------------
# Figure 7: primary matrix-association result (illustration only -- inference is the Mantel test)
# --------------------------------------------------------------------------------------

def figure7_matrix_association_scatter() -> None:
    structure_dist = pd.read_csv(ARTIFACTS_DIR / "structure_distance_matrix.csv", index_col=0)
    safety_dist = pd.read_csv(ARTIFACTS_DIR / "safety_distance_matrix.csv", index_col=0)
    with (ARTIFACTS_DIR / "matrix_association_results.json").open() as f:
        assoc = json.load(f)
    h2_result = next(r for r in assoc["results"] if "structure-only" in r["description"])

    labels = structure_dist.index.tolist()
    xs, ys = [], []
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            sd = safety_dist.loc[a, b]
            if pd.notna(sd):
                xs.append(structure_dist.loc[a, b])
                ys.append(sd)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(xs, ys, s=60, color="#4477aa", edgecolor="black", alpha=0.8, zorder=3)
    ax.set_xlabel("Structural distance (molecular/pharmacological representation)")
    ax.set_ylabel("Safety-phenotype distance")
    stat_line = (
        f"Mantel test (SECONDARY, H2): Spearman rho={h2_result['statistic_spearman_rho']:.3f}, "
        f"one-sided p={h2_result['p_value_one_sided']:.3f}, n={h2_result['n_objects']} compounds, "
        f"{len(xs)} pairs. PRIMARY (combined structure+receptor) test: NOT COMPUTABLE (see Phase 9)."
    )
    _captioned_title(
        ax,
        "Figure 7. Molecular vs. safety-phenotype pairwise distance (each point = one compound pair; "
        "for illustration only -- statistical inference is the permutation test, not this scatter). "
        + stat_line,
        width=95,
    )
    _save(fig, "figure7_matrix_association_scatter")


# --------------------------------------------------------------------------------------
# Figure 8: structure-only vs. receptor-only vs. combined
# --------------------------------------------------------------------------------------

def figure8_representation_comparison() -> None:
    with (ARTIFACTS_DIR / "matrix_association_results.json").open() as f:
        assoc = json.load(f)

    order = [
        ("PRIMARY\ncombined", "combined"),
        ("SECONDARY\nstructure-only", "structure-only"),
        ("SECONDARY\nreceptor-only", "receptor-only"),
    ]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    xs = range(len(order))
    heights, colors, annotations = [], [], []
    for label, key in order:
        r = next(r for r in assoc["results"] if key in r["description"])
        if r["computable"]:
            heights.append(r["statistic_spearman_rho"])
            colors.append("#4477aa")
            annotations.append(f"p={r['p_value_one_sided']:.3f}\nn={r['n_objects']}")
        else:
            heights.append(0.0)
            colors.append("#cccccc")
            annotations.append("NOT\nCOMPUTABLE")

    bars = ax.bar(xs, heights, color=colors, edgecolor="black")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([label for label, _ in order])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Spearman rho (distance-matrix association with safety phenotype)")
    # Fixed, explicit y-limits so a zero-height "not computable" bar's label sits inside the
    # plot rather than drifting above y=0 into the title area (all real rho values here are
    # negative, so naive height-relative placement pushed that label above the data range
    # entirely -- found by rendering the figure, not by inspection).
    span = max(heights) - min(heights) if heights else 1.0
    pad = max(span * 0.25, 0.05)
    ax.set_ylim(min(heights) - pad, max(heights) + pad)
    for bar, ann, height in zip(bars, annotations, heights):
        label_y = (height - pad * 0.4) if height < 0 else -pad * 0.4
        ax.text(bar.get_x() + bar.get_width() / 2, label_y, ann, ha="center", va="top", fontsize=8)
    _captioned_title(
        ax,
        "Figure 8. Comparison of molecular representations' association with the safety phenotype "
        "(H2). The combined (PRIMARY) and receptor-only representations are not computable with "
        "current receptor-bioactivity coverage (Phase 9); only structure-only is fully computable.",
    )
    _save(fig, "figure8_representation_comparison")


# --------------------------------------------------------------------------------------
# Figure 9: therapeutic vs. misuse safety profiles
# --------------------------------------------------------------------------------------

def figure9_therapeutic_vs_misuse() -> None:
    table = pd.read_csv(ARTIFACTS_DIR / "misuse_vs_therapeutic_ae_categories.csv")
    table = table.sort_values("odds_ratio")
    log_or = np.log(table["odds_ratio"])
    log_ci_low = np.log(table["ci_low"])
    log_ci_high = np.log(table["ci_high"])
    err_low = log_or - log_ci_low
    err_high = log_ci_high - log_or

    fig, ax = plt.subplots(figsize=(8, 6))
    y = list(range(len(table)))
    colors = ["#cc6677" if p < 0.05 else "#888888" for p in table["fisher_p_value"]]
    # ax.errorbar's `ecolor` takes a single color, not a per-point list (passing a list raised
    # "RGBA sequence should have length 3 or 4" -- found running this against real data, not by
    # inspection) -- draw each point's error bar individually instead, colored by significance.
    for i, (lo_val, hi_val, y_val, c) in enumerate(zip(err_low, err_high, y, colors)):
        ax.errorbar(
            log_or.iloc[i], y_val, xerr=[[lo_val], [hi_val]], fmt="o", color=c,
            ecolor=c, elinewidth=2, capsize=3, markersize=6, zorder=3,
        )
    ax.axvline(0, color="black", lw=0.8, linestyle="--")
    ax.set_yticks(list(y))
    ax.set_yticklabels(table["category"])
    ax.set_xlabel("log(Odds Ratio), misuse-associated vs. therapeutic-associated reports")
    n_misuse = int(table["misuse_n"].iloc[0])
    n_therapeutic = int(table["therapeutic_n"].iloc[0])
    _captioned_title(
        ax,
        f"Figure 9. Therapeutic-use-vs-misuse AE category comparison (H3). Misuse-associated "
        f"n={n_misuse}, therapeutic-associated n={n_therapeutic} reports (real, classified FAERS "
        "data, Phase 6). Red = Fisher exact p<0.05. Error bars = 95% CI on log(OR).",
    )
    _save(fig, "figure9_therapeutic_vs_misuse")


# --------------------------------------------------------------------------------------
# Figure 10: sensitivity-analysis summary
# --------------------------------------------------------------------------------------

def figure10_sensitivity_summary() -> None:
    with (ARTIFACTS_DIR / "sensitivity_results.json").open() as f:
        sens = json.load(f)
    with (ARTIFACTS_DIR / "matrix_association_results.json").open() as f:
        assoc = json.load(f)
    primary_h2 = next(r for r in assoc["results"] if "structure-only" in r["description"])

    labels = ["Primary\n(full cohort)"] + list(sens.keys())
    entries = [primary_h2] + list(sens.values())

    fig, ax = plt.subplots(figsize=(11, 6))
    xs = range(len(labels))
    heights, colors, annotations = [], [], []
    for e in entries:
        if e.get("computable"):
            heights.append(e["statistic_spearman_rho"])
            colors.append("#4477aa")
            annotations.append(f"p={e['p_value_one_sided']:.2f}")
        else:
            heights.append(0.0)
            colors.append("#cccccc")
            annotations.append("N/A")

    bars = ax.bar(xs, heights, color=colors, edgecolor="black")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.5)
    ax.set_ylabel("Spearman rho (structure-only vs. safety distance)")
    # Explicit headroom above y=0 so a label on a positive (or zero-height "N/A") bar doesn't
    # sit flush against the top axis spine, next to the wrapped title (see the matching fix in
    # figure8_representation_comparison, found the same way -- by rendering, not inspection).
    span = max(heights) - min(heights) if heights else 1.0
    pad = max(span * 0.15, 0.04)
    ax.set_ylim(min(heights) - pad, max(heights) + pad)
    for bar, ann, height in zip(bars, annotations, heights):
        label_y = height + pad * 0.3 if height >= 0 else height - pad * 0.3
        ax.text(bar.get_x() + bar.get_width() / 2, label_y, ann, ha="center",
                 va="bottom" if height >= 0 else "top", fontsize=7)
    _captioned_title(
        ax,
        "Figure 10. Sensitivity-analysis summary (Phase 11): the H2 (structure-only vs. safety) "
        "Mantel test re-run under each of the 8 pre-specified variants. All computable variants "
        "remain non-significant (p>0.05); gray bars are variants not computable with current data.",
        width=100,
    )
    _save(fig, "figure10_sensitivity_summary")


def run() -> None:
    figure1_schematic()
    figure3_molecular_pca()
    figure4_safety_pca()
    figure5_structural_similarity()
    figure6_safety_similarity()
    figure7_matrix_association_scatter()
    figure8_representation_comparison()
    figure9_therapeutic_vs_misuse()
    figure10_sensitivity_summary()


if __name__ == "__main__":
    run()
