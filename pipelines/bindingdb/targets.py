"""The same 6 receptor targets as pipelines/chembl/targets.py, keyed by UniProt accession
(BindingDB's REST API is queried by UniProt ID, not ChEMBL target ID).

Every accession was cross-checked against ChEMBL's own target-component UniProt cross-references
(GET /chembl/api/data/target.json?target_chembl_id=...) on 2026-08-27, not copied from memory --
e.g. CHEMBL1871 (Androgen receptor, Homo sapiens) cross-references UniProt P10275, matching the
commonly-cited AR accession. See pipelines/bindingdb/README.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BindingDbTarget:
    short_name: str
    full_name: str
    uniprot_id: str


BINDINGDB_TARGETS: tuple[BindingDbTarget, ...] = (
    BindingDbTarget("AR", "Androgen receptor", "P10275"),
    BindingDbTarget("PR", "Progesterone receptor", "P06401"),
    BindingDbTarget("GR", "Glucocorticoid receptor", "P04150"),
    BindingDbTarget("MR", "Mineralocorticoid receptor", "P08235"),
    BindingDbTarget("ERalpha", "Estrogen receptor alpha", "P03372"),
    BindingDbTarget("ERbeta", "Estrogen receptor beta", "Q92731"),
)
