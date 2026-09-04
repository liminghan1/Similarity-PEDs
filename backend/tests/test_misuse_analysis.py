from decimal import Decimal

import pandas as pd
import pytest
from sqlalchemy import event

from analysis.misuse_analysis import (
    compare_ae_categories,
    compare_binary_outcome,
    compare_demographics,
    load_report_categories,
)
from backend.app.db.session import SessionLocal, engine
from backend.app.models.faers import FaersReaction, FaersReport, UseClassification

# Plain .value strings, not the raw enum members: pandas' string-dtype inference calls str() on
# column elements, and a `str, Enum` mixin's __str__ returns "UseClassification.MISUSE", not the
# value "misuse" -- see the note in analysis/misuse_analysis.py::load_group_report_table.
MISUSE = UseClassification.MISUSE.value
THERAPEUTIC = UseClassification.THERAPEUTIC.value


@pytest.fixture
def synthetic_reports():
    # 6 misuse reports: 4 serious, 2 not. 6 therapeutic reports: 1 serious, 5 not.
    return pd.DataFrame(
        {
            "report_id": list(range(1, 13)),
            "group": [MISUSE] * 6 + [THERAPEUTIC] * 6,
            "serious": [True, True, True, True, False, False, True, False, False, False, False, False],
            "hospitalization": [True, False, True, False, False, False, False, False, False, False, False, False],
            "death": [False] * 12,
            "age": [25, 30, 22, 28, 35, 40, 50, 55, 60, 45, 52, 48],
            "sex": ["male"] * 5 + [None] + ["female"] * 6,
        }
    )


class TestCompareBinaryOutcome:
    def test_counts_and_proportions_correct(self, synthetic_reports):
        result = compare_binary_outcome(synthetic_reports, "serious")
        assert result["misuse_n"] == 6
        assert result["therapeutic_n"] == 6
        assert result["misuse_count"] == 4
        assert result["therapeutic_count"] == 1
        assert result["misuse_proportion"] == pytest.approx(4 / 6)
        assert result["therapeutic_proportion"] == pytest.approx(1 / 6)

    def test_odds_ratio_matches_hand_calculation(self, synthetic_reports):
        # a=4 (misuse+serious), b=2 (misuse+not), c=1 (therapeutic+serious), d=5 (therapeutic+not)
        # OR = (4*5)/(2*1) = 10
        result = compare_binary_outcome(synthetic_reports, "serious")
        assert result["odds_ratio"] == pytest.approx(10.0)

    def test_ci_brackets_the_point_estimate(self, synthetic_reports):
        result = compare_binary_outcome(synthetic_reports, "serious")
        assert result["ci_low"] < result["odds_ratio"] < result["ci_high"]

    def test_fisher_p_value_is_valid_probability(self, synthetic_reports):
        result = compare_binary_outcome(synthetic_reports, "hospitalization")
        assert 0.0 <= result["fisher_p_value"] <= 1.0

    def test_no_events_in_either_group_does_not_crash(self, synthetic_reports):
        result = compare_binary_outcome(synthetic_reports, "death")
        assert result["misuse_count"] == 0
        assert result["therapeutic_count"] == 0


class TestCompareAeCategories:
    def test_category_counts_correct(self, synthetic_reports):
        # Cardiovascular reaction present in reports 1,2,7 (2 misuse, 1 therapeutic).
        report_categories = pd.DataFrame(
            {"report_id": [1, 2, 7], "category": ["cardiovascular"] * 3}
        )
        table = compare_ae_categories(synthetic_reports, report_categories, ["cardiovascular", "hepatic"])
        row = table[table["category"] == "cardiovascular"].iloc[0]
        assert row["misuse_count"] == 2
        assert row["therapeutic_count"] == 1

    def test_category_with_zero_occurrences_handled(self, synthetic_reports):
        report_categories = pd.DataFrame({"report_id": [], "category": []})
        table = compare_ae_categories(synthetic_reports, report_categories, ["hepatic"])
        row = table[table["category"] == "hepatic"].iloc[0]
        assert row["misuse_count"] == 0
        assert row["therapeutic_count"] == 0

    def test_sorted_by_p_value_ascending(self, synthetic_reports):
        report_categories = pd.DataFrame(
            {"report_id": [1, 2, 3, 4, 5, 6], "category": ["cardiovascular"] * 6}
        )
        table = compare_ae_categories(synthetic_reports, report_categories, ["cardiovascular", "renal"])
        assert table.iloc[0]["fisher_p_value"] <= table.iloc[1]["fisher_p_value"]


