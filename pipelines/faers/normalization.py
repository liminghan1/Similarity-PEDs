"""Drug-name normalization: match a raw FAERS `medicinalproduct` string against our cohort's
canonical names / curated aliases / formulation names (project brief Sec. 9).

This module is deliberately DB-independent in its matching logic (`match_drug_name` operates on
a plain `NormalizationIndex` built from query results, not live ORM objects) so it can be unit
tested with fixture data (backend/tests/test_faers_normalization.py) without a database.

Matching tiers, most to least confident (first match wins; see `MatchResult.mapping_method`,
values from `backend.app.models.faers.MappingMethod`):

1. `exact_alias`      -- normalized raw text equals a canonical name, alias, or formulation name
                          exactly (confidence 1.0).
2. `curated_match`     -- the canonical/alias/formulation string appears in the raw text as a
                          whole word/phrase (regex word-boundary match, e.g. "TESTOSTERONE
                          CYPIONATE INJECTION USP" matches "TESTOSTERONE CYPIONATE"). Word
                          boundaries matter: this must NOT match "TESTOSTERONE" inside
                          "METHYLTESTOSTERONE" (a different, non-cohort compound) -- verified by
                          test (confidence 0.9).
3. `normalized_string_match` -- same as (1)/(2) but after aggressively stripping punctuation and
                          trailing dosage-form words (INJECTION, TABLET, SOLUTION, ...) from the
                          raw text first (confidence 0.75).
4. `fuzzy_high_confidence` -- difflib string-similarity ratio >= FUZZY_THRESHOLD against a
                          catalog string, for minor misspellings (confidence = the ratio).
5. `manual_review`     -- reserved for a case this module actively detects as **ambiguous**
                          (the same raw text plausibly matches more than one distinct cohort
                          compound at the same tier) -- flagged for a human, never silently
                          resolved by picking one (project brief: "Never silently resolve
                          ambiguous matches"). This module never assigns `manual_review` to mean
                          "a human already reviewed this" -- only "a human should."
6. `unmapped`          -- no tier matched, OR the raw text matched a `KNOWN_DISTINCT_COMPOUND`
                          block-list entry (see below). `compound_id`/`formulation_id` are None.

When multiple catalog strings match at the same tier, the **longest** (most specific) string
wins, preferring a formulation-scoped match over a parent-level match on a tie in length.

## False-positive guard: `KNOWN_DISTINCT_COMPOUNDS`

Real FAERS data surfaced two genuine false positives from the fuzzy tier during Phase 6
development (2026-08-28), both at ratio ~0.90-0.92, the same range as several *correct* fuzzy
matches (e.g. "TREBELONE ACETATE" -> trenbolone at 0.914) -- so raising `FUZZY_THRESHOLD` would
have also killed those correct matches, not just the bad ones:

- `ANDROSTANOLONE` fuzzy-matched to drostanolone (ratio 0.923), but androstanolone (= stanolone =
  dihydrotestosterone/DHT) is a **chemically distinct** real compound -- drostanolone is
  2alpha-methyl-DHT, one methyl group different, not a spelling variant of DHT (confirmed via web
  search, English Wikipedia "Drostanolone").
- `TRIENOLONE` fuzzy-matched to trenbolone (ratio 0.90), but trienolone (= methyltrienolone =
  metribolone = R1881) is trenbolone's **17-alpha-methylated derivative** -- a distinct,
  orally-active, more hepatotoxic compound with its own separate research/clinical identity
  (confirmed via web search, English Wikipedia "Metribolone").

Both were found by manually inspecting real fuzzy-tier matches after ingestion, not anticipated in
advance -- exactly the kind of real-data quality issue this project's "verify uncertain external
details, do not fabricate" principle exists to catch. Rather than raise the threshold (which would
sacrifice real recall), `KNOWN_DISTINCT_COMPOUNDS` hard-blocks specific confusable strings from
matching *any* tier, checked before all other logic.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from backend.app.models.faers import MappingMethod

FUZZY_THRESHOLD = 0.90

_DOSAGE_FORM_WORDS = {
    "INJECTION", "TABLET", "TABLETS", "CAPSULE", "CAPSULES", "SOLUTION", "SUSPENSION",
    "CREAM", "GEL", "PATCH", "IMPLANT", "PELLET", "PELLETS", "USP", "UNKNOWN", "ORAL",
    "INTRAMUSCULAR", "TOPICAL",
}

# Real, chemically distinct compounds that are NOT in the current cohort but are string-similar
# enough to a cohort compound to risk a fuzzy false-positive match. Forced to UNMAPPED regardless
# of tier. See the module docstring "False-positive guard" section for the two real cases (found
# in live FAERS data) that motivated this list -- extend it if further confusable names are found.
KNOWN_DISTINCT_COMPOUNDS: frozenset[str] = frozenset({
    "ANDROSTANOLONE",  # = stanolone = dihydrotestosterone (DHT); distinct from drostanolone
    "STANOLONE",
    "DIHYDROTESTOSTERONE",
    "TRIENOLONE",  # = methyltrienolone = metribolone = R1881; distinct from trenbolone
    "METHYLTRIENOLONE",
    "METRIBOLONE",
    "R1881",
    "R-1881",
})


@dataclass(frozen=True)
class CatalogEntry:
    text: str  # already normalized (see normalize_text)
    compound_id: int
    compound_name: str
    formulation_id: int | None


@dataclass(frozen=True)
class NormalizationIndex:
    entries: tuple[CatalogEntry, ...]


@dataclass(frozen=True)
class MatchResult:
    compound_id: int | None
    formulation_id: int | None
    mapping_method: MappingMethod
    confidence: float | None
    matched_text: str | None = None


def normalize_text(raw: str) -> str:
    text = raw.strip().upper()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .,;:")
    return text


def _strip_dosage_form_words(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text)  # drop punctuation
    text = re.sub(r"\b\d+(\.\d+)?\s*(MG|MCG|G|ML|MG/ML)\b", " ", text)  # drop dose tokens
    words = [w for w in text.split() if w not in _DOSAGE_FORM_WORDS]
    return normalize_text(" ".join(words))


def build_index(rows: list[tuple[str, int, str, int | None]]) -> NormalizationIndex:
    """`rows`: (raw_catalog_text, compound_id, compound_name, formulation_id) tuples --
    typically the compound's canonical_name (formulation_id=None), every compound_aliases.alias
    (with its formulation_id, possibly None), and every formulations.formulation_name
    (formulation_id=that formulation). Building this from live DB rows happens in ingest.py."""
    entries = tuple(
        CatalogEntry(normalize_text(text), compound_id, compound_name, formulation_id)
        for text, compound_id, compound_name, formulation_id in rows
        if text and text.strip()
    )
    return NormalizationIndex(entries)


def _best_candidate(candidates: list[CatalogEntry]) -> CatalogEntry | None:
    """Longest text wins; ties prefer a formulation-scoped entry."""
    if not candidates:
        return None
    return max(candidates, key=lambda e: (len(e.text), e.formulation_id is not None))


def _distinct_compounds(candidates: list[CatalogEntry]) -> set[int]:
    return {c.compound_id for c in candidates}


def match_drug_name(raw_name: str, index: NormalizationIndex) -> MatchResult:
    if not raw_name or not raw_name.strip():
        return MatchResult(None, None, MappingMethod.UNMAPPED, None)

    normalized_raw = normalize_text(raw_name)

    # Hard block: known chemically-distinct compounds that are string-similar to a cohort
    # compound (see module docstring "False-positive guard"). Checked before every tier.
    if normalized_raw in KNOWN_DISTINCT_COMPOUNDS:
        return MatchResult(None, None, MappingMethod.UNMAPPED, None)

    # Tier 1: exact match.
    exact_candidates = [e for e in index.entries if e.text == normalized_raw]
    if exact_candidates:
        if len(_distinct_compounds(exact_candidates)) > 1:
            return MatchResult(None, None, MappingMethod.MANUAL_REVIEW, None, matched_text=normalized_raw)
        best = _best_candidate(exact_candidates)
        return MatchResult(best.compound_id, best.formulation_id, MappingMethod.EXACT_ALIAS, 1.0, best.text)

    # Tier 2: whole-word/phrase substring match on the raw (lightly normalized) text.
    word_boundary_candidates = [
        e for e in index.entries
        if re.search(rf"\b{re.escape(e.text)}\b", normalized_raw)
    ]
    if word_boundary_candidates:
        if len(_distinct_compounds(word_boundary_candidates)) > 1:
            return MatchResult(None, None, MappingMethod.MANUAL_REVIEW, None, matched_text=normalized_raw)
        best = _best_candidate(word_boundary_candidates)
        return MatchResult(best.compound_id, best.formulation_id, MappingMethod.CURATED_MATCH, 0.9, best.text)

    # Tier 3: aggressive normalization (strip punctuation/dosage-form words), retry exact + substring.
    stripped_raw = _strip_dosage_form_words(raw_name)
    if stripped_raw and stripped_raw in KNOWN_DISTINCT_COMPOUNDS:
        return MatchResult(None, None, MappingMethod.UNMAPPED, None)
    if stripped_raw:
        stripped_candidates = [e for e in index.entries if e.text == stripped_raw]
        if not stripped_candidates:
            stripped_candidates = [
                e for e in index.entries if re.search(rf"\b{re.escape(e.text)}\b", stripped_raw)
            ]
        if stripped_candidates:
            if len(_distinct_compounds(stripped_candidates)) > 1:
                return MatchResult(None, None, MappingMethod.MANUAL_REVIEW, None, matched_text=stripped_raw)
            best = _best_candidate(stripped_candidates)
            return MatchResult(
                best.compound_id, best.formulation_id, MappingMethod.NORMALIZED_STRING_MATCH, 0.75, best.text
            )

    # Tier 4: fuzzy match against the full catalog.
    best_ratio = 0.0
    best_entries: list[CatalogEntry] = []
    for entry in index.entries:
        ratio = difflib.SequenceMatcher(None, normalized_raw, entry.text).ratio()
        if ratio >= FUZZY_THRESHOLD and ratio >= best_ratio:
            if ratio > best_ratio:
                best_entries = []
            best_ratio = ratio
            best_entries.append(entry)
    if best_entries:
        if len(_distinct_compounds(best_entries)) > 1:
            return MatchResult(None, None, MappingMethod.MANUAL_REVIEW, None, matched_text=normalized_raw)
        best = _best_candidate(best_entries)
        return MatchResult(
            best.compound_id, best.formulation_id, MappingMethod.FUZZY_HIGH_CONFIDENCE, best_ratio, best.text
        )

    return MatchResult(None, None, MappingMethod.UNMAPPED, None)
