# Literature Review (Scaffold — First Pass)

**Status:** First-pass, non-exhaustive structured search performed via general web search (not yet a formal
indexed-database systematic search of PubMed/Embase/Scopus with a registered search string). This is sufficient
to avoid an unsupported novelty claim but **should be supplemented** with a formal PubMed search (via NCBI
E-utilities or manual PubMed queries) before any manuscript-facing claim is finalized. That upgrade is tracked in
`TODO.md`.

**Database/tool searched:** General web search (search engine aggregating indexed sources including PubMed,
PMC, journal publisher sites, and preprint servers). Individual results below are predominantly PubMed/PMC-indexed
or peer-reviewed journal articles; a few are preprints (medRxiv) or non-peer-reviewed aggregator pages
(academia.edu mirrors of published papers), noted as such.

**Date searched:** 2026-08-27

**Search terms used (from the required topic list):**
1. `anabolic androgenic steroid FAERS pharmacovigilance adverse event reporting`
2. `anabolic steroid receptor selectivity computational structure activity relationship QSAR`
3. `molecular similarity chemical structure adverse event profile prediction drug target`
4. `disproportionality analysis reporting odds ratio FAERS openFDA drug class comparison methodology`
5. `"Stacking the Risks" anabolic steroid misuse FAERS fatal outcomes stacking substance use`
6. `ChEMBL androgen receptor binding affinity dataset steroids bioactivity database pharmacology`