class TestCompareAeCategoriesFdrCorrection:
    """Regression coverage for the BH-FDR fix: research/hypotheses.md's H3 falsifiability clause
    requires surviving multiple-comparison correction, but the code previously only ever reported
    raw Fisher p-values, and reports/research_report.md counted "7/11 categories significant" on
    raw p<0.05 alone -- inconsistent with the pre-registered plan."""

    def test_adds_fdr_columns(self, synthetic_reports):
        report_categories = pd.DataFrame({"report_id": [1, 2, 7], "category": ["cardiovascular"] * 3})
        table = compare_ae_categories(synthetic_reports, report_categories, ["cardiovascular", "hepatic"])
        assert "fdr_q_value" in table.columns
        assert "significant_fdr_05" in table.columns

    def test_fdr_q_value_never_smaller_than_raw_p(self, synthetic_reports):
        report_categories = pd.DataFrame({"report_id": list(range(1, 7)), "category": ["cardiovascular"] * 6})
        table = compare_ae_categories(
            synthetic_reports,
            report_categories,
            ["cardiovascular", "hepatic", "renal", "endocrine", "reproductive"],
        )
        assert (table["fdr_q_value"] >= table["fisher_p_value"] - 1e-9).all()

    def test_fdr_significant_implies_raw_p_significant(self, synthetic_reports):
        report_categories = pd.DataFrame({"report_id": list(range(1, 7)), "category": ["cardiovascular"] * 6})
        table = compare_ae_categories(
            synthetic_reports,
            report_categories,
            ["cardiovascular", "hepatic", "renal", "endocrine", "reproductive"],
        )
        significant = table[table["significant_fdr_05"]]
        assert (significant["fisher_p_value"] < 0.05).all()

    def test_correction_overturns_a_raw_significant_result_when_testing_many_categories(self, synthetic_reports):
        # cardiovascular is present in 5/6 misuse reports and 0/6 therapeutic reports here:
        # Fisher p=0.0152 (raw-significant at p<0.05) but, tested alongside 5 other categories
        # with no association at all, BH-FDR q=0.0909 (not significant) -- exactly the scenario
        # that made the uncorrected "7/11 categories significant" claim in the research report
        # inconsistent with the pre-registered plan.
        report_categories = pd.DataFrame({"report_id": [1, 2, 3, 4, 5], "category": ["cardiovascular"] * 5})
        table = compare_ae_categories(
            synthetic_reports,
            report_categories,
            ["cardiovascular", "hepatic", "renal", "endocrine", "reproductive", "metabolic"],
        )
        cardio = table[table["category"] == "cardiovascular"].iloc[0]
        assert cardio["fisher_p_value"] == pytest.approx(0.0152, abs=1e-3)
        assert cardio["fisher_p_value"] < 0.05
        assert cardio["fdr_q_value"] > 0.05
        assert not cardio["significant_fdr_05"]


