"""Unit tests for pipelines/chembl/units.py (nM conversion) and the pure activity-filtering
logic in pipelines/chembl/ingest.py::evaluate_activity, using fixture payloads captured from
real ChEMBL API responses (testosterone, CHEMBL386630, vs. androgen receptor CHEMBL1871, on
2026-08-27 -- see pipelines/chembl/README.md) rather than synthetic data.
"""

import pytest

from pipelines.chembl.ingest import evaluate_activity
from pipelines.chembl.units import to_nanomolar

# Real activity record (IC50 = 3.9 nM, relation '=').
REAL_QUALIFYING_ACTIVITY = {
    "activity_id": 1469054,
    "assay_chembl_id": "CHEMBL874560",
    "potential_duplicate": 0,
    "data_validity_comment": None,
    "standard_type": "IC50",
    "standard_relation": "=",
    "standard_value": "3.9",
    "standard_units": "nM",
    "value": "3.9",
    "units": "nM",
}

# Real record with no determinable relation/value ("Not Determined").
REAL_NOT_DETERMINED_ACTIVITY = {
    "activity_id": 1469056,
    "assay_chembl_id": "CHEMBL834741",
    "potential_duplicate": 0,
    "data_validity_comment": None,
    "standard_type": "IC50",
    "standard_relation": None,
    "standard_value": None,
    "standard_units": "nM",
    "value": None,
    "units": "nM",
}

# Real record ChEMBL itself flags as a likely duplicate of another curated entry.
REAL_DUPLICATE_ACTIVITY = {
    "activity_id": 2030222,
    "assay_chembl_id": "CHEMBL874560",
    "potential_duplicate": 1,
    "data_validity_comment": None,
    "standard_type": "IC50",
    "standard_relation": "=",
    "standard_value": "2.7",
    "standard_units": "nM",
    "value": "2.7",
    "units": "nM",
}


class TestToNanomolar:
    def test_nanomolar_passthrough(self):
        assert to_nanomolar(3.9, "nM") == pytest.approx(3.9)

    def test_micromolar_converts(self):
        assert to_nanomolar(1.0, "uM") == pytest.approx(1000.0)

    def test_millimolar_converts(self):
        assert to_nanomolar(1.0, "mM") == pytest.approx(1_000_000.0)

    def test_molar_converts(self):
        assert to_nanomolar(1.0, "M") == pytest.approx(1_000_000_000.0)

    def test_picomolar_converts(self):
        assert to_nanomolar(1000.0, "pM") == pytest.approx(1.0)

    def test_unrecognized_unit_returns_none(self):
        assert to_nanomolar(5.0, "%") is None
        assert to_nanomolar(5.0, "mg/kg") is None


class TestEvaluateActivity:
    def test_qualifying_activity_is_kept_and_standardized(self):
        result = evaluate_activity(REAL_QUALIFYING_ACTIVITY)
        assert result.keep
        assert result.measurement_type == "IC50"
        assert result.relation == "="
        assert result.standardized_value_nm == pytest.approx(3.9)
        # 9 - log10(3.9) ~= 8.409, matches ChEMBL's own pchembl_value (8.41) for this record.
        assert result.p_activity == pytest.approx(8.409, abs=0.01)
        assert not result.unrecognized_units

    def test_not_determined_activity_is_skipped(self):
        result = evaluate_activity(REAL_NOT_DETERMINED_ACTIVITY)
        assert not result.keep
        assert result.skip_reason == "no_relation_or_value"

    def test_potential_duplicate_is_skipped(self):
        result = evaluate_activity(REAL_DUPLICATE_ACTIVITY)
        assert not result.keep
        assert result.skip_reason == "potential_duplicate"

    def test_data_validity_flagged_is_skipped(self):
        flagged = {**REAL_QUALIFYING_ACTIVITY, "data_validity_comment": "Outside typical range"}
        result = evaluate_activity(flagged)
        assert not result.keep
        assert result.skip_reason == "data_validity_flagged"

    def test_non_equals_relation_has_no_pactivity(self):
        # A ">" censored value has a defined standardized_value_nm but an undefined point
        # pActivity (research/exclusion_rules.md Sec. 3: only relation == '=' gets p_activity).
        censored = {**REAL_QUALIFYING_ACTIVITY, "standard_relation": ">", "value": ">3.9"}
        result = evaluate_activity(censored)
        assert result.keep
        assert result.relation == ">"
        assert result.standardized_value_nm == pytest.approx(3.9)
        assert result.p_activity is None

    def test_unrecognized_units_kept_but_not_standardized(self):
        percent_binding = {
            **REAL_QUALIFYING_ACTIVITY,
            "standard_type": "IC50",
            "standard_units": "%",
            "standard_value": "23.1",
        }
        result = evaluate_activity(percent_binding)
        assert result.keep
        assert result.unrecognized_units
        assert result.standardized_value_nm is None
        assert result.p_activity is None
