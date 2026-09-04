# Literature Review

**Status:** Two-pass search. Pass 1 (2026-08-27) was a non-exhaustive general web search, sufficient to avoid an
unsupported novelty claim but explicitly flagged as needing a formal-database follow-up. **Pass 2 (2026-09-04)**
completed that follow-up: a formal PubMed search via NCBI E-utilities (`esearch`/`esummary`/`efetch`, live HTTP
calls, not assumed) using the full required term list with exact recorded hit counts per term, plus a
backward/forward citation search on the two closest papers (via OpenAlex and Semantic Scholar's citation graph
APIs) and a targeted search for AAS-specific ChEMBL/BindingDB curation literature. This is still not a
PRISMA-grade systematic review (no dual independent screening, no pre-registered protocol, single-database
citation-graph tools rather than Scopus/Web of Science) — that caveat is carried into the novelty-claim wording
below — but every item in Pass 1's "Outstanding work" checklist is now addressed with real, recorded results
rather than left open.

**Databases/tools searched:**
- Pass 1: general web search (aggregating PubMed, PMC, journal publisher sites, preprint servers).
- Pass 2: NCBI E-utilities (`eutils.ncbi.nlm.nih.gov`, PubMed/MEDLINE), OpenAlex API (`api.openalex.org`,
  reference-list/backward-citation lookup), Semantic Scholar Graph API (`api.semanticscholar.org`,
  forward-citation/citing-paper lookup).

**Dates searched:** 2026-08-27 (Pass 1), 2026-09-04 (Pass 2)

**Search terms used (from the required topic list):**
1. `anabolic androgenic steroid FAERS pharmacovigilance adverse event reporting`
2. `anabolic steroid receptor selectivity computational structure activity relationship QSAR`
3. `molecular similarity chemical structure adverse event profile prediction drug target`
4. `disproportionality analysis reporting odds ratio FAERS openFDA drug class comparison methodology`
5. `"Stacking the Risks" anabolic steroid misuse FAERS fatal outcomes stacking substance use`
6. `ChEMBL androgen receptor binding affinity dataset steroids bioactivity database pharmacology`

Terms from the brief's suggested list that Pass 1 covered only incidentally (via #1/#2/#3 above) rather than as
their own separate query -- now searched individually in Pass 2, below: `anabolic steroid adverse event
reporting`, `anabolic steroid structure activity relationship`, `anabolic steroid QSAR`, `molecular pharmacology
pharmacovigilance`, `chemical structure adverse event similarity`.

---

## Pass 2: formal PubMed search (NCBI E-utilities, 2026-09-04)

Every term below (the original 6, plus the 5 "not yet separately searched" broader terms) was run against
`esearch.fcgi?db=pubmed`, letting PubMed's own automatic term-mapping expand each phrase (the same mapping a
manual PubMed UI search would apply — not manually simplified). `count` is PubMed's exact `esearchresult.count`;
this is a live, reproducible number, not an estimate.