class TestLoadReportCategoriesExcludeTerms:
    """Regression coverage for the leakage-control fix: pipelines/faers/classification.py's
    "substance abuse" is both misuse-classification evidence and a research/ae_categories.csv
    "psychiatric" entry, so a report could count toward the psychiatric AE-category outcome for
    no reason other than the same term that got it labeled MISUSE in the first place."""

    @pytest.fixture
    def db_session(self):
        connection = engine.connect()
        outer_transaction = connection.begin()
        session = SessionLocal(bind=connection)
        nested = connection.begin_nested()

        @event.listens_for(session, "after_transaction_end")
        def _restart_savepoint(sess, transaction):
            nonlocal nested
            if not nested.is_active:
                nested = connection.begin_nested()

        try:
            yield session
        finally:
            session.close()
            outer_transaction.rollback()
            connection.close()

    def test_excluded_term_does_not_contribute_a_category_row(self, db_session):
        report = FaersReport(case_id="case-leakage-test-1", version=1, source_report_id="src-1")
        db_session.add(report)
        db_session.flush()
        db_session.add_all(
            [
                FaersReaction(report_id=report.id, meddra_term="substance abuse"),
                FaersReaction(report_id=report.id, meddra_term="anxiety"),
            ]
        )
        db_session.commit()

        category_map = {"substance abuse": {"psychiatric"}, "anxiety": {"psychiatric"}}

        without_exclusion = load_report_categories(db_session, category_map)
        assert (without_exclusion["report_id"] == report.id).sum() >= 1
        rows = without_exclusion[without_exclusion["report_id"] == report.id]
        assert set(rows["category"]) == {"psychiatric"}

        with_exclusion = load_report_categories(
            db_session, category_map, exclude_terms=frozenset({"SUBSTANCE ABUSE"})
        )
        rows_excluded = with_exclusion[with_exclusion["report_id"] == report.id]
        # "anxiety" is an independent, non-excluded term that also maps to psychiatric, so the
        # category row survives -- only the excluded term's own contribution is removed.
        assert set(rows_excluded["category"]) == {"psychiatric"}

    def test_excluding_the_only_qualifying_term_removes_the_category_row(self, db_session):
        report = FaersReport(case_id="case-leakage-test-2", version=1, source_report_id="src-2")
        db_session.add(report)
        db_session.flush()
        db_session.add(FaersReaction(report_id=report.id, meddra_term="substance abuse"))
        db_session.commit()

        category_map = {"substance abuse": {"psychiatric"}}

        with_exclusion = load_report_categories(
            db_session, category_map, exclude_terms=frozenset({"SUBSTANCE ABUSE"})
        )
        assert not (with_exclusion["report_id"] == report.id).any()


class TestCompareDemographics:
    def test_age_medians_computed_per_group(self, synthetic_reports):
        result = compare_demographics(synthetic_reports)
        assert result["age"]["misuse_n_with_age"] == 6

    def test_decimal_age_values_do_not_crash_mannwhitney(self):
        # Regression guard: FaersReport.age is a Postgres NUMERIC column, returned as
        # decimal.Decimal by psycopg -- scipy's mannwhitneyu (via np.isnan) cannot operate on an
        # object-dtype array of Decimals. load_group_report_table() converts age via
        # pd.to_numeric() before this function ever sees it; this test locks in that the fix
        # actually resolves the failure mode found running against the live database, using
        # pd.to_numeric the same way the loader does rather than assuming plain floats.
        df = pd.DataFrame(
            {
                "report_id": [1, 2, 3, 4, 5, 6],
                "group": [MISUSE] * 3 + [THERAPEUTIC] * 3,
                "serious": [True] * 6,
                "hospitalization": [False] * 6,
                "death": [False] * 6,
                "age": [Decimal("25"), Decimal("30"), None, Decimal("40"), Decimal("45"), Decimal("50")],
                "sex": [None] * 6,
            }
        )
        df["age"] = pd.to_numeric(df["age"], errors="coerce")
        result = compare_demographics(df)  # must not raise
        assert result["age"]["misuse_n_with_age"] == 2
        assert result["age"]["therapeutic_n_with_age"] == 3

    def test_sex_table_excludes_missing_values(self, synthetic_reports):
        result = compare_demographics(synthetic_reports)
        # One misuse report has sex=None -- must not appear as its own category.
        table = result["sex"]["table"]
        all_sexes = {sex for group_dict in table.values() for sex in group_dict}
        assert None not in all_sexes
