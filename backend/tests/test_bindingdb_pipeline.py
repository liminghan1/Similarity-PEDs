"""Unit tests for pipelines/bindingdb/ingest.py::parse_affinity, using real value formats
captured from the live BindingDB API (getLigandsByUniprot for UniProt P10275/AR, 2026-08-27 --
see pipelines/bindingdb/README.md)."""

import pytest

from pipelines.bindingdb.ingest import parse_affinity


class TestParseAffinity:
    def test_plain_value_with_leading_space(self):
        # Real record: {'bdb.affinity_type': 'IC50', 'bdb.affinity': ' 219'}
        result = parse_affinity(" 219")
        assert result.relation == "="
        assert result.value_nm == pytest.approx(219.0)

    def test_censored_greater_than_value(self):
        # Real record: {'bdb.affinity_type': 'Ki', 'bdb.affinity': '>10000'}
        result = parse_affinity(">10000")
        assert result.relation == ">"
        assert result.value_nm == pytest.approx(10000.0)

    def test_censored_less_than_value(self):
        result = parse_affinity("<0.5")
        assert result.relation == "<"
        assert result.value_nm == pytest.approx(0.5)

    def test_decimal_value(self):
        result = parse_affinity(" 57.9")
        assert result.relation == "="
        assert result.value_nm == pytest.approx(57.9)

    def test_unparseable_text_returns_none(self):
        assert parse_affinity("N/A") is None
        assert parse_affinity("") is None
