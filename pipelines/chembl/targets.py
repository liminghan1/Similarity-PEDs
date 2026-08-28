"""The 6 receptor targets this project collects bioactivity for (project brief Sec. 2).

Every target_chembl_id below was confirmed via a live query to
GET /chembl/api/data/target/search.json?q=... (AR/PR/GR/MR) or
GET /chembl/api/data/target.json?target_synonym__icontains=ESR1|ESR2 (ERalpha/ERbeta, since a
plain-text search for "estrogen receptor alpha/beta" surfaces the ERR1 orphan receptor and the
combined "Estrogen receptor" PROTEIN FAMILY entry ahead of the correct SINGLE PROTEIN target) on
2026-08-27, filtered to organism == "Homo sapiens" and target_type == "SINGLE PROTEIN" -- not
copied from memory or documentation. See pipelines/chembl/README.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReceptorTarget:
    short_name: str
    gene_symbol: str
    full_name: str
    chembl_target_id: str
    organism: str = "Homo sapiens"


RECEPTOR_TARGETS: tuple[ReceptorTarget, ...] = (
    ReceptorTarget("AR", "AR", "Androgen receptor", "CHEMBL1871"),
    ReceptorTarget("PR", "PGR", "Progesterone receptor", "CHEMBL208"),
    ReceptorTarget("GR", "NR3C1", "Glucocorticoid receptor", "CHEMBL2034"),
    ReceptorTarget("MR", "NR3C2", "Mineralocorticoid receptor", "CHEMBL1994"),
    ReceptorTarget("ERalpha", "ESR1", "Estrogen receptor", "CHEMBL206"),
    ReceptorTarget("ERbeta", "ESR2", "Estrogen receptor beta", "CHEMBL242"),
)
