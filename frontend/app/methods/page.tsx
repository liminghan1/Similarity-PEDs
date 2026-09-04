import { Card } from "@/components/Card";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";

function Cite({ path }: { path: string }) {
  return <code className="rounded bg-slate-100 px-1 text-xs">{path}</code>;
}

export default function MethodsPage() {
  return (
    <div className="space-y-6">
      <Card title="Methods">
        <p className="text-sm text-slate-600">
          Full detail lives in the repository alongside the code that implements it -- this page
          summarizes each stage and cites the file that is the source of truth, per the project&apos;s
          reproducibility requirement that every number trace back to a script and a data source.
        </p>
      </Card>

      <Card title="Compound cohort">
        <p className="text-sm text-slate-700">
          10 canonical AAS parent compounds were selected a priori: testosterone, nandrolone,
          oxandrolone, stanozolol, oxymetholone, methandienone, drostanolone, methenolone,
          boldenone, and trenbolone. Ester/formulation variants (e.g. testosterone enanthate) are
          tracked as distinct entities in the database but rolled up to the parent compound for the
          primary analysis.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="research/exclusion_rules.md" /> (Sec. 1, cohort selection) ·{" "}
          <Cite path="docs/database_schema.md" /> (parent/ester rollup)
        </p>
      </Card>

      <Card title="Chemical data">
        <p className="text-sm text-slate-700">
          Canonical/isomeric SMILES, InChIKey, and molecular formula retrieved from PubChem PUG
          REST. RDKit computed descriptors (molecular weight, XLogP, TPSA, H-bond donor/acceptor
          count, ring counts, fraction Csp3 -- <code className="text-xs">rotatable_bonds</code>{" "}
          was excluded from similarity analyses as zero-variance across this cohort) and Morgan
          fingerprints (radius 2, 2048 bits). Every structure was validated via RDKit parse/sanitize
          plus a PubChem formula/molecular-weight cross-check before inclusion; 10/10 compounds
          passed.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="pipelines/pubchem/" /> · <Cite path="analysis/phenotype_matrix.py" />
        </p>
      </Card>

      <Card title="Receptor pharmacology">
        <p className="text-sm text-slate-700">
          ChEMBL and BindingDB were queried for Ki/IC50/EC50/Kd measurements against six human
          targets: androgen (AR), progesterone (PR), glucocorticoid (GR), mineralocorticoid (MR),
          and both estrogen receptors (ER-alpha, ER-beta). Measurement types were never pooled
          across each other. pActivity (9 - log10(value in nM)) was computed only for exact,
          non-censored measurements, and the primary receptor phenotype matrix was further
          restricted to ChEMBL assay confidence &ge;8.
        </p>
        <p className="mt-2 text-sm text-slate-700">
          Coverage proved far sparser than anticipated: only 3 of 10 cohort compounds have any
          qualifying measurement. See <ProvenanceBadge kind="INTERPRETATION" /> in the Limitations
          page for what this means for the primary hypothesis test.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="pipelines/chembl/" /> · <Cite path="pipelines/bindingdb/" /> ·{" "}
          <Cite path="research/exclusion_rules.md" /> (Sec. 3, assay confidence threshold)
        </p>
      </Card>

      <Card title="FAERS safety phenotype">
        <p className="text-sm text-slate-700">
          openFDA <code className="text-xs">/drug/event</code> reports matching any cohort
          compound&apos;s canonical name, curated alias, or formulation name were retrieved. Every drug
          entry in every fetched report was re-matched against the full cohort (not only the
          original query term) via a 5-tier normalization scheme: exact match, curated alias,
          normalized-string match, fuzzy match, and ambiguous (flagged for manual review). Reports
          were deduplicated to one row per case. Reactions were mapped to 11 research-defined
          adverse-event categories via case-insensitive exact match against a curated taxonomy --
          explicitly <strong>not</strong> an official MedDRA hierarchy.
        </p>
        <p className="mt-2 text-sm text-slate-700">
          For each compound &times; category pair, a log Reporting Odds Ratio (logROR) was computed
          against a <strong>cohort-relative background</strong> (the compound&apos;s reports vs. the rest
          of the 10-compound cohort&apos;s reports in the same extract), with Haldane-Anscombe continuity
          correction applied when any 2&times;2 cell was zero. Cells with fewer than 3 reports, and
          compounds with fewer than 20 total reports, were excluded from the primary safety
          phenotype matrix as statistically unreliable rather than shown as zero or imputed.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="pipelines/faers/normalization.py" /> (5-tier matching) ·{" "}
          <Cite path="docs/faers_deduplication.md" /> · <Cite path="research/ae_categories.csv" /> ·{" "}
          <Cite path="research/exclusion_rules.md" /> (Sec. 4, minimum-report thresholds)
        </p>
      </Card>

      <Card title="Similarity, distance, and the matrix-association test">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>
            <strong>Structural distance:</strong> mean of min-max-normalized Tanimoto distance
            (Morgan fingerprints) and Euclidean distance (z-scored descriptors).
          </li>
          <li>
            <strong>Receptor distance:</strong> 1 &minus; Pearson correlation on shared pActivity
            columns, requiring at least 3 shared columns (a 2-column correlation is mathematically
            deterministic and uninformative).
          </li>
          <li>
            <strong>Safety distance:</strong> 1 &minus; Pearson correlation on shared logROR
            categories, same 3-column minimum.
          </li>
          <li>
            <strong>Matrix-association test (H1, pre-specified primary):</strong> a Mantel-style
            permutation test -- Spearman rho on upper-triangle pairwise distances between the
            combined (structure+receptor) distance matrix and the safety distance matrix, N=9,999
            permutations, seed=42, one- and two-sided empirical p-values, and a 1,999-resample
            bootstrap confidence interval.
          </li>
        </ul>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="analysis/similarity_analysis.py" /> · <Cite path="analysis/matrix_association.py" /> ·{" "}
          <Cite path="research/analysis_plan.md" />
        </p>
      </Card>

      <Card title="Secondary and exploratory analyses">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>
            <strong>Clustering:</strong> independent hierarchical clustering (average linkage) of
            the structure and safety distance matrices, k chosen by maximum silhouette over k=2-5,
            compared via Adjusted Rand Index and Normalized Mutual Information. An exploratory
            PCA+k-means result is shown separately and was not used for any hypothesis test.
          </li>
          <li>
            <strong>Therapeutic vs. misuse (H3):</strong> a conservative rule-based classifier
            (v2) labeled each report THERAPEUTIC, MISUSE, MULTI_AAS_EXPOSURE, AMBIGUOUS_EXPOSURE,
            or UNKNOWN from reaction terms and indication text -- misuse was never inferred from
            multi-drug co-reporting alone, and misuse evidence is split into a high-confidence
            tier (sufficient alone) and an ambiguous tier (e.g. &quot;accidental overdose,&quot; &quot;product
            use in unapproved indication&quot; -- both have legitimate non-misuse explanations, so
            neither is sufficient alone; a report with only ambiguous evidence is classified
            AMBIGUOUS_EXPOSURE, not MISUSE). THERAPEUTIC-vs-MISUSE reports were compared on
            seriousness/hospitalization/death and on AE-category presence via Fisher&apos;s exact
            test (odds ratios with 95% CI), with Benjamini-Hochberg FDR correction (q&lt;0.05)
            applied across all AE-category tests and a leakage-controlled sensitivity variant
            (excluding every classifier-evidence reaction term from AE-category counting, since
            &quot;substance abuse&quot; is both misuse evidence and a category-taxonomy entry).
          </li>
          <li>
            <strong>Multivariate/H4 (exploratory):</strong> a penalized (Ridge) regression with
            leave-one-out cross-validation and permutation testing explored whether molecular
            descriptors predict each AE category&apos;s logROR (n=10 compounds).
          </li>
          <li>
            <strong>Sensitivity analyses:</strong> all 8 pre-specified variants (report-count
            thresholds, parent-vs-ester scope, mapping confidence, term vs. category granularity,
            alternate similarity metrics, alternate phenotype background) were run against the one
            fully computable primary result (H2); 9/10 variants were computable with current data.
            The all-FAERS-background variant (compound vs. the entire FAERS database rather than
            only the other 9 cohort compounds) was initially infeasible without a full database
            re-ingestion, but is now computed via ~132 live, count-only openFDA aggregate queries
            (<Cite path="analysis/full_faers_background.py" />) instead -- see Limitations for
            what this changed and what it didn&apos;t.
          </li>
        </ul>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="analysis/clustering.py" /> · <Cite path="pipelines/faers/classification.py" /> ·{" "}
          <Cite path="analysis/misuse_analysis.py" /> · <Cite path="analysis/multivariate_association.py" /> ·{" "}
          <Cite path="research/analysis_plan.md" /> (Sec. 7, sensitivity plan)
        </p>
      </Card>

      <Card title="Software and reproducibility">
        <p className="text-sm text-slate-700">
          Python 3.13; RDKit, pandas, numpy, scipy, scikit-learn, SQLAlchemy/PostgreSQL, all pinned
          via <code className="text-xs">uv.lock</code>. All random seeds are fixed (default 42).
          Every derived artifact carries a provenance manifest recording the git commit and
          generation timestamp it was produced from.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Cite path="artifacts/matrices/dataset_manifest.json" /> · <Cite path="reports/research_report.md" />{" "}
          (full report, regenerated by <code className="text-xs">make report</code>)
        </p>
      </Card>
    </div>
  );
}
