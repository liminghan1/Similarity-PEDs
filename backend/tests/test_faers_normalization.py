import pytest

from backend.app.models.faers import MappingMethod
from pipelines.faers.normalization import build_index, match_drug_name, normalize_text

# A small synthetic catalog mirroring the real cohort structure: two compounds, each with a
# canonical name, one formulation, and one formulation-scoped brand alias, plus one parent-level
# alias. (raw_catalog_text, compound_id, compound_name, formulation_id)
CATALOG_ROWS = [
    ("testosterone", 1, "testosterone", None),
    ("Test", 1, "testosterone", None),  # parent-level abbreviation alias
    ("testosterone cypionate", 1, "testosterone", 101),  # formulation
    ("Depo-Testosterone", 1, "testosterone", 101),  # formulation-scoped brand alias
    ("nandrolone", 2, "nandrolone", None),
    ("nandrolone decanoate", 2, "nandrolone", 201),  # formulation
    ("Deca-Durabolin", 2, "nandrolone", 201),  # formulation-scoped brand alias
    ("Deca", 2, "nandrolone", 201),  # formulation-scoped abbreviation
    ("drostanolone", 3, "drostanolone", None),
    ("dromostanolone", 3, "drostanolone", None),  # real USAN synonym, confirmed via live FAERS data
    ("trenbolone", 4, "trenbolone", None),
]


@pytest.fixture
def index():
    return build_index(CATALOG_ROWS)


class TestNormalizeText:
    def test_uppercases_and_strips(self):
        assert normalize_text("  testosterone  ") == "TESTOSTERONE"

    def test_collapses_whitespace(self):
        assert normalize_text("testosterone   cypionate") == "TESTOSTERONE CYPIONATE"

    def test_strips_trailing_punctuation(self):
        assert normalize_text("nandrolone.") == "NANDROLONE"


class TestExactMatch:
    def test_canonical_name_exact_match(self, index):
        result = match_drug_name("testosterone", index)
        assert result.mapping_method == MappingMethod.EXACT_ALIAS
        assert result.compound_id == 1
        assert result.formulation_id is None
        assert result.confidence == pytest.approx(1.0)

    def test_case_insensitive(self, index):
        result = match_drug_name("TESTOSTERONE", index)
        assert result.mapping_method == MappingMethod.EXACT_ALIAS
        assert result.compound_id == 1

    def test_formulation_scoped_brand_alias_resolves_formulation(self, index):
        result = match_drug_name("Deca-Durabolin", index)
        assert result.mapping_method == MappingMethod.EXACT_ALIAS
        assert result.compound_id == 2
        assert result.formulation_id == 201

    def test_parent_level_alias_has_no_formulation(self, index):
        result = match_drug_name("Test", index)
        assert result.compound_id == 1
        assert result.formulation_id is None


class TestCuratedMatch:
    def test_dosage_suffixed_text_matches_formulation_name(self, index):
        result = match_drug_name("TESTOSTERONE CYPIONATE INJECTION 200MG/ML", index)
        assert result.mapping_method == MappingMethod.CURATED_MATCH
        assert result.compound_id == 1
        assert result.formulation_id == 101

    def test_prefers_more_specific_formulation_match_over_parent(self, index):
        # Raw text contains both "nandrolone" and "nandrolone decanoate" as substrings --
        # the longer, formulation-scoped match should win.
        result = match_drug_name("NANDROLONE DECANOATE INJECTION USP", index)
        assert result.formulation_id == 201

    def test_does_not_false_positive_on_fused_compound_name(self, index):
        # "METHYLTESTOSTERONE" contains "TESTOSTERONE" as a raw substring but NOT as a separate
        # word -- must not match, since methyltestosterone is a different, non-cohort compound.
        result = match_drug_name("METHYLTESTOSTERONE", index)
        assert result.mapping_method != MappingMethod.CURATED_MATCH
        assert result.mapping_method != MappingMethod.EXACT_ALIAS
        assert result.compound_id is None


