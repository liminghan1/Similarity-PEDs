"""Maps FAERS/openFDA's numeric `reactionoutcome` code to a human-readable label.

Code definitions per the ICH E2B(R2) individual case safety report standard, which FAERS follows
(cross-checked via web search against multiple independent FAERS-analysis papers describing this
exact 6-point scale, 2026-08-28 -- see pipelines/faers/README.md; no single official FDA data
dictionary page enumerating the codes could be located, so this is documented as a
well-corroborated but not directly-quoted-from-FDA mapping). An unrecognized code is preserved
as raw text (`"code_<n>"`) rather than guessed at or silently dropped.
"""

REACTION_OUTCOME_LABELS: dict[str, str] = {
    "1": "Recovered/resolved",
    "2": "Recovering/resolving",
    "3": "Not recovered/not resolved",
    "4": "Recovered/resolved with sequelae",
    "5": "Fatal",
    "6": "Unknown",
}


def map_reaction_outcome(code: str | None) -> str | None:
    if code is None:
        return None
    return REACTION_OUTCOME_LABELS.get(code, f"code_{code}")
