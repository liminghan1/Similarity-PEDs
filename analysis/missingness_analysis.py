"""Coverage / missingness analysis (project brief Sec. 26).

Builds the compound x {AR, PR, GR, MR, ERalpha, ERbeta, FAERS} coverage matrix -- counts of
usable measurements, not binary presence/absence, so real sparsity is visible rather than hidden
-- and renders it as Figure 2 (a data-coverage heatmap). Missing values are never treated as
zero activity; a `0` in this matrix means "zero *measurements*," which is a statement about data
availability, not about the compound's actual pharmacology.

Usage:
    uv run python -m analysis.missingness_analysis
"""

from __future__ import annotations

import csv
import datetime as dt
import subprocess
from pathlib import Path

import textwrap

import matplotlib.pyplot as plt
import numpy as np

from backend.app.db.session import SessionLocal
from backend.app.models import Bioactivity, Compound, FaersDrug, Target
from pipelines.bindingdb.targets import BINDINGDB_TARGETS
from pipelines.chembl.targets import RECEPTOR_TARGETS

RECEPTOR_COLUMNS = ["AR", "PR", "GR", "MR", "ERalpha", "ERbeta"]
ALL_COLUMNS = RECEPTOR_COLUMNS + ["FAERS"]

ARTIFACTS_DIR = Path("artifacts/matrices")
FIGURES_DIR = Path("figures")


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _target_id_to_receptor_short_name(db) -> dict[int, str]:
    """Map every targets.id in the DB back to its canonical receptor short name (AR/PR/.../
    ERbeta), using the static (source, source_target_id) -> short_name registries in
    pipelines/chembl/targets.py and pipelines/bindingdb/targets.py, so ChEMBL's and BindingDB's
    separately-provenanced Target rows for "the same" biological receptor are combined into one
    coverage column."""
    lookup = {}
    for r in RECEPTOR_TARGETS:
        lookup[("chembl", r.chembl_target_id)] = r.short_name
    for r in BINDINGDB_TARGETS:
        lookup[("bindingdb", r.uniprot_id)] = r.short_name

    result = {}
    for target in db.query(Target).all():
        short_name = lookup.get((target.source, target.source_target_id))
        if short_name is not None:
            result[target.id] = short_name
    return result


def build_coverage_matrix(db) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Returns (compound_names_sorted, {compound_name: {column: count}})."""
    compounds = db.query(Compound).order_by(Compound.canonical_name).all()
    compound_names = [c.canonical_name for c in compounds]
    matrix = {name: dict.fromkeys(ALL_COLUMNS, 0) for name in compound_names}

    target_to_receptor = _target_id_to_receptor_short_name(db)
    compound_id_to_name = {c.id: c.canonical_name for c in compounds}

    for bioactivity in db.query(Bioactivity).all():
        receptor = target_to_receptor.get(bioactivity.target_id)
        compound_name = compound_id_to_name.get(bioactivity.compound_id)
        if receptor is None or compound_name is None:
            continue
        matrix[compound_name][receptor] += 1

    for faers_drug in db.query(FaersDrug).filter(FaersDrug.normalized_compound_id.isnot(None)).all():
        compound_name = compound_id_to_name.get(faers_drug.normalized_compound_id)
        if compound_name is not None:
            matrix[compound_name]["FAERS"] += 1

    return compound_names, matrix


def write_csv(compound_names: list[str], matrix: dict[str, dict[str, int]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["canonical_name", *ALL_COLUMNS])
        for name in compound_names:
            writer.writerow([name, *[matrix[name][col] for col in ALL_COLUMNS]])


def plot_heatmap(compound_names: list[str], matrix: dict[str, dict[str, int]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = np.array([[matrix[name][col] for col in ALL_COLUMNS] for name in compound_names])

    fig, ax = plt.subplots(figsize=(8, max(3, 0.5 * len(compound_names) + 1)))
    # 0 measurements rendered as a distinct light-gray "missing" color, not the low end of a
    # continuous scale, so missingness reads as missingness rather than "a small number."
    masked = np.ma.masked_equal(data, 0)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="#e8e8e8")
    im = ax.imshow(masked, cmap=cmap, aspect="auto")

    ax.set_xticks(range(len(ALL_COLUMNS)))
    ax.set_xticklabels(ALL_COLUMNS, rotation=45, ha="right")
    ax.set_yticks(range(len(compound_names)))
    ax.set_yticklabels(compound_names)

    for i, name in enumerate(compound_names):
        for j, col in enumerate(ALL_COLUMNS):
            value = matrix[name][col]
            ax.text(
                j, i, str(value), ha="center", va="center",
                color="black" if value == 0 else "white" if value > data.max() / 2 else "black",
                fontsize=9,
            )

    caption = (
        f"Figure 2. Compound x target data-coverage matrix (n={len(compound_names)} cohort compounds). "
        "Cell values = count of usable measurements (Ki/IC50/EC50/Kd bioactivity records, or "
        "normalized FAERS drug-report mappings). Gray = zero measurements (missing, not zero activity)."
    )
    ax.set_title("\n".join(textwrap.wrap(caption, width=70)), fontsize=9, loc="left")
    fig.colorbar(im, ax=ax, label="Measurement count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    fig.savefig(out_path.with_suffix(".pdf"))
    plt.close(fig)


def run() -> None:
    db = SessionLocal()
    try:
        compound_names, matrix = build_coverage_matrix(db)
    finally:
        db.close()

    csv_path = ARTIFACTS_DIR / "coverage_matrix.csv"
    write_csv(compound_names, matrix, csv_path)
    fig_path = FIGURES_DIR / "figure2_data_coverage_heatmap.png"
    plot_heatmap(compound_names, matrix, fig_path)

    total_cells = len(compound_names) * len(ALL_COLUMNS)
    missing_cells = sum(1 for name in compound_names for col in ALL_COLUMNS if matrix[name][col] == 0)
    print(f"Coverage matrix written to {csv_path}")
    print(f"Figure written to {fig_path} (and .pdf)")
    print(
        f"Missingness: {missing_cells}/{total_cells} compound x column cells have zero measurements "
        f"({100 * missing_cells / total_cells:.1f}%)."
    )
    print(f"Generated {dt.datetime.now(dt.timezone.utc).isoformat()} at commit {_code_version()}")


if __name__ == "__main__":
    run()
