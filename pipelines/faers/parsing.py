"""Pure parsing of one raw openFDA `/drug/event` JSON record into plain dataclasses, independent
of the database -- so this logic is unit-testable against real fixture records
(backend/tests/test_faers_parsing.py) without a live DB or network call.

FAERS/openFDA field-code conventions used here (patientsex, drugcharacterization) follow the
ICH E2B(R2) individual case safety report standard, the same standard cited for reactionoutcome
in pipelines/faers/reactions.py -- cross-checked, not assumed from a single source.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from pipelines.faers.classification import ClassificationResult, MatchedDrug, classify_report
from pipelines.faers.normalization import MatchResult, NormalizationIndex, match_drug_name
from pipelines.faers.reactions import map_reaction_outcome

_SEX_LABELS = {"1": "male", "2": "female"}
_ROLE_LABELS = {"1": "suspect", "2": "concomitant", "3": "interacting", "4": "not_administered"}


def _parse_fda_date(value: str | None) -> dt.date | None:
    """openFDA dates are YYYYMMDD strings (format code 102) or occasionally partial/invalid."""
    if not value or len(value) != 8:
        return None
    try:
        return dt.datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


@dataclass(frozen=True)
class ParsedDrug:
    raw_name: str
    match: MatchResult
    role: str | None
    indication: str | None


@dataclass(frozen=True)
class ParsedReaction:
    meddra_term: str
    outcome: str | None


@dataclass(frozen=True)
class ParsedReport:
    case_id: str
    version: int | None
    source_report_id: str
    received_date: dt.date | None
    age: float | None
    age_unit: str | None
    sex: str | None
    country: str | None
    serious: bool | None
    seriousness_death: bool | None
    seriousness_hospitalization: bool | None
    drugs: list[ParsedDrug] = field(default_factory=list)
    reactions: list[ParsedReaction] = field(default_factory=list)
    classification: ClassificationResult | None = None

    @property
    def cohort_drugs(self) -> list[ParsedDrug]:
        """Drug entries that matched a cohort compound with a known (non-ambiguous) identity."""
        return [d for d in self.drugs if d.match.compound_id is not None]


def parse_report(record: dict, index: NormalizationIndex) -> ParsedReport:
    patient = record.get("patient", {})

    drugs = []
    for raw_drug in patient.get("drug", []):
        raw_name = raw_drug.get("medicinalproduct") or ""
        match = match_drug_name(raw_name, index)
        drugs.append(
            ParsedDrug(
                raw_name=raw_name,
                match=match,
                role=_ROLE_LABELS.get(raw_drug.get("drugcharacterization")),
                indication=raw_drug.get("drugindication"),
            )
        )

    reactions = [
        ParsedReaction(
            meddra_term=r.get("reactionmeddrapt", ""),
            outcome=map_reaction_outcome(r.get("reactionoutcome")),
        )
        for r in patient.get("reaction", [])
        if r.get("reactionmeddrapt")
    ]

    matched_for_classification = [
        MatchedDrug(compound_id=d.match.compound_id, drugindication=d.indication)
        for d in drugs
        if d.match.compound_id is not None
    ]
    classification = classify_report(
        matched_for_classification, [r.meddra_term for r in reactions]
    )

    version_raw = record.get("safetyreportversion")
    age_raw = patient.get("patientonsetage")

    return ParsedReport(
        case_id=record["safetyreportid"],
        version=int(version_raw) if version_raw and version_raw.isdigit() else None,
        source_report_id=record["safetyreportid"],
        received_date=_parse_fda_date(record.get("receivedate")),
        age=float(age_raw) if age_raw not in (None, "") else None,
        age_unit=patient.get("patientonsetageunit"),
        sex=_SEX_LABELS.get(patient.get("patientsex")),
        country=record.get("occurcountry") or record.get("primarysourcecountry"),
        serious=record.get("serious") == "1",
        seriousness_death=record.get("seriousnessdeath") == "1",
        seriousness_hospitalization=record.get("seriousnesshospitalization") == "1",
        drugs=drugs,
        reactions=reactions,
        classification=classification,
    )
