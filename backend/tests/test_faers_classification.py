from backend.app.models.faers import UseClassification
from pipelines.faers.classification import MatchedDrug, classify_report


class TestUnknown:
    def test_no_evidence_is_unknown(self):
        result = classify_report([MatchedDrug(compound_id=1, drugindication=None)], [])
        assert result.use_classification == UseClassification.UNKNOWN
        assert result.confidence == 0.0

    def test_uninformative_indication_is_unknown(self):
        result = classify_report(
            [MatchedDrug(compound_id=1, drugindication="Product used for unknown indication")], []
        )
        assert result.use_classification == UseClassification.UNKNOWN


class TestTherapeutic:
    def test_recognized_indication_classifies_therapeutic(self):
        result = classify_report(
            [MatchedDrug(compound_id=1, drugindication="Hypogonadism")], []
        )
        assert result.use_classification == UseClassification.THERAPEUTIC
        assert result.confidence > 0
        assert any(e["type"] == "therapeutic_indication" for e in result.evidence)

    def test_indication_substring_match_is_case_insensitive(self):
        result = classify_report(
            [MatchedDrug(compound_id=2, drugindication="aplastic ANAEMIA")], []
        )
        assert result.use_classification == UseClassification.THERAPEUTIC


class TestMultiAasExposure:
    def test_two_distinct_compounds_no_other_evidence_is_multi_aas_not_misuse(self):
        result = classify_report(
            [MatchedDrug(compound_id=1), MatchedDrug(compound_id=2)], []
        )
        assert result.use_classification == UseClassification.MULTI_AAS_EXPOSURE

    def test_same_compound_twice_is_not_multi_aas(self):
        # e.g. two formulations of the same parent compound both listed -- not "multiple AAS."
        result = classify_report(
            [MatchedDrug(compound_id=1), MatchedDrug(compound_id=1)], []
        )
        assert result.use_classification == UseClassification.UNKNOWN


class TestMisuse:
    def test_explicit_misuse_reaction_term_classifies_misuse(self):
        result = classify_report([MatchedDrug(compound_id=1)], ["Drug abuse"])
        assert result.use_classification == UseClassification.MISUSE
        assert any(e["type"] == "misuse_reaction_term_high_confidence" for e in result.evidence)

    def test_misuse_term_is_case_insensitive_and_trimmed(self):
        result = classify_report([MatchedDrug(compound_id=1)], ["  intentional overdose  "])
        assert result.use_classification == UseClassification.MISUSE

    def test_multi_aas_alone_never_triggers_misuse(self):
        # Regression guard for the brief's explicit rule: multiple drugs != automatic misuse.
        result = classify_report(
            [MatchedDrug(compound_id=1), MatchedDrug(compound_id=2), MatchedDrug(compound_id=3)], []
        )
        assert result.use_classification != UseClassification.MISUSE
        assert result.use_classification == UseClassification.MULTI_AAS_EXPOSURE

    def test_multi_aas_plus_misuse_term_is_misuse_with_higher_confidence_than_misuse_alone(self):
        single_evidence = classify_report([MatchedDrug(compound_id=1)], ["Drug abuse"])
        combined_evidence = classify_report(
            [MatchedDrug(compound_id=1), MatchedDrug(compound_id=2)], ["Drug abuse"]
        )
        assert combined_evidence.use_classification == UseClassification.MISUSE
        assert combined_evidence.confidence > single_evidence.confidence

    def test_misuse_evidence_takes_precedence_over_therapeutic_indication(self):
        # A report showing BOTH a legitimate indication and explicit misuse evidence must not be
        # classified therapeutic -- misuse evidence is conservative and takes precedence.
        result = classify_report(
            [MatchedDrug(compound_id=1, drugindication="Hypogonadism")], ["Drug abuse"]
        )
        assert result.use_classification == UseClassification.MISUSE


class TestAmbiguousExposure:
    """v2 classifier: terms consistent with misuse but not sufficient alone (module docstring) --
    accidental/unspecified overdose and off-label use both have legitimate non-misuse
    explanations, so neither should classify MISUSE by itself."""

    def test_accidental_overdose_alone_is_ambiguous_not_misuse(self):
        result = classify_report([MatchedDrug(compound_id=1)], ["Accidental overdose"])
        assert result.use_classification == UseClassification.AMBIGUOUS_EXPOSURE
        assert any(e["type"] == "misuse_reaction_term_ambiguous" for e in result.evidence)

    def test_bare_overdose_alone_is_ambiguous_not_misuse(self):
        result = classify_report([MatchedDrug(compound_id=1)], ["Overdose"])
        assert result.use_classification == UseClassification.AMBIGUOUS_EXPOSURE

    def test_unapproved_indication_alone_is_ambiguous_not_misuse(self):
        # Off-label prescribing is legitimate clinical practice, not inherently misuse.
        result = classify_report([MatchedDrug(compound_id=1)], ["Product use in unapproved indication"])
        assert result.use_classification == UseClassification.AMBIGUOUS_EXPOSURE

    def test_ambiguous_term_confidence_is_lower_than_misuse_confidence(self):
        ambiguous = classify_report([MatchedDrug(compound_id=1)], ["Overdose"])
        misuse = classify_report([MatchedDrug(compound_id=1)], ["Drug abuse"])
        assert ambiguous.confidence < misuse.confidence

    def test_high_confidence_term_plus_ambiguous_term_is_still_misuse(self):
        # A high-confidence term gates the decision; an ambiguous term found alongside it still
        # contributes to the evidence trail and confidence, but doesn't change the outcome.
        result = classify_report([MatchedDrug(compound_id=1)], ["Drug abuse", "Overdose"])
        assert result.use_classification == UseClassification.MISUSE
        assert any(e["type"] == "misuse_reaction_term_ambiguous" for e in result.evidence)

    def test_ambiguous_term_takes_precedence_over_therapeutic_indication(self):
        # Real, if weak, misuse-consistent evidence should not be overridden by a therapeutic
        # indication -- mirrors the existing precedence rule for high-confidence misuse terms.
        result = classify_report(
            [MatchedDrug(compound_id=1, drugindication="Hypogonadism")], ["Overdose"]
        )
        assert result.use_classification == UseClassification.AMBIGUOUS_EXPOSURE

    def test_multi_aas_takes_precedence_over_ambiguous_alone(self):
        # Existing multi_aas precedence is unchanged by the new ambiguous tier.
        result = classify_report(
            [MatchedDrug(compound_id=1), MatchedDrug(compound_id=2)], ["Overdose"]
        )
        assert result.use_classification == UseClassification.MULTI_AAS_EXPOSURE


class TestEvidencePreserved:
    def test_evidence_list_is_json_serializable_dicts(self):
        result = classify_report(
            [MatchedDrug(compound_id=1, drugindication="Hypogonadism"), MatchedDrug(compound_id=2)],
            ["Drug abuse"],
        )
        assert isinstance(result.evidence, list)
        for item in result.evidence:
            assert isinstance(item, dict)
            assert "type" in item and "detail" in item

    def test_classifier_version_is_recorded(self):
        result = classify_report([MatchedDrug(compound_id=1)], [])
        assert result.classifier_version == "v2"
