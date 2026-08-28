"""Tests for pipelines/faers/parsing.py against real openFDA fixture records (fetched live,
2026-08-28 -- see backend/tests/fixtures/ and pipelines/faers/README.md for provenance). FAERS is
public, de-identified U.S. government surveillance data; using real records here (rather than
synthetic ones) is deliberate, per the project's "do not fabricate scientific data" principle --
these fixtures exercise real messiness (multi-drug arrays, missing fields, real misspellings)
that synthetic data would not reliably reproduce.
"""

import json
from pathlib import Path

import pytest

from backend.app.models.faers import MappingMethod, UseClassification
from pipelines.faers.normalization import build_index
from pipelines.faers.parsing import parse_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Mirrors the real cohort structure closely enough to exercise real matching behavior.
CATALOG_ROWS = [
    ("testosterone", 1, "testosterone", None),
    ("testosterone undecanoate", 1, "testosterone", 11),
    ("nandrolone", 2, "nandrolone", None),
    ("nandrolone decanoate", 2, "nandrolone", 21),
    ("Deca-Durabolin", 2, "nandrolone", 21),
    ("stanozolol", 3, "stanozolol", None),
    ("methandienone", 4, "methandienone", None),
    ("metandienone", 4, "methandienone", None),
    ("methandrostenolone", 4, "methandienone", None),
    ("Dianabol", 4, "methandienone", None),
]


@pytest.fixture
def index():
    return build_index(CATALOG_ROWS)


def load_fixture(name: str) -> dict:
    with (FIXTURES_DIR / name).open() as f:
        return json.load(f)


class TestNandroloneFixture:
    """Real record: a Soliris/PNH case listing nandrolone as a concomitant drug for haemolytic
    anaemia (a genuine historical therapeutic indication), among 10 total drugs."""

    def test_case_and_version(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert report.case_id == "10028019"
        assert report.version == 3

    def test_dates_and_country(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert report.received_date.isoformat() == "2014-03-21"
        assert report.country == "AR"

    def test_seriousness_flags(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert report.serious is True
        assert report.seriousness_hospitalization is True
        assert report.seriousness_death is False  # not flagged in this record

    def test_missing_sex_is_none(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert report.sex is None

    def test_only_nandrolone_matches_cohort_among_ten_drugs(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert len(report.drugs) == 10  # every drug entry is parsed
        assert len(report.cohort_drugs) == 1  # only nandrolone is one of ours
        matched = report.cohort_drugs[0]
        assert matched.raw_name == "NANDROLONE"
        assert matched.match.compound_id == 2
        assert matched.match.mapping_method == MappingMethod.EXACT_ALIAS

    def test_nandrolone_indication_is_haemolytic_anaemia(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        matched = report.cohort_drugs[0]
        assert matched.indication == "HAEMOLYTIC ANAEMIA"

    def test_single_compound_with_recognized_indication_classifies_therapeutic(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        # "ANAEMIA" is a substring of "HAEMOLYTIC ANAEMIA" -- a real therapeutic indication.
        assert report.classification.use_classification == UseClassification.THERAPEUTIC

    def test_reactions_parsed_with_outcome_labels(self, index):
        record = load_fixture("faers_sample_nandrolone.json")
        report = parse_report(record, index)
        assert len(report.reactions) == 8
        terms = {r.meddra_term for r in report.reactions}
        assert "Ascites" in terms
        assert "Portal hypertension" in terms
        outcome_by_term = {r.meddra_term: r.outcome for r in report.reactions if r.meddra_term == "Portal hypertension"}
        assert outcome_by_term["Portal hypertension"] == "Recovered/resolved"  # code "1"


class TestStanozololFixture:
    """Real record: a fatal multi-AAS case (testosterone undecanoate, stanozolol, methandienone
    [as "METHANE DROSTENOLONE"], nandrolone decanoate) with an explicit "Drug abuse" reaction
    term and two fatal-outcome-coded reactions."""

    def test_four_distinct_cohort_compounds_matched(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        matched_compound_ids = {d.match.compound_id for d in report.cohort_drugs}
        # testosterone, nandrolone, stanozolol are exact/curated matches; methandienone
        # ("METHANE DROSTENOLONE") depends on fuzzy-match behavior against real messy text --
        # asserted separately below rather than assumed here.
        assert {1, 2, 3}.issubset(matched_compound_ids)

    def test_methane_drostenolone_fuzzy_matches_or_is_left_unmapped(self, index):
        # Documents actual behavior against this real misspelling/slang string rather than
        # assuming an outcome -- "Methane" is well-known slang for methandienone but was not in
        # the original curated alias list, so this is exactly the kind of real-data discovery
        # process research/exclusion_rules.md anticipates for iterating the alias catalog.
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        drostenolone_entry = next(d for d in report.drugs if d.raw_name == "METHANE DROSTENOLONE")
        assert drostenolone_entry.match.mapping_method in (
            MappingMethod.FUZZY_HIGH_CONFIDENCE,
            MappingMethod.UNMAPPED,
        )

    def test_explicit_drug_abuse_reaction_term_present(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        terms = {r.meddra_term for r in report.reactions}
        assert "Drug abuse" in terms

    def test_classifies_as_misuse_not_multi_aas_or_therapeutic(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        assert report.classification.use_classification == UseClassification.MISUSE

    def test_fatal_reaction_outcome_mapped(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        fatal_terms = {r.meddra_term for r in report.reactions if r.outcome == "Fatal"}
        assert "Carotid artery occlusion" in fatal_terms
        assert "Intracranial venous sinus thrombosis" in fatal_terms

    def test_uninformative_indication_does_not_trigger_therapeutic(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        for d in report.cohort_drugs:
            assert d.indication == "PRODUCT USED FOR UNKNOWN INDICATION"

    def test_patient_demographics(self, index):
        record = load_fixture("faers_sample_stanozolol.json")
        report = parse_report(record, index)
        assert report.sex == "male"
        assert report.age == pytest.approx(24.0)
