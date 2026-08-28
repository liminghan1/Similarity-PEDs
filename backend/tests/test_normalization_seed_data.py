"""Static data-quality checks on the curated normalization seed CSVs
(pipelines/normalization/*.csv), independent of any database.

These catch curation errors -- e.g. an alias referencing a formulation_name that doesn't exist
in formulations_seed.csv, or an invalid alias_type -- at test time rather than only when the
seed script runs against a real database.
"""

import csv

from backend.app.models.compounds import AliasType
from pipelines.normalization.seed_registry import ALIASES_CSV, FORMULATIONS_CSV
from pipelines.pubchem.cohort import INITIAL_COHORT

COHORT_NAMES = {c.canonical_name for c in INITIAL_COHORT}


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestFormulationsSeed:
    def test_every_formulation_references_a_cohort_compound(self):
        rows = _read_csv(FORMULATIONS_CSV)
        assert rows, "formulations_seed.csv should not be empty"
        for row in rows:
            assert row["canonical_name"] in COHORT_NAMES, (
                f"formulation {row['formulation_name']!r} references unknown compound "
                f"{row['canonical_name']!r}"
            )

    def test_formulation_names_unique_per_compound(self):
        rows = _read_csv(FORMULATIONS_CSV)
        seen = set()
        for row in rows:
            key = (row["canonical_name"], row["formulation_name"])
            assert key not in seen, f"duplicate formulation row: {key}"
            seen.add(key)


class TestAliasesSeed:
    def test_every_alias_references_a_cohort_compound(self):
        rows = _read_csv(ALIASES_CSV)
        assert rows, "aliases_seed.csv should not be empty"
        for row in rows:
            assert row["canonical_name"] in COHORT_NAMES, (
                f"alias {row['alias']!r} references unknown compound {row['canonical_name']!r}"
            )

    def test_alias_type_is_valid(self):
        rows = _read_csv(ALIASES_CSV)
        valid_types = {t.value for t in AliasType}
        for row in rows:
            assert row["alias_type"] in valid_types, (
                f"alias {row['alias']!r} has invalid alias_type {row['alias_type']!r}"
            )

    def test_formulation_scoped_aliases_reference_a_declared_formulation(self):
        """Every non-empty formulation_name in aliases_seed.csv must exist in
        formulations_seed.csv for the same compound -- this is exactly the class of error
        seed_registry.py would otherwise silently reject at load time (data quality caught here,
        at test time, instead)."""
        formulation_rows = _read_csv(FORMULATIONS_CSV)
        declared = {(row["canonical_name"], row["formulation_name"]) for row in formulation_rows}

        alias_rows = _read_csv(ALIASES_CSV)
        for row in alias_rows:
            formulation_name = row.get("formulation_name", "").strip()
            if not formulation_name:
                continue  # parent-level alias, not formulation-scoped
            key = (row["canonical_name"], formulation_name)
            assert key in declared, (
                f"alias {row['alias']!r} references formulation {formulation_name!r} for "
                f"{row['canonical_name']!r}, which is not declared in formulations_seed.csv"
            )

    def test_verified_column_is_well_formed_boolean_text(self):
        rows = _read_csv(ALIASES_CSV)
        for row in rows:
            assert row["verified"].strip().lower() in ("true", "false"), (
                f"alias {row['alias']!r} has non-boolean verified value {row['verified']!r}"
            )

    def test_no_duplicate_alias_rows(self):
        rows = _read_csv(ALIASES_CSV)
        seen = set()
        for row in rows:
            key = (row["canonical_name"], row["alias"], row["alias_type"])
            assert key not in seen, f"duplicate alias row: {key}"
            seen.add(key)
