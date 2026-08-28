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

The term lists below (`MISUSE_EVIDENCE_REACTION_TERMS`, `THERAPEUTIC_INDICATION_TERMS`) are a
first-pass curated list, not a database-verified MedDRA extract -- version-stamped via
`CLASSIFIER_VERSION` and documented in pipelines/faers/README.md as requiring validation against
the terms actually observed once real FAERS data was ingested (which happened for this project;
see that README for what was actually found and whether the list needed adjustment).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.models.faers import UseClassification

CLASSIFIER_VERSION = "v1"

# Reaction (patient.reaction[].reactionmeddrapt) terms treated as direct evidence of misuse,
# intentional/product-use-error, or supratherapeutic exposure (exclusion_rules.md Sec. 6).
MISUSE_EVIDENCE_REACTION_TERMS: frozenset[str] = frozenset({
    "DRUG ABUSE",
    "DRUG ABUSER",
    "SUBSTANCE ABUSE",
    "INTENTIONAL PRODUCT MISUSE",
    "INTENTIONAL PRODUCT USE ISSUE",
    "INTENTIONAL OVERDOSE",
    "ACCIDENTAL OVERDOSE",
    "OVERDOSE",
    "PRESCRIPTION DRUG USED WITHOUT PRESCRIPTION",
    "ILLICIT DRUG USE",
    "PRODUCT USE IN UNAPPROVED INDICATION",
})

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
    method: str = "rule_based_v1"
    classifier_version: str = CLASSIFIER_VERSION


def classify_report(matched_drugs: list[MatchedDrug], reaction_terms: list[str]) -> ClassificationResult:
    evidence: list[EvidenceItem] = []

    normalized_reactions = {t.strip().upper() for t in reaction_terms if t}
    misuse_terms_found = normalized_reactions & MISUSE_EVIDENCE_REACTION_TERMS
    for term in sorted(misuse_terms_found):
        evidence.append(EvidenceItem("misuse_reaction_term", term))

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
    if misuse_terms_found:
        # Multi-AAS alone never triggers MISUSE; it only contributes once an independent
        # qualifying signal (a real misuse reaction term) is already present.
        n_independent = len(misuse_terms_found) + (1 if multi_aas else 0)
        confidence = min(0.95, 0.55 + 0.15 * n_independent)
        return ClassificationResult(
            UseClassification.MISUSE, confidence, [e.__dict__ for e in evidence]
        )

    if multi_aas:
        confidence = min(0.9, 0.5 + 0.1 * len(distinct_compounds))
        return ClassificationResult(
            UseClassification.MULTI_AAS_EXPOSURE, confidence, [e.__dict__ for e in evidence]
        )

    if therapeutic_terms_found:
        confidence = min(0.9, 0.5 + 0.1 * len(therapeutic_terms_found))
        return ClassificationResult(
            UseClassification.THERAPEUTIC, confidence, [e.__dict__ for e in evidence]
        )

    return ClassificationResult(UseClassification.UNKNOWN, 0.0, [])
