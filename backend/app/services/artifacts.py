"""Reads the already-computed research artifacts (artifacts/matrices/*.csv, *.json) produced by
analysis/*.py (Phases 8-13) for the API layer to serve. This module never computes a new
statistic -- it only loads and reshapes what analysis/ already wrote and tested (Sec. 37:
DERIVED STATISTICS are computed once, by the analysis pipeline, not on every API request).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ARTIFACTS_DIR = Path("artifacts/matrices")


class ArtifactNotFoundError(Exception):
    """Raised when a requested artifact has not been generated yet (e.g. the analysis pipeline
    has not been run). The API layer turns this into a clear 404, not a fabricated empty result."""


def _require(path: Path) -> Path:
    if not path.exists():
        raise ArtifactNotFoundError(
            f"{path} does not exist -- run the corresponding analysis/*.py script first "
            "(see Makefile targets `build-datasets`, `analyze`)."
        )
    return path


def load_matrix_csv(name: str) -> dict:
    """Loads a compound x compound (or compound x category) CSV matrix and returns it as
    {"labels": [...], "columns": [...], "values": [[...]]} with NaN as JSON null."""
    path = _require(ARTIFACTS_DIR / f"{name}.csv")
    df = pd.read_csv(path, index_col=0)
    return {
        "labels": df.index.tolist(),
        "columns": df.columns.tolist(),
        "values": df.where(pd.notna(df), None).values.tolist(),
    }


def load_json_artifact(name: str) -> dict:
    path = _require(ARTIFACTS_DIR / f"{name}.json")
    with path.open() as f:
        return json.load(f)


def load_long_table_csv(name: str) -> list[dict]:
    path = _require(ARTIFACTS_DIR / f"{name}.csv")
    df = pd.read_csv(path)
    return df.where(pd.notna(df), None).to_dict(orient="records")
