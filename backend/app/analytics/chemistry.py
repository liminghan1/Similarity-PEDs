"""RDKit-based structural feature extraction: descriptors, Morgan fingerprints, scaffolds.

Every function here takes a SMILES string and either returns a well-defined result or raises
InvalidStructureError -- it never silently returns a partial/plausible-looking result for an
unparseable structure (research/exclusion_rules.md Sec. 2: structural validity gates inclusion).
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, Lipinski, rdFingerprintGenerator, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold


class InvalidStructureError(ValueError):
    """Raised when a SMILES string cannot be parsed and sanitized by RDKit."""


def parse_smiles(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise InvalidStructureError(f"RDKit could not parse SMILES: {smiles!r}")
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:  # noqa: BLE001 -- re-raised as a typed, project-specific error
        raise InvalidStructureError(f"RDKit could not sanitize SMILES: {smiles!r} ({exc})") from exc
    return mol


@dataclass(frozen=True)
class MolecularDescriptors:
    molecular_formula: str
    molecular_weight: float
    xlogp: float
    tpsa: float
    h_bond_donors: int
    h_bond_acceptors: int
    rotatable_bonds: int
    ring_count: int
    aromatic_ring_count: int
    fraction_csp3: float


def compute_descriptors(smiles: str) -> MolecularDescriptors:
    """Compute the descriptor set listed in the project brief (Sec. 2 Chemical structure)."""
    mol = parse_smiles(smiles)
    return MolecularDescriptors(
        molecular_formula=rdMolDescriptors.CalcMolFormula(mol),
        molecular_weight=Descriptors.MolWt(mol),
        xlogp=Descriptors.MolLogP(mol),
        tpsa=Descriptors.TPSA(mol),
        h_bond_donors=Lipinski.NumHDonors(mol),
        h_bond_acceptors=Lipinski.NumHAcceptors(mol),
        rotatable_bonds=Descriptors.NumRotatableBonds(mol),
        ring_count=rdMolDescriptors.CalcNumRings(mol),
        aromatic_ring_count=rdMolDescriptors.CalcNumAromaticRings(mol),
        fraction_csp3=rdMolDescriptors.CalcFractionCSP3(mol),
    )


def compute_inchikey(smiles: str) -> str:
    mol = parse_smiles(smiles)
    return Chem.MolToInchiKey(mol)


def connectivity_inchikey_block(smiles: str) -> str:
    """The first (connectivity-layer) block of the InChIKey -- 14 characters, stereo-independent
    by construction (InChIKey's second block, not the first, encodes stereochemistry). Used to
    match structures across data sources that may assign stereo descriptors differently or not
    at all (e.g. pipelines/bindingdb/ingest.py matching returned ligand SMILES against our
    cohort), where an exact full-InChIKey match would be too brittle.
    """
    return compute_inchikey(smiles).split("-")[0]


def compute_morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048):
    """Morgan (ECFP-like) fingerprint as an RDKit ExplicitBitVect.

    radius=2, n_bits=2048 is the project's primary structural-similarity fingerprint
    configuration (research/analysis_plan.md Sec. 3).
    """
    mol = parse_smiles(smiles)
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    return generator.GetFingerprint(mol)


def tanimoto_similarity(smiles_a: str, smiles_b: str, radius: int = 2, n_bits: int = 2048) -> float:
    """Tanimoto similarity between Morgan fingerprints of two structures. Bounded [0, 1]."""
    fp_a = compute_morgan_fingerprint(smiles_a, radius=radius, n_bits=n_bits)
    fp_b = compute_morgan_fingerprint(smiles_b, radius=radius, n_bits=n_bits)
    return DataStructs.TanimotoSimilarity(fp_a, fp_b)


def bemis_murcko_scaffold(smiles: str) -> str:
    """Return the canonical SMILES of the Bemis-Murcko scaffold (ring systems + linkers)."""
    mol = parse_smiles(smiles)
    scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    return Chem.MolToSmiles(scaffold)