Terms from the brief's suggested list not yet separately searched (tracked in TODO.md for the formal pass):
`anabolic steroid adverse event reporting` (covered incidentally by #1/#5), `anabolic steroid structure activity
relationship` (covered by #2), `anabolic steroid QSAR` (covered by #2), `molecular pharmacology
pharmacovigilance` (covered by #3), `chemical structure adverse event similarity` (covered by #3).

---

## Findings table

| Paper | Year | Data | Method | Compounds | Research question | Overlap with this project | What this project adds |
|---|---|---|---|---|---|---|---|
| Heo, Yang, Yum, Joo, Yum. "Stacking the Risks: Fatal Consequences of Anabolic Steroid Misuse and Stacked Substance Use in FAERS Data." *Substance Use & Addiction Journal* (SAGE), 2026. [PubMed](https://pubmed.ncbi.nlm.nih.gov/40910553/) / [journal](https://journals.sagepub.com/doi/10.1177/29767342251360872) | 2026 | FAERS, 286 reports of intentional AAS misuse (218 usable after dedup) | Descriptive + logistic regression on serious/fatal outcome predictors (age, drug count, stacking, report year) | Multiple AAS, general "anabolic steroid" class | Directly overlaps with Aim 4 / H3 (therapeutic vs. misuse, stacking) and with FAERS-based AAS pharmacovigilance generally | This project (a) links reporting phenotype to **molecular/receptor pharmacology similarity**, which this paper does not attempt; (b) treats misuse classification as a documented, evidence-and-confidence-logged variable rather than an intentional-misuse-only cohort; (c) analyzes the full research-defined AE category taxonomy rather than a fatal/serious-outcome-focused endpoint |
| (Unspecified authors, PMC). "Major adverse cardiovascular events associated with testosterone treatment: a pharmacovigilance study of the FAERS database." [PMC10370495](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10370495/) | ~2023 | FAERS, testosterone-labeled products | Disproportionality analysis (single compound, single AE domain) | Testosterone only | Cardiovascular signal detection for one AAS | Single-compound, single-domain design; this project is comparative **across** the AAS class and multimodal (adds structure/receptor layer) | Cross-compound comparative design; explicit multimodal structure-to-safety linkage |
| Multiple disproportionality-analysis methods papers (e.g., ScienceDirect "Statistical and graphical approaches for disproportionality analysis..."; various FAERS single-drug studies, e.g., denosumab, propranolol, doxorubicin) | Various, 2013–2025 | FAERS | ROR/PRR/BCPNN/MGPS methodology and applications | Non-AAS drugs, methodology-focused | Establishes ROR/logROR/CI formulas and continuity-correction conventions used in this project (Sec. 11) | Methodological baseline, not AAS-specific | This project applies the same established disproportionality machinery specifically to a within-class AAS comparator design (cohort-relative background) rather than a single-drug-vs-all-FAERS design |
| Multiple QSAR papers on anabolic/androgenic steroid activity: e.g., "Anabolic and androgenic activities of 19-nor-testosterone steroids: QSAR study using quantum and physicochemical molecular descriptors" ([PubMed 21514384](https://pubmed.ncbi.nlm.nih.gov/21514384/)); "Chemometric and chemoinformatic analyses of anabolic and androgenic activities of testosterone and dihydrotestosterone analogues" ([PubMed 18514531](https://pubmed.ncbi.nlm.nih.gov/18514531/)); "A Quantitative Structure–Activity Relationship Study of the Anabolic Activity of Ecdysteroids" (2026, [doi](https://doi.org/10.3390/computation13080195)) | 2008–2026 | Curated steroid series with measured anabolic/androgenic activity (not FAERS) | QSAR: quantum/physicochemical descriptors + multilinear regression / pattern recognition, R²≈0.84, q²≈0.80 | Structurally diverse steroid series (not identical to this project's cohort) | Establishes that steroid structural descriptors correlate with *receptor-level* anabolic/androgenic activity | These papers connect structure → receptor activity. **None connect structure or receptor activity → real-world adverse-event reporting.** This project's Aim 3 (structure/pharmacology → FAERS safety phenotype) is the gap these papers do not address. |
| Vilar, Uriarte, Santana, Tatonetti, Friedman (and related). "The role of drug profiles as similarity metrics: applications to repurposing, adverse effects detection and drug–drug interactions." *Briefings in Bioinformatics*, 2017. [link](https://academic.oup.com/bib/article/18/4/670/2562764) | 2017 | Mixed (chemical structure, target, ADE profiles) | Similarity-based modeling across multiple drug-profile types for ADE/DDI prediction | General drug set, not AAS-specific | Directly overlaps with this project's core methodological premise: does profile similarity (structural/target) associate with adverse-event profile similarity? | Establishes precedent that structure/target similarity has been linked to ADE similarity **in general pharmacology**, supporting H1's plausibility | This project is the first (per this search) to apply this similarity-linkage framework specifically **within the AAS class**, using a rigorously normalized FAERS phenotype and an explicit permutation-based (Mantel-style) matrix-association test rather than a general repurposing/DDI prediction framing |
| "Facilitating adverse drug event detection in pharmacovigilance databases using molecular structure similarity: application to rhabdomyolysis." [PMC3241177](https://pmc.ncbi.nlm.nih.gov/articles/PMC3241177/) | ~2011 | FAERS + molecular structure | Structure-similarity-guided signal detection for one specific AE (rhabdomyolysis) across many drug classes | Cross-class, one AE | Methodologically close precedent: molecular structure similarity used alongside FAERS signal detection | Single-AE, cross-class design (not AAS-specific, not multi-domain safety phenotype) | This project generalizes the idea to a full multi-domain safety phenotype vector within one pharmacological class, plus adds receptor pharmacology as a second similarity layer |
| "3D Pharmacophoric Similarity improves Multi Adverse Drug Event Identification in Pharmacovigilance." *Scientific Reports*, 2015. [link](https://www.nature.com/articles/srep08809) | 2015 | FAERS/ADE + 3D pharmacophore similarity | Similarity-based multi-ADE signal detection | General drug set | Related precedent for structure-similarity-informed pharmacovigilance signal detection | Uses 3D pharmacophore similarity (not attempted in this project's initial scope, which uses 2D fingerprints/descriptors + receptor activity) | Notes 3D pharmacophore modeling as a plausible future extension of this project (see Limitations) |

## Synthesis

Two literature clusters are directly relevant and do **not overlap with each other**:

1. **AAS + FAERS pharmacovigilance** (e.g., Heo et al. 2026 "Stacking the Risks"; testosterone MACE study):
   these establish that FAERS-based AAS safety signal analysis is an active, current area (2023–2026), and that
   misuse/stacking classification from FAERS coded terms is methodologically precedented. None of the located
   papers incorporate molecular structure or receptor-binding data.
2. **AAS structure/receptor QSAR** (multiple 2008–2026 papers): these establish that steroid structural features
   are predictive of *in vitro* anabolic/androgenic receptor activity. None of the located papers connect this
   structural/receptor phenotype to real-world adverse-event reporting data.

A third, general-pharmacology cluster (Vilar et al. 2017; rhabdomyolysis structure-similarity paper; 3D
pharmacophore ADE paper) establishes that linking chemical/target similarity to adverse-event-profile similarity
is a validated general strategy in pharmacovigilance informatics, but applied across broad, heterogeneous drug
sets rather than within one structurally/pharmacologically coherent class.

**Conclusion for novelty framing:** Based on this first-pass structured search, no located study integrates (a)
receptor pharmacology and structural similarity of anabolic-androgenic steroids with (b) a normalized,
class-internal FAERS adverse-event reporting phenotype, using (c) a formal matrix-association permutation test.
Per the brief's instruction (Sec. 38), the appropriate claim is:

> "To our knowledge, following a structured (though not yet exhaustive, systematic-review-grade) literature
> search, this project investigates a relatively underexplored integration of anabolic-androgenic steroid
> receptor pharmacology and structural similarity with real-world FAERS adverse-event reporting phenotypes."

This is **not** "this has never been done," and must be revisited once the formal PubMed pass (TODO.md) is
complete — it is possible a directly overlapping paper exists that this first-pass web search did not surface.

## Outstanding work before this document can support a manuscript-facing novelty claim

- [ ] Formal PubMed/E-utilities search using the exact term list in Sec. 38 of the project brief, with recorded
      hit counts per term.
- [ ] Backward/forward citation search on Heo et al. 2026 and Vilar et al. 2017 (the two closest papers).
- [ ] Search ChEMBL/BindingDB documentation and any published steroid-focused bioactivity curation papers for
      prior AR/PR/GR/MR/ER steroid datasets that could be reused/cross-validated against.
- [ ] Re-run this review after the primary analysis is complete, in case results surface additional relevant
      comparator literature not found in a pre-analysis search.
