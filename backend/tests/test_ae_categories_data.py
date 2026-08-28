"""Static data-quality checks on research/ae_categories.csv.

Regression guard: an earlier version of this file had several notes containing an unquoted
comma, which silently produced extra columns per row (caught by manual inspection while building
analysis/phenotype_matrix.py, not by a test -- this test exists so it's caught automatically next
time).
"""

import csv
from pathlib import Path

AE_CATEGORIES_CSV = Path(__file__).parent.parent.parent / "research" / "ae_categories.csv"


def _read_rows():
    with AE_CATEGORIES_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, [row for row in reader if row]


class TestAeCategoriesCsv:
    def test_every_row_has_exactly_four_columns(self):
        header, rows = _read_rows()
        assert header == ["category", "representative_reported_term", "version", "notes"]
        for i, row in enumerate(rows, start=2):
            assert len(row) == 4, f"row {i} has {len(row)} columns (expected 4): {row}"

    def test_no_empty_category_or_term(self):
        _, rows = _read_rows()
        for row in rows:
            assert row[0].strip(), f"empty category in row: {row}"
            assert row[1].strip(), f"empty representative_reported_term in row: {row}"

    def test_no_duplicate_category_term_pairs(self):
        _, rows = _read_rows()
        seen = set()
        for row in rows:
            key = (row[0].strip().lower(), row[1].strip().lower())
            assert key not in seen, f"duplicate (category, term) pair: {key}"
            seen.add(key)

    def test_version_is_a_recognized_value(self):
        _, rows = _read_rows()
        for row in rows:
            assert row[2] in ("0.1", "0.2"), f"unexpected version {row[2]!r} in row: {row}"
