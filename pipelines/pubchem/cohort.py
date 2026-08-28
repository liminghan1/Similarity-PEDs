"""The initial candidate compound cohort (research/exclusion_rules.md Sec. 1).

This is a starting point, not a guarantee of inclusion in any given analysis -- each compound
must independently satisfy the structural-validity, receptor-coverage, and FAERS-coverage
criteria in research/exclusion_rules.md for each representation it participates in.

`pubchem_query_name` was verified to resolve to a single unambiguous PubChem CID via
PUG REST (`/compound/name/{name}/cids/JSON`) on 2026-08-27 before being hardcoded here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CohortCompound:
    canonical_name: str
    pubchem_query_name: str
    drug_class: str = "anabolic-androgenic steroid"


INITIAL_COHORT: tuple[CohortCompound, ...] = (
    CohortCompound("testosterone", "testosterone"),
    CohortCompound("nandrolone", "nandrolone"),
    CohortCompound("oxandrolone", "oxandrolone"),
    CohortCompound("stanozolol", "stanozolol"),
    CohortCompound("oxymetholone", "oxymetholone"),
    CohortCompound("methandienone", "methandienone"),
    CohortCompound("drostanolone", "drostanolone"),
    CohortCompound("methenolone", "methenolone"),
    CohortCompound("boldenone", "boldenone"),
    CohortCompound("trenbolone", "trenbolone"),
)
