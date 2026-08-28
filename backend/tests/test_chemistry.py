import pytest

from backend.app.analytics.chemistry import (
    InvalidStructureError,
    bemis_murcko_scaffold,
    compute_descriptors,
    compute_inchikey,
    compute_morgan_fingerprint,
    parse_smiles,
    tanimoto_similarity,
)

# PubChem CID 6013. Flat/canonical SMILES (no stereochemistry) is used for the structural
# tests below (formula, descriptors, fingerprints, scaffold), since those properties do not
# depend on stereochemistry. The InChIKey test below uses the isomeric (stereo-defined) SMILES
# instead, since InChIKey's stereo layer depends on it -- verified against the known PubChem
# InChIKey via RDKit before being hardcoded here (see research/literature_review.md sourcing).
TESTOSTERONE_SMILES = "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C"
TESTOSTERONE_ISOMERIC_SMILES = "C[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@]34C)[C@@H]1CC[C@@H]2O"
BENZENE_SMILES = "c1ccccc1"
INVALID_SMILES = "this-is-not-a-molecule("


class TestParseSmiles:
    def test_valid_smiles_parses(self):
        mol = parse_smiles(TESTOSTERONE_SMILES)
        assert mol is not None

    def test_invalid_smiles_raises(self):
        with pytest.raises(InvalidStructureError):
            parse_smiles(INVALID_SMILES)


class TestDescriptors:
    def test_testosterone_formula_and_weight(self):
        desc = compute_descriptors(TESTOSTERONE_SMILES)
        assert desc.molecular_formula == "C19H28O2"
        # Known testosterone MW ~288.42 g/mol; allow tolerance for descriptor rounding.
        assert desc.molecular_weight == pytest.approx(288.42, abs=0.5)

    def test_testosterone_has_one_h_bond_donor(self):
        # a single secondary hydroxyl (17-OH); the 3-keto oxygen is an acceptor, not a donor
        desc = compute_descriptors(TESTOSTERONE_SMILES)
        assert desc.h_bond_donors == 1

    def test_testosterone_ring_count_is_four(self):
        desc = compute_descriptors(TESTOSTERONE_SMILES)
        assert desc.ring_count == 4  # steroid nucleus: three 6-membered + one 5-membered ring

    def test_invalid_smiles_raises(self):
        with pytest.raises(InvalidStructureError):
            compute_descriptors(INVALID_SMILES)


class TestInchikey:
    def test_testosterone_isomeric_inchikey_matches_known_value(self):
        # Known InChIKey for testosterone (PubChem CID 6013 / CAS 58-22-0).
        assert compute_inchikey(TESTOSTERONE_ISOMERIC_SMILES) == "MUMGGOZAMZWBJJ-DYKIIFRCSA-N"

    def test_flat_smiles_gives_same_connectivity_layer(self):
        # The flat (non-stereo) SMILES should still share the first InChIKey block
        # (connectivity layer) with the isomeric form; only the stereo layer differs.
        flat_key = compute_inchikey(TESTOSTERONE_SMILES)
        isomeric_key = compute_inchikey(TESTOSTERONE_ISOMERIC_SMILES)
        assert flat_key.split("-")[0] == isomeric_key.split("-")[0] == "MUMGGOZAMZWBJJ"
        assert flat_key != isomeric_key  # stereo layer must differ


class TestFingerprintsAndSimilarity:
    def test_self_similarity_is_one(self):
        assert tanimoto_similarity(TESTOSTERONE_SMILES, TESTOSTERONE_SMILES) == pytest.approx(1.0)

    def test_dissimilar_structures_have_low_similarity(self):
        sim = tanimoto_similarity(TESTOSTERONE_SMILES, BENZENE_SMILES)
        assert 0.0 <= sim < 0.3

    def test_similarity_is_bounded(self):
        sim = tanimoto_similarity(TESTOSTERONE_SMILES, BENZENE_SMILES)
        assert 0.0 <= sim <= 1.0

    def test_fingerprint_has_requested_length(self):
        fp = compute_morgan_fingerprint(TESTOSTERONE_SMILES, n_bits=1024)
        assert fp.GetNumBits() == 1024


class TestScaffold:
    def test_testosterone_scaffold_parses_and_has_four_rings(self):
        scaffold_smiles = bemis_murcko_scaffold(TESTOSTERONE_SMILES)
        scaffold_desc = compute_descriptors(scaffold_smiles)
        assert scaffold_desc.ring_count == 4

    def test_scaffold_is_smaller_than_parent(self):
        parent = compute_descriptors(TESTOSTERONE_SMILES)
        scaffold_smiles = bemis_murcko_scaffold(TESTOSTERONE_SMILES)
        scaffold = compute_descriptors(scaffold_smiles)
        assert scaffold.molecular_weight < parent.molecular_weight
