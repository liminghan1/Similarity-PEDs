import { Card } from "@/components/Card";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getOverview } from "@/lib/api";

export default async function LimitationsPage() {
  const overview = await getOverview();

  return (
    <div className="space-y-6">
      <Card title="Limitations">
        <p className="text-sm text-slate-600">
          <ProvenanceBadge kind="INTERPRETATION" /> This page states plainly what this pipeline
          cannot show, alongside what it can. None of these are edge cases discovered after the
          fact -- most were anticipated in the pre-registered analysis plan; the FAERS
          cohort-relative background finding below was flagged during exploratory data inspection,
          before it could bias the primary hypothesis test.
        </p>
      </Card>

      <Card title="FAERS cannot establish incidence, prevalence, absolute risk, or causation">
        <p className="text-sm text-slate-700">
          Every statistic in this project is a <strong>reporting association</strong> or
          disproportionality signal, never incidence, prevalence, absolute risk, or a causal
          clinical effect. FAERS is a voluntary, spontaneous reporting system with no reliable
          exposure denominator, subject to stimulated/publicity reporting, reporter-type and
          country-of-origin variation, and substantial ascertainment bias -- this cohort&apos;s overall
          reported-serious proportion ranges 48-98% across compounds, far higher than plausible true
          clinical incidence, consistent with well-documented FAERS serious-outcome reporting bias.
        </p>
      </Card>

      <Card title="Small compound cohort limits statistical power">
        A 10-compound cohort (45 pairs) gives a Mantel-style permutation test limited resolving
        power for any matrix-association analysis. The exploratory Ridge-regression analysis (H4)
        is likely underpowered regardless of penalization, independent of whether a true effect
        exists.
      </Card>

      <Card title="Receptor bioactivity coverage is a first-order limitation, not a minor one">
        <p className="text-sm text-slate-700">
          7 of 10 cohort compounds have zero measurements against any of the six receptors queried
          (AR, PR, GR, MR, ER-alpha, ER-beta), which prevented the intended primary analysis (H1)
          from running at all. This reflects real, documented gaps in ChEMBL/BindingDB curation for
          classic (non-drug-candidate) AAS compounds, not a pipeline defect -- but it means this
          project currently cannot speak to the receptor-pharmacology-to-safety question.
        </p>
      </Card>

      <Card title="The cohort-relative safety-phenotype background is a methodological choice with real consequences">
        <p className="text-sm text-slate-700">
          Each compound&apos;s primary logROR is computed against the rest of the 10-compound
          cohort, not the full FAERS database. Testosterone contributes 75% of total cohort report
          volume (5,549 of 7,433 reports) and its cohort-relative safety profile is strongly
          anti-correlated with every other cohort compound (Pearson r as low as -0.96), while the
          other nine compounds are strongly positively correlated with each other. This is a real,
          now-confirmed effect of the cohort-relative background: an all-FAERS-background
          sensitivity variant (live openFDA aggregate count queries rather than a full
          re-ingestion -- see Methods) shows testosterone&apos;s correlation with the other nine
          compounds flip to mostly positive instead, and per-cell logROR agrees with the
          cohort-relative version only weakly (r=0.522, 57.3% sign agreement across 110 cells).
          Reassuringly, the H2a structural-similarity conclusion itself is unchanged under either
          background (both null, similar effect size) -- but this is a genuine methodological
          sensitivity in the underlying safety-phenotype numbers, not just a hypothetical concern.
        </p>
      </Card>

      <Card title="Confounding is not controlled for">
        Age, sex, underlying disease, polypharmacy, other performance-and-image-enhancing-drug
        exposure, route of administration, product adulteration/provenance (especially relevant for
        misuse-associated, non-pharmaceutical-grade products), country, reporter type, and reporting
        year are not adjusted for anywhere in this project. The therapeutic-vs-misuse comparison
        (H3) is particularly susceptible to confounding by indication and by population -- clinical
        TRT patients skew older and healthier-selected than recreational users -- so its odds ratios
        describe reporting-pattern differences between two report strata, not a controlled estimate
        of the causal effect of misuse itself.
      </Card>

      <Card title="The misuse classifier is a first-pass rule set, even after its two-tier redesign">
        <p className="text-sm text-slate-700">
          100 reports (18% of the earlier, less conservative classifier&apos;s MISUSE group) now fall
          into a separately-tracked AMBIGUOUS_EXPOSURE outcome and are excluded from the H3
          comparison entirely -- some are almost certainly genuine misuse under-counted by the
          stricter rule, and the true sensitivity/specificity trade-off cannot be resolved without
          manually-adjudicated ground truth, which this project does not have. Separately, the
          leakage-controlled sensitivity analysis (see Therapeutic vs. Misuse) only controls for
          exact reaction-term overlap between the classifier and the AE-category taxonomy (one
          term, &quot;substance abuse&quot;) -- it cannot detect or control for subtler correlations between
          what gets a report classified MISUSE and what gets it counted in a given AE category.
        </p>
      </Card>

      <Card title="Research-defined AE categories are not an official MedDRA hierarchy">
        The 11-category taxonomy used throughout this project is a curated, documented, but
        non-licensed grouping of reaction terms. Category-level findings should not be presented as
        standardized MedDRA System Organ Class results.
      </Card>

      <Card title="Cross-source duplicate reports and imperfect name normalization">
        <p className="text-sm text-slate-700">
          This project deduplicates report <em>versions</em> (the same case updated over time) but
          does not attempt to resolve independent reports of the same real-world event submitted by
          different sources (e.g. both a clinician and a manufacturer) -- a distinct, harder problem
          requiring narrative-text analysis beyond this project&apos;s scope. Separately, drug-name
          normalization -- while tested against real messy FAERS data and fixed twice during
          development after confirmed false positives -- still has 3 fuzzy-tier matches and 1
          ambiguous, manual-review-flagged match in the final dataset; some unmeasured residual
          misclassification of raw FAERS drug-name strings is possible.
        </p>
      </Card>

      {overview.major_limitations.length > 0 && (
        <Card title="Summary (as surfaced in the API overview)">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {overview.major_limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