class TestNormalizedStringMatch:
    def test_punctuation_and_dosage_words_stripped(self, index):
        result = match_drug_name("NANDROLONE.", index)
        # "NANDROLONE." normalizes (tier 1) to "NANDROLONE" which already matches exactly --
        # use a case that truly needs tier-3 stripping instead.
        assert result.compound_id == 2

    def test_tier_three_after_removing_dosage_words(self, index):
        result = match_drug_name("NANDROLONE, TABLET, UNKNOWN", index)
        assert result.compound_id == 2
        assert result.mapping_method in (
            MappingMethod.CURATED_MATCH,
            MappingMethod.NORMALIZED_STRING_MATCH,
            MappingMethod.EXACT_ALIAS,
        )


class TestFuzzyMatch:
    def test_minor_misspelling_matches_with_high_confidence(self, index):
        result = match_drug_name("NANDROLOEN", index)  # transposed letters
        assert result.mapping_method == MappingMethod.FUZZY_HIGH_CONFIDENCE
        assert result.compound_id == 2
        assert result.confidence >= 0.90

    def test_dissimilar_text_does_not_fuzzy_match(self, index):
        result = match_drug_name("XYZQWERTY", index)
        assert result.mapping_method == MappingMethod.UNMAPPED

    def test_real_usan_synonym_dromostanolone_matches_drostanolone(self, index):
        # Not actually a fuzzy match here (it's in the catalog as a curated synonym), but
        # documents the real, confirmed-correct case alongside the false positives below.
        result = match_drug_name("DROMOSTANOLONE", index)
        assert result.compound_id == 3


class TestKnownDistinctCompoundGuard:
    """Regression tests for two real false positives found in live FAERS data during Phase 6
    (see normalization.py's "False-positive guard" docstring section): both had a fuzzy-match
    ratio in the same 0.90-0.92 range as genuinely correct matches, so the fix is a targeted
    block-list, not a raised threshold."""

    def test_androstanolone_does_not_match_drostanolone(self, index):
        # Androstanolone = DHT, a chemically distinct compound from drostanolone (2a-methyl-DHT).
        result = match_drug_name("ANDROSTANOLONE", index)
        assert result.mapping_method == MappingMethod.UNMAPPED
        assert result.compound_id is None

    def test_androstanolone_with_trailing_period_does_not_match(self, index):
        # The actual raw FAERS string that surfaced this bug.
        result = match_drug_name("ANDROSTANOLONE.", index)
        assert result.mapping_method == MappingMethod.UNMAPPED

    def test_trienolone_does_not_match_trenbolone(self, index):
        # Trienolone = methyltrienolone/metribolone/R1881, trenbolone's 17-alpha-methylated,
        # orally-active derivative -- a distinct compound, not a spelling variant.
        result = match_drug_name("TRIENOLONE", index)
        assert result.mapping_method == MappingMethod.UNMAPPED
        assert result.compound_id is None

    def test_methyltrienolone_does_not_match_trenbolone(self, index):
        result = match_drug_name("METHYLTRIENOLONE", index)
        assert result.mapping_method == MappingMethod.UNMAPPED


class TestUnmapped:
    def test_unrelated_drug_is_unmapped(self, index):
        result = match_drug_name("ASPIRIN", index)
        assert result.mapping_method == MappingMethod.UNMAPPED
        assert result.compound_id is None
        assert result.formulation_id is None

    def test_empty_string_is_unmapped(self, index):
        result = match_drug_name("", index)
        assert result.mapping_method == MappingMethod.UNMAPPED

    def test_whitespace_only_is_unmapped(self, index):
        result = match_drug_name("   ", index)
        assert result.mapping_method == MappingMethod.UNMAPPED


class TestAmbiguousMatch:
    def test_same_text_matching_two_compounds_is_flagged_manual_review(self):
        ambiguous_index = build_index([
            ("Andro", 1, "testosterone", None),
            ("Andro", 3, "androstenedione", None),  # hypothetical second compound, same alias
        ])
        result = match_drug_name("Andro", ambiguous_index)
        assert result.mapping_method == MappingMethod.MANUAL_REVIEW
        assert result.compound_id is None
