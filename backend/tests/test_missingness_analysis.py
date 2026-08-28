import csv

from analysis.missingness_analysis import ALL_COLUMNS, write_csv


def test_write_csv_round_trips_matrix(tmp_path):
    compound_names = ["boldenone", "testosterone"]
    matrix = {
        "boldenone": dict.fromkeys(ALL_COLUMNS, 0),
        "testosterone": {**dict.fromkeys(ALL_COLUMNS, 0), "AR": 11, "GR": 2},
    }
    out_path = tmp_path / "coverage_matrix.csv"

    write_csv(compound_names, matrix, out_path)

    with out_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [r["canonical_name"] for r in rows] == compound_names
    assert rows[0]["AR"] == "0"
    assert rows[1]["AR"] == "11"
    assert rows[1]["GR"] == "2"
    assert rows[1]["FAERS"] == "0"
