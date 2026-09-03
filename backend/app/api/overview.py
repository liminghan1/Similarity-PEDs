from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import Compound, FaersReport
from backend.app.services.artifacts import ArtifactNotFoundError, load_json_artifact

router = APIRouter(prefix="/api/overview", tags=["overview"])

RESEARCH_QUESTION = (
    "Are anabolic-androgenic steroids with similar molecular structures and receptor "
    "pharmacology associated with similar real-world adverse-event reporting profiles?"
)

AIMS = [
    {
        "aim": 1,
        "title": "Molecular and pharmacological phenotype",
        "summary": "Construct a molecular/pharmacological representation of each compound: "
        "chemical structure (PubChem/RDKit) and receptor pharmacology (ChEMBL/BindingDB).",
    },
    {
        "aim": 2,
        "title": "Real-world adverse-event phenotype",
        "summary": "Construct a FAERS-derived adverse-event reporting phenotype per compound, "
        "using research-defined categories -- never described as incidence, risk, or a causal effect.",
    },
    {
        "aim": 3,
        "title": "Structure/pharmacology to safety",
        "summary": "Test whether pairwise molecular/pharmacological similarity is associated "
        "with pairwise safety-reporting-profile similarity via a permutation-based matrix-"
        "association test (H1/H2).",
    },
    {
        "aim": 4,
        "title": "Therapeutic use vs. misuse",
        "summary": "Compare adverse-event reporting phenotypes between conservatively-classified "
        "therapeutic-use-associated and misuse-associated reports (H3).",
    },
]

HYPOTHESES = [
    {"id": "H1", "label": "PRIMARY", "statement": "Compounds more similar in receptor pharmacology will show more similar safety reporting profiles.", "status": "NOT COMPUTABLE with current receptor-bioactivity coverage."},
    {"id": "H2", "label": "SECONDARY", "statement": "Structural similarity alone will explain less safety-profile variation than a combined structure+receptor representation.", "status": "Structure-only tested: no significant association found."},
    {"id": "H3", "label": "SECONDARY", "statement": "Therapeutic-use-associated and misuse-associated reports will show measurably different safety reporting phenotypes.", "status": "Supported: significant differences found in seriousness, hospitalization, and AE-category patterns."},
    {"id": "H4", "label": "EXPLORATORY", "statement": "Specific pharmacological features will associate with specific adverse-event categories.", "status": "Adapted to molecular descriptors (receptor data infeasible); no category showed a significant association."},
]

MAJOR_LIMITATIONS = [
    "FAERS is a voluntary, spontaneous reporting system: it cannot establish incidence, "
    "prevalence, absolute risk, or causation. Every statistic here is a reporting association.",
    "Receptor bioactivity coverage is sparse: 7/10 cohort compounds have zero measurements "
    "against any of the six receptors queried (ChEMBL/BindingDB), preventing the primary "
    "analysis (H1) entirely.",
    "Small compound cohort (n=10) limits statistical power for every matrix-association and "
    "multivariate analysis.",
    "The safety-phenotype background is cohort-relative: testosterone contributes 75% of total "
    "report volume, which can mechanically influence every other compound's relative signal.",
    "Confounding (age, sex, indication, polypharmacy, other PED exposure, reporting bias, "
    "product provenance) is not adjusted for anywhere in this project.",
    "Research-defined adverse-event categories are a curated taxonomy, not an official "
    "licensed MedDRA hierarchy.",
]


@router.get("")
def get_overview(db: Session = Depends(get_db)) -> dict:
    n_compounds = db.query(Compound).count()
    n_faers_reports = db.query(FaersReport).filter(FaersReport.is_deduplicated_latest.is_(True)).count()

    try:
        manifest = load_json_artifact("dataset_manifest")
        n_compounds_min_reports = len(manifest.get("compounds_meeting_minimum_reports", []))
        n_ae_categories = len(manifest.get("ae_categories", []))
    except ArtifactNotFoundError:
        n_compounds_min_reports = None
        n_ae_categories = None

    return {
        "research_question": RESEARCH_QUESTION,
        "aims": AIMS,
        "hypotheses": HYPOTHESES,
        "dataset_sizes": {
            "n_compounds": n_compounds,
            "n_faers_reports": n_faers_reports,
            "n_compounds_meeting_faers_minimum": n_compounds_min_reports,
            "n_ae_categories": n_ae_categories,
        },
        "major_limitations": MAJOR_LIMITATIONS,
        "not_a_ped_tool_notice": (
            "This project does not build cycle builders, dose calculators, 'safest/best "
            "steroid' rankings, stacking recommendations, or novel compound design. See "
            "the Limitations page and research/exclusion_rules.md."
        ),
    }
