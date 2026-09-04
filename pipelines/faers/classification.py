"""Conservative therapeutic-use-vs-misuse report classification (project brief Sec. 22,
research/exclusion_rules.md Sec. 6).

This is intentionally a small, versioned, DB-independent rule set operating on plain Python
structures (not live ORM objects), so its logic is fully unit-testable
(backend/tests/test_faers_classification.py) and auditable independent of any specific report.

**Never infer misuse solely because the drug is anabolic, and never infer misuse solely because
multiple drugs are co-reported** (project brief Sec. 5/Sec. 22 explicitly forbid both). Multiple
cohort compounds co-reported ("multi-AAS exposure") is tracked as its own category and only
counts as *contributing* evidence toward MISUSE when combined with at least one independent
qualifying evidence type.

**v2 (this version): two-tier misuse evidence, not one flat list.** v1 treated every term in a
single `MISUSE_EVIDENCE_REACTION_TERMS` set as equally strong evidence, including terms that
don't actually imply intentional non-medical use: "accidental overdose" is, by definition, not
intentional; "overdose" alone doesn't say whether it was intentional or a dosing error; "product
use in unapproved indication" describes off-label use, which is legitimate and common in clinical
practice, not inherently misuse. Treating these the same as an explicit "drug abuse" reaction
term risked classifying reports as MISUSE on weak grounds. v2 splits the evidence into
`HIGH_CONFIDENCE_MISUSE_TERMS` (sufficient on their own) and `AMBIGUOUS_EXPOSURE_TERMS`
(suggestive but never sufficient alone -- see `UseClassification.AMBIGUOUS_EXPOSURE`, a new,
separately-tracked outcome for reports whose only positive evidence is ambiguous). This also
matters for H3 (misuse vs. therapeutic AE-category comparison, analysis/misuse_analysis.py): one
high-confidence term, "substance abuse", is *also* a member of the psychiatric AE-category
taxonomy (research/ae_categories.csv), which is a source of classifier-outcome leakage the
misuse_analysis leakage-controlled sensitivity variant is designed to detect and control for.

The term lists below (`HIGH_CONFIDENCE_MISUSE_TERMS`, `AMBIGUOUS_EXPOSURE_TERMS`,
`THERAPEUTIC_INDICATION_TERMS`) are a first-pass curated list, not a database-verified MedDRA
extract -- version-stamped via `CLASSIFIER_VERSION` and documented in pipelines/faers/README.md as
requiring validation against the terms actually observed once real FAERS data was ingested (which
happened for this project; see that README for what was actually found).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.models.faers import UseClassification

CLASSIFIER_VERSION = "v2"

# Reaction (patient.reaction[].reactionmeddrapt) terms treated as sufficient, standalone evidence
# of intentional misuse or non-medical use (exclusion_rules.md Sec. 6). Any one of these present
# is enough to classify MISUSE (subject to the precedence rules in classify_report below).
HIGH_CONFIDENCE_MISUSE_TERMS: frozenset[str] = frozenset({
    "DRUG ABUSE",
    "DRUG ABUSER",
    "SUBSTANCE ABUSE",
    "INTENTIONAL PRODUCT MISUSE",
    "INTENTIONAL OVERDOSE",
    "PRESCRIPTION DRUG USED WITHOUT PRESCRIPTION",
    "ILLICIT DRUG USE",
})

# Reaction terms that are *consistent with* misuse/non-medical use but do not, on their own,
# distinguish it from a legitimate clinical scenario (accidental dosing error, off-label
# prescribing). Never sufficient alone to classify MISUSE -- see UseClassification.AMBIGUOUS_EXPOSURE.
AMBIGUOUS_EXPOSURE_TERMS: frozenset[str] = frozenset({
    "INTENTIONAL PRODUCT USE ISSUE",
    "ACCIDENTAL OVERDOSE",
    "OVERDOSE",
    "PRODUCT USE IN UNAPPROVED INDICATION",
})

# Union of both tiers -- every reaction term this classifier ever treats as misuse-relevant
# evidence of either kind. Exists so callers (analysis/misuse_analysis.py's leakage-controlled
# sensitivity variant) can exclude the full set from AE-category tabulation without importing
# both tier constants and re-deriving the union themselves.
ALL_MISUSE_EVIDENCE_TERMS: frozenset[str] = HIGH_CONFIDENCE_MISUSE_TERMS | AMBIGUOUS_EXPOSURE_TERMS

# Raw patient.drug[].drugindication text (substring, normalized) treated as evidence of a
# legitimate therapeutic indication for this compound class.
THERAPEUTIC_INDICATION_TERMS: frozenset[str] = frozenset({
    "HYPOGONADISM",
    "TESTOSTERONE DEFICIENCY",
    "DELAYED PUBERTY",
    "ANAEMIA",
    "ANEMIA",
    "BREAST CANCER",
    "HEREDITARY ANGIOEDEMA",
    "HIV WASTING SYNDROME",
    "CACHEXIA",
    "OSTEOPOROSIS",
    "MUSCLE WASTING",
    "WEIGHT LOSS",
})

# Literal openFDA drugindication values that mean "no information," not evidence either way.
UNINFORMATIVE_INDICATION_TERMS: frozenset[str] = frozenset({
    "PRODUCT USED FOR UNKNOWN INDICATION",
    "",
})


@dataclass(frozen=True)
class MatchedDrug:
    compound_id: int
    drugindication: str | None = None


@dataclass(frozen=True)
class EvidenceItem:
    type: str
    detail: str


@dataclass(frozen=True)
class ClassificationResult:
    use_classification: UseClassification
    confidence: float
    evidence: list[dict] = field(default_factory=list)
    method: str = "rule_based_v2"
    classifier_version: str = CLASSIFIER_VERSION


def classify_report(matched_drugs: list[MatchedDrug], reaction_terms: list[str]) -> ClassificationResult:
    evidence: list[EvidenceItem] = []

    normalized_reactions = {t.strip().upper() for t in reaction_terms if t}
    high_confidence_found = normalized_reactions & HIGH_CONFIDENCE_MISUSE_TERMS
    ambiguous_found = normalized_reactions & AMBIGUOUS_EXPOSURE_TERMS
    for term in sorted(high_confidence_found):
        evidence.append(EvidenceItem("misuse_reaction_term_high_confidence", term))
    for term in sorted(ambiguous_found):
        evidence.append(EvidenceItem("misuse_reaction_term_ambiguous", term))

    distinct_compounds = {d.compound_id for d in matched_drugs}
    multi_aas = len(distinct_compounds) >= 2
    if multi_aas:
        evidence.append(EvidenceItem("multi_aas_co_reported", f"{len(distinct_compounds)} distinct cohort compounds"))

    therapeutic_terms_found: list[str] = []
    for drug in matched_drugs:
        if not drug.drugindication:
            continue
        indication = drug.drugindication.strip().upper()
        if indication in UNINFORMATIVE_INDICATION_TERMS:
            continue
        for term in THERAPEUTIC_INDICATION_TERMS:
            if term in indication:
                therapeutic_terms_found.append(indication)
                evidence.append(EvidenceItem("therapeutic_indication", indication))
                break

    # --- Decision rule (precedence order; see module docstring) ---
    if high_confidence_found:
        # Multi-AAS and ambiguous-tier terms alone never trigger MISUSE; both only contribute
        # once an independent, sufficient signal (a high-confidence misuse reaction term) is
        # already present.
        n_independent = len(high_confidence_found) + len(ambiguous_found) + (1 if multi_aas else 0)
        confidence = min(0.95, 0.55 + 0.15 * n_independent)
        return ClassificationResult(
            UseClassification.MISUSE, confidence, [e.__dict__ for e in evidence]
        )

    if multi_aas:
        confidence = min(0.9, 0.5 + 0.1 * len(distinct_compounds))
        return ClassificationResult(
            UseClassification.MULTI_AAS_EXPOSURE, confidence, [e.__dict__ for e in evidence]
        )

    if ambiguous_found:
        # Ambiguous-only: real positive evidence, but not sufficient to call it misuse (see
        # module docstring -- e.g. "accidental overdose" or "product use in unapproved
        # indication" have legitimate, non-misuse explanations). Tracked as its own outcome
        # rather than folded into UNKNOWN, so it stays visible and auditable rather than lost.
        confidence = min(0.6, 0.3 + 0.1 * len(ambiguous_found))
        return ClassificationResult(
            UseClassification.AMBIGUOUS_EXPOSURE, confidence, [e.__dict__ for e in evidence]
        )

    if therapeutic_terms_found:
        confidence = min(0.9, 0.5 + 0.1 * len(therapeutic_terms_found))
        return ClassificationResult(
            UseClassification.THERAPEUTIC, confidence, [e.__dict__ for e in evidence]
        )

    return ClassificationResult(UseClassification.UNKNOWN, 0.0, [])