| # | Term (as searched) | Hits | Notes |
|---|---|---|---|
| 1 | `anabolic androgenic steroid FAERS pharmacovigilance adverse event reporting` | **0** | The literal 5-concept AND combination matches nothing indexed. |
| 2 | `anabolic steroid receptor selectivity computational structure activity relationship QSAR` | **1** | PMID [23872659](https://pubmed.ncbi.nlm.nih.gov/23872659/) — virtual-screening study to *identify new* anabolic steroid candidates (drug discovery), not a safety-reporting linkage; also exactly the kind of novel-compound-design work Sec. 36 of the project brief excludes this project from doing. |
| 3 | `molecular similarity chemical structure adverse event profile prediction drug target` | **1** | PMID [41187567](https://pubmed.ncbi.nlm.nih.gov/41187567/), 2026 — "Trialblazer," a general chemistry-based toxicity-risk predictor for late-stage drug development. Not AAS-specific, not FAERS-based, no receptor-similarity comparator matrix — belongs in the general-pharmacology cluster (Synthesis, below), not a direct overlap. |
| 4 | `disproportionality analysis reporting odds ratio FAERS openFDA drug class comparison methodology` | **0** | No indexed paper combines all of these concepts in one record. |
| 5 | `anabolic steroid misuse FAERS fatal outcomes stacking substance use` | **1** | PMID [40910553](https://pubmed.ncbi.nlm.nih.gov/40910553/) — Heo et al., already in the findings table below. Confirms Pass 1's web search surfaced the same paper a formal PubMed search does. |
| 6 | `ChEMBL androgen receptor binding affinity dataset steroids bioactivity database pharmacology` | **0** | No indexed paper combines ChEMBL curation methodology with AAS/androgen-receptor-specific bioactivity in one record — see the dedicated ChEMBL/BindingDB search below for a broader attempt at this question. |
| 7 | `anabolic steroid adverse event reporting` | **56** | All 56 titles scanned (not just the top 5). All either clinical case reports/series, narrative reviews of AAS health effects, or single-compound/single-domain pharmacovigilance studies (e.g. PMID [41503895](https://pubmed.ncbi.nlm.nih.gov/41503895/), 2026, a testosterone-cypionate cardiovascular/thrombotic FAERS study — a second example of the single-compound design pattern already in the findings table). None combine structure/receptor similarity with a FAERS phenotype. |
| 8 | `anabolic steroid structure activity relationship` | **38** | All 38 titles scanned. Confirms the existing QSAR-literature cluster (structure -> *in vitro* receptor activity, not -> real-world reporting) and surfaces two new, closely-related **narrative reviews** added to the findings table below (PMID [41898445](https://pubmed.ncbi.nlm.nih.gov/41898445/), 2026; PMID [39322097](https://pubmed.ncbi.nlm.nih.gov/39322097/), 2024) — see Synthesis for why neither overlaps this project's quantitative design despite conceptual closeness. |
| 9 | `anabolic steroid QSAR` | **6** | Matches the QSAR papers already identified in Pass 1 (PMIDs 23872659, 21514384, 19836752, 19523507, 18514531, plus one more) — no new papers. |
| 10 | `molecular pharmacology pharmacovigilance` | **457** | Too broad to hand-screen exhaustively (both terms are common, and PubMed's automatic mapping expanded "molecular pharmacology" to include the journal *Molecular Pharmacology* generally) — recorded as a broad co-occurrence baseline, not screened paper-by-paper. The top 5 by relevance were general pharmacovigilance-methodology papers unrelated to AAS. |
| 11 | `chemical structure adverse event similarity` | **1,694** | Similarly too broad to hand-screen exhaustively; recorded as a baseline. The top 5 by relevance were general cheminformatics/pharmacovigilance-methodology papers unrelated to AAS. |

**New findings surfaced by Pass 2**, added to the table below: PMID 41898445, PMID 39322097, PMID 41503895, PMID
41187567 (all assessed in Synthesis).

## Backward/forward citation search (2026-09-04)

Per Pass 1's outstanding-work item, both closest papers were checked for who they cite and who cites them.

**Heo et al. 2026 ("Stacking the Risks")** — DOI `10.1177/29767342251360872`, PMID 40910553.
- *Backward* (references, via OpenAlex, 12 total, all titles checked): exclusively clinical case
  reports/series and AAS cardiometabolic/reproductive-effects/stigma literature (e.g. "Cardiac and Metabolic
  Effects of Anabolic-Androgenic Steroid Abuse on Lipids, Blood Pressure...", "Long-Term Anabolic-Androgenic
  Steroid Use Is Associated With Left Ventricular Dysfunction"). None involve molecular structure, receptor
  bioactivity data, or a similarity/distance-matrix framework.
- *Forward* (citing papers, via Semantic Scholar, 1 total as of this search — expected for a paper this recent):
  PMID [41869035](https://pubmed.ncbi.nlm.nih.gov/41869035/) (2026), a narrative review on non-medical
  testosterone/AAS use citing Heo et al. as one supporting reference for the "growing public-health concern"
  framing. Not FAERS-based, not structure/receptor-comparative. No overlap.

**Vilar et al. 2016/2017 ("The role of drug profiles as similarity metrics")** — DOI `10.1093/bib/bbw048`,
PMID 27273288.
- *Forward* (citing papers, via Semantic Scholar, 40 total, all titles checked): drug-repurposing,
  drug-drug-interaction-prediction, and adverse-effect-prediction methodology papers (2017-2024) applied to
  general/heterogeneous drug sets (cancer, lupus, diabetes, ischemic stroke, etc.). **None are AAS- or
  steroid-specific.** No paper in this citation lineage has applied the general
  structure/target-similarity-to-ADE-similarity framework specifically within the AAS class — the gap this
  project addresses remains open in this citation lineage through 2024 (most recent citing papers found).
- *Backward*: not pulled (133 references on a broad methodological review paper; the forward-citation check is
  the more informative direction for a novelty claim, since it asks "has anyone since built on this idea for
  AAS," not "what pharmacology/similarity-metrics literature predates it").

## ChEMBL/BindingDB steroid-curation literature search (2026-09-04)

Per Pass 1's outstanding-work item: searched for any published paper documenting AAS-specific curation of
ChEMBL/BindingDB receptor bioactivity data (`ChEMBL curation steroid bioactivity dataset`: 0 hits;
`BindingDB androgen receptor steroid dataset curation`: 0 hits; `steroid receptor binding affinity database
curated`: 2 hits, both unrelated — a deep-learning docking-surrogate tool and an atrazine endocrine-disruption
study, neither AAS-specific). **No published paper was found describing or quantifying AAS-specific
receptor-bioactivity coverage gaps in ChEMBL/BindingDB.** This means this project's own empirical finding
(7/10 cohort compounds have zero receptor measurements in these databases, `reports/data_quality.md`) appears
to be a first-hand observation, not independently corroborated or contradicted by existing literature — worth
stating plainly rather than implying it is a known, published fact.

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
| Wiacek, Zubrzycki. "Anabolic-Androgenic Steroids Revisited: Structural Biology, Receptor Signaling, and Mechanisms of Anabolic-Androgenic Dissociation." *Int J Mol Sci*, 2026. [PubMed](https://pubmed.ncbi.nlm.nih.gov/41898445/) | 2026 | Narrative synthesis of preclinical/mechanistic literature (no new data) | Qualitative review: structural chemistry + AR ligand-binding-domain biology + signaling, explaining why structurally-related AAS diverge in effect | General AAS class, mechanistic/preclinical focus | **Conceptually the closest paper found**: explicitly links AAS molecular structure (C17-substitution chemistry) to receptor-level mechanism to divergent physiological/cardiovascular outcomes -- the same structure-to-outcome chain this project tests quantitatively | Confirms the field recognizes this structure-to-outcome link as a live, current (2026) question worth reviewing, supporting H1/H2a's plausibility -- but this is a **qualitative mechanistic synthesis of preclinical evidence**, not a quantitative model, uses no FAERS or other real-world reporting data, and computes no similarity metric or statistical test | This project operationalizes the same conceptual link (structure/receptor -> outcome) **quantitatively**: real ChEMBL/BindingDB receptor data, real FAERS reporting data, a formal distance-matrix similarity metric, and a pre-registered permutation test -- turning this review's qualitative narrative into a falsifiable, numeric hypothesis test |
| Sinha, Deb, Datta, Yadav, Phulkar, Adhikari. "Evaluation of structural features of anabolic-androgenic steroids: entanglement for organ-specific toxicity." *Steroids*, 2024. [PubMed](https://pubmed.ncbi.nlm.nih.gov/39322097/) | 2024 | Narrative synthesis of clinical/preclinical literature (no new data) | Qualitative review of AAS structural features and organ-specific toxicity mechanisms (hepatic, cardiovascular, reproductive, psychiatric) | General AAS class | Title suggests a direct structure-to-toxicity linkage; in substance, a narrative summary of known per-organ AAS harms without a quantitative structure-similarity or receptor-similarity metric | Same gap as above: qualitative, not quantitative; no FAERS data; no formal statistical test linking structural distance to an adverse-event-category distance | Reinforces that the specific quantitative gap this project fills (structure/receptor similarity <-> FAERS safety-phenotype similarity, tested via permutation) has not been closed even by papers whose titles suggest exactly that link |
| "Myocardial Infarction, Pulmonary Embolism, and Deep Vein Thrombosis Following Testosterone Cypionate Use: A Pharmacovigilance Study." 2026. [PubMed](https://pubmed.ncbi.nlm.nih.gov/41503895/) | 2026 | FAERS, testosterone cypionate | Disproportionality analysis, cardiovascular/thrombotic domain only | Testosterone (one ester) only | A second example (alongside the PMC10370495 testosterone-MACE study already above) of the recurring single-compound, single-AE-domain FAERS study design for this class | Same limitation as the other single-compound study: no cross-compound comparison, no structural/receptor layer | Reinforces the pattern this project's Aim 3 addresses: single-compound FAERS pharmacovigilance for AAS is a well-established, current (2026) design, but never extended to a within-class comparative, structure-linked framework |
| Zhang, Welsch, Schueller, Kirchmair. "Trialblazer: A chemistry-focused predictor of toxicity risks in late-stage drug development." *Eur J Med Chem*, 2026. [PubMed](https://pubmed.ncbi.nlm.nih.gov/41187567/) | 2026 | Chemistry + late-stage clinical-trial toxicity outcomes, general drug set | ML model predicting toxicity risk from chemical structure | General drug candidates, not AAS-specific | General-pharmacology precedent for structure -> real-world (trial-stage) toxicity-outcome prediction, methodologically adjacent to this project's structure -> FAERS-outcome premise | Predicts aggregate trial-stage toxicity risk from structure alone (no receptor layer, no within-class comparator, no AAS focus, not FAERS-based) | Same general-pharmacology-cluster relationship as Vilar et al. 2017: establishes structure -> adverse-outcome prediction as an active 2026 research area broadly, not within the AAS class specifically |

## Synthesis

Three literature clusters are directly relevant and do **not overlap with each other**:

1. **AAS + FAERS pharmacovigilance** (Heo et al. 2026 "Stacking the Risks"; two single-compound testosterone
   studies, PMC10370495 and PMID 41503895): these establish that FAERS-based AAS safety signal analysis is an
   active, current area (2023-2026), and that misuse/stacking classification from FAERS coded terms is
   methodologically precedented. None of the located papers incorporate molecular structure or receptor-binding
   data.
2. **AAS structure/receptor QSAR and mechanistic review** (multiple 2008-2026 QSAR papers, plus two 2024/2026
   narrative reviews explicitly framed around structure-to-outcome linkage, Wiacek & Zubrzycki 2026 and Sinha et
   al. 2024): these establish that steroid structural features are predictive of *in vitro* receptor activity,
   and that the field recognizes structure->receptor->outcome as a live conceptual question worth reviewing as
   recently as 2026. **None of the located papers, including the two narrative reviews whose titles most closely
   resemble this project's premise, connect this structural/receptor phenotype to real-world adverse-event
   *reporting* data, or compute any quantitative similarity/distance metric.** They synthesize known mechanisms
   in prose; this project tests a specific, falsifiable, numeric hypothesis against real FAERS data.
3. **General-pharmacology structure-to-ADE similarity** (Vilar et al. 2016; rhabdomyolysis structure-similarity
   paper; 3D pharmacophore ADE paper; Trialblazer 2026): establishes that linking chemical/target similarity to
   adverse-event-profile similarity is a validated, actively-developed general strategy in pharmacovigilance
   informatics (as recently as 2026), but applied across broad, heterogeneous drug sets rather than within one
   structurally/pharmacologically coherent class. The forward-citation search on Vilar et al. (40 citing papers,
   2017-2024, all titles checked) found no AAS- or steroid-specific application of this framework in its
   citation lineage.

**Conclusion for novelty framing:** Following a formal PubMed E-utilities search (11 required terms, exact hit
counts recorded above; every one of the 103 hits across the 9 narrower terms individually screened by title,
plus the top 5 by relevance from each of the two broadest terms, 457 and 1,694 hits respectively) plus a
backward/forward citation search on the two closest papers and a targeted ChEMBL/BindingDB curation-literature
search, no located study integrates (a)
receptor pharmacology and structural similarity of anabolic-androgenic steroids with (b) a normalized,
class-internal FAERS adverse-event reporting phenotype, using (c) a formal matrix-association permutation test.
The closest conceptual precedents (Wiacek & Zubrzycki 2026; Sinha et al. 2024) confirm the question is
recognized as live and current, but address it qualitatively, not quantitatively. Per the brief's instruction
(Sec. 38), the appropriate claim is:

> "To our knowledge, following a structured literature search (general web search plus a formal PubMed
> E-utilities search across the required term list, with a citation-graph check on the two closest papers --
> not a PRISMA-grade systematic review with dual independent screening), this project investigates a relatively
> underexplored integration of anabolic-androgenic steroid receptor pharmacology and structural similarity with
> real-world FAERS adverse-event reporting phenotypes. The closest conceptual precedents are two 2024/2026
> narrative reviews explicitly framed around linking AAS structure to outcomes, neither of which uses FAERS
> data or a quantitative similarity metric."

This is **not** "this has never been done" — it is a specific, evidenced claim about what was and wasn't found,
scoped to the search actually performed. A single-analyst PubMed/citation-graph search, however formal, is not
a substitute for a registered systematic review with independent dual screening across Embase/Scopus/Web of
Science; that remains a real limitation of this novelty claim, not a technicality (see Limitations, below).

## Limitations of this review

- **Single analyst, no dual screening.** All PubMed titles (56 + 38 + 40 forward-citation titles, plus every
  low-count term's results) were screened by one reader against one set of inclusion criteria; a second
  independent screener, standard for a real systematic review, was not used.
- **PubMed/MEDLINE only for the formal pass**, not Embase, Scopus, or Web of Science — a paper indexed only in
  one of those (common for pharmacology/toxicology and non-US journals) would be missed here.
- **Two broad terms (10, 11) were not exhaustively screened** (457 and 1,694 hits respectively) — only the top 5
  by PubMed relevance ranking were checked for each, so a relevant but low-relevance-ranked paper under those
  specific broad terms could have been missed. Every other term's full result set was screened.
- **Citation-graph coverage (OpenAlex, Semantic Scholar) is not complete or authoritative** — Heo et al.'s own
  reference list came through OpenAlex (Semantic Scholar's copy was elided by the publisher), and citation
  counts on both platforms can lag true citation counts, especially for very recent papers.

## Outstanding work before this document can support a manuscript-facing novelty claim

- [x] Formal PubMed/E-utilities search using the exact term list (both the originally-specified 6 terms and the
      5 broader terms), with recorded hit counts per term — see "Pass 2" above (2026-09-04).
- [x] Backward/forward citation search on Heo et al. 2026 and Vilar et al. 2017 (the two closest papers) — see
      "Backward/forward citation search" above (2026-09-04).
- [x] Search ChEMBL/BindingDB documentation and any published steroid-focused bioactivity curation papers for
      prior AR/PR/GR/MR/ER steroid datasets that could be reused/cross-validated against — see "ChEMBL/BindingDB
      steroid-curation literature search" above (2026-09-04); no such paper was found, so this project's own
      receptor-coverage-gap finding (`reports/data_quality.md`) appears to be a first-hand observation.
- [x] Re-run this review after the primary analysis is complete, in case results surface additional relevant
      comparator literature not found in a pre-analysis search — Pass 2 (2026-09-04) was conducted after Phases
      9-13's results (including the receptor-sparsity finding, the null H2a result, and the H3 misuse-vs-
      therapeutic result) were already known, and the search terms/scope above were reviewed against those
      results; no additional directly-overlapping paper was surfaced by knowing the results in advance.
- [ ] Before any manuscript submission (not required for this project's own reporting): a proper multi-database,
      dual-screened systematic search (PubMed + Embase + Scopus/Web of Science), ideally with a pre-registered
      protocol (e.g. PROSPERO), to support a stronger novelty claim than "following the search actually
      performed" — see Limitations, above, for exactly what this pass does not substitute for.
