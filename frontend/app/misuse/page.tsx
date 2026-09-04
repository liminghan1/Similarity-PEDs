import { Card, Stat } from "@/components/Card";
import { ChartExplainer } from "@/components/ChartExplainer";
import { ForestPlot } from "@/components/charts/ForestPlot";
import { AnalysisLabelBadge, ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getMisuseAnalysis } from "@/lib/api";

export default async function MisusePage() {
  const misuse = await getMisuseAnalysis();

  const seriousnessRows = misuse.seriousness_outcomes.map((o) => ({
    label: o.outcome,
    oddsRatio: o.odds_ratio,
    ciLow: o.ci_low,
    ciHigh: o.ci_high,
    pValue: o.fisher_p_value,
  }));

  const categoryRows = misuse.ae_category_comparison.map((c) => ({
    label: c.category,
    oddsRatio: c.odds_ratio,
    ciLow: c.ci_low,
    ciHigh: c.ci_high,
    pValue: c.fisher_p_value,
    qValue: c.fdr_q_value,
    significant: c.significant_fdr_05,
  }));

  const nFdrSignificant = misuse.ae_category_comparison.filter((c) => c.significant_fdr_05).length;

  const leakageByCategory = new Map(
    misuse.ae_category_comparison_leakage_controlled.map((c) => [c.category, c]),
  );
  const leakageComparisonRows = misuse.ae_category_comparison
    .map((primary) => {
      const controlled = leakageByCategory.get(primary.category);
      if (!controlled) return null;
      return {
        category: primary.category,
        primaryP: primary.fisher_p_value,
        primaryQ: primary.fdr_q_value,
        primarySig: primary.significant_fdr_05,
        controlledP: controlled.fisher_p_value,
        controlledQ: controlled.fdr_q_value,
        controlledSig: controlled.significant_fdr_05,
        changed: primary.significant_fdr_05 !== controlled.significant_fdr_05,
      };
    })
    .filter((row): row is NonNullable<typeof row> => row !== null)
    .sort((a, b) => (a.changed === b.changed ? a.primaryP - b.primaryP : a.changed ? -1 : 1));

  const fullDist = misuse.full_classification_distribution;
  const sexTable = misuse.demographics.sex.table;
  const sexes = Object.keys(sexTable);

  return (
    <div className="space-y-6">
      <Card title="Therapeutic vs. Misuse">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <AnalysisLabelBadge label="SECONDARY" />
          <ProvenanceBadge kind="DERIVED" />
          <span className="text-sm text-slate-600">
            H3: reports coded (classifier {misuse.classifier_version}; by indication/route/
            reporter-narrative signals, see Methods) as misuse/non-medical-use vs.
            therapeutic/medical use, compared on outcome severity and adverse-event category. Odds
            ratios via Fisher&apos;s exact test.
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Stat label="Misuse-coded reports" value={misuse.group_sizes.misuse.toLocaleString()} />
          <Stat label="Therapeutic-coded reports" value={misuse.group_sizes.therapeutic.toLocaleString()} />
          <Stat
            label="Both strata >= 20 reports"
            value={misuse.strata_meet_minimum_20_reports ? "Yes" : "No"}
          />
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Full classification distribution across all{" "}
          {Object.values(fullDist).reduce((a, b) => a + b, 0).toLocaleString()} deduplicated
          reports:{" "}
          {Object.entries(fullDist)
            .sort((a, b) => b[1] - a[1])
            .map(([k, v]) => `${v.toLocaleString()} ${k}`)
            .join(", ")}
          . Only misuse and therapeutic are compared below; ambiguous_exposure is a separately-
          tracked outcome (real, but not confident-enough evidence to call misuse -- see Methods)
          and is excluded from this comparison, same as multi_aas_exposure and unknown.
        </p>
      </Card>

      <Card title="Outcome severity: misuse vs. therapeutic (odds ratio)">
        <ChartExplainer>
          Each dot is one outcome. The dashed vertical line at 1 means &quot;no difference between the
          two groups.&quot; A dot to the <strong>right</strong> of the line means that outcome was
          reported proportionally more often among misuse-coded reports than therapeutic-coded
          ones; a dot to the <strong>left</strong> means less often. The horizontal line through
          each dot is the 95% confidence interval -- the range of plausible odds ratios given the
          sample size; if that line crosses the dashed line at 1, the difference is not
          statistically distinguishable from chance. <strong>Red dots</strong> reached the
          conventional p&lt;0.05 significance threshold; gray dots did not.
        </ChartExplainer>
        <ForestPlot rows={seriousnessRows} height={260} />
        <p className="mt-2 text-xs text-slate-500">
          OR &gt; 1 means the outcome is reported proportionally more often in the misuse-coded
          group. Red = p &lt; 0.05 (uncorrected -- only 3 outcomes are tested here, so no
          multiple-comparison correction is applied; compare the AE-category chart below, where
          11 simultaneous tests make correction necessary). Death shows no significant difference;
          serious and hospitalization outcomes are reported significantly more often in the misuse
          group.
        </p>
      </Card>

      <Card title="Adverse-event category: misuse vs. therapeutic (odds ratio)">
        <ChartExplainer>
          Same reading as the chart above, now broken out by adverse-event category instead of by
          outcome severity: a category to the right of the dashed line at OR=1 is reported
          proportionally more often among misuse-coded reports; to the left, more often among
          therapeutic-coded reports. The x-axis is log-scaled (equal visual distance = equal
          multiplicative difference) since these odds ratios range from about 0.4x to nearly 9x.
          <strong> Red dots</strong> here mean significant after Benjamini-Hochberg FDR correction
          across all {categoryRows.length} categories (q&lt;0.05) -- not the raw, uncorrected
          p-value used in the chart above. Testing 11 categories simultaneously makes some raw
          p&lt;0.05 results expected by chance alone; FDR correction is what research/hypotheses.md
          requires before treating a category as supporting H3.
        </ChartExplainer>
        <ForestPlot rows={categoryRows} height={420} />
        <p className="mt-2 text-xs text-slate-500">
          {nFdrSignificant}/{categoryRows.length} categories remain significant after FDR
          correction (q&lt;0.05). See the leakage-controlled sensitivity check below before treating
          any single category as a confirmed finding.
        </p>
      </Card>

      <Card title="Sensitivity check: classifier-outcome leakage control">
        <ChartExplainer>
          One misuse-classification term, &quot;substance abuse,&quot; is <em>also</em> a
          &quot;psychiatric&quot; entry in the AE-category taxonomy -- so a report could count
          toward the psychiatric outcome for no reason other than the same term that got it
          labeled misuse in the first place. This check re-runs the AE-category comparison with
          every classifier-evidence reaction term excluded from category counting, and shows
          whether each category&apos;s FDR significance survives. A category whose significance
          flips is not reported as a finding.
        </ChartExplainer>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-1.5 pr-4">Category</th>
                <th className="py-1.5 pr-4">Primary q</th>
                <th className="py-1.5 pr-4">Leakage-controlled q</th>
                <th className="py-1.5 pr-4">Significance changed?</th>
              </tr>
            </thead>
            <tbody>
              {leakageComparisonRows.map((row) => (
                <tr
                  key={row.category}
                  className={`border-b border-slate-100 ${row.changed ? "bg-amber-50" : ""}`}
                >
                  <td className="py-1.5 pr-4 capitalize">{row.category}</td>
                  <td className="py-1.5 pr-4">
                    {row.primaryQ.toFixed(4)} {row.primarySig ? "(significant)" : ""}
                  </td>
                  <td className="py-1.5 pr-4">
                    {row.controlledQ.toFixed(4)} {row.controlledSig ? "(significant)" : ""}
                  </td>
                  <td className="py-1.5 pr-4 font-medium">
                    {row.changed ? "Yes -- not reported as a finding" : "No"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {misuse.ae_category_comparison_leakage_controlled_note}
        </p>
      </Card>

      <Card title="Demographics">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Age</h3>
            <div className="grid grid-cols-2 gap-3">
              <Stat
                label="Misuse median age"
                value={misuse.demographics.age.misuse_median_age?.toFixed(0) ?? "N/A"}
                sub={`n=${misuse.demographics.age.misuse_n_with_age}`}
              />
              <Stat
                label="Therapeutic median age"
                value={misuse.demographics.age.therapeutic_median_age?.toFixed(0) ?? "N/A"}
                sub={`n=${misuse.demographics.age.therapeutic_n_with_age}`}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Mann-Whitney U p-value:{" "}
              {misuse.demographics.age.mannwhitney_p_value !== null
                ? misuse.demographics.age.mannwhitney_p_value.toExponential(2)
                : "N/A"}
              {misuse.demographics.age.note && ` -- ${misuse.demographics.age.note}`}
            </p>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Sex</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-1.5 pr-4">Sex</th>
                  <th className="py-1.5 pr-4">Misuse</th>
                  <th className="py-1.5 pr-4">Therapeutic</th>
                </tr>
              </thead>
              <tbody>
                {sexes.map((sex) => (
                  <tr key={sex} className="border-b border-slate-100">
                    <td className="py-1.5 pr-4 capitalize">{sex}</td>
                    <td className="py-1.5 pr-4">{sexTable[sex].misuse}</td>
                    <td className="py-1.5 pr-4">{sexTable[sex].therapeutic}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {misuse.demographics.sex.fisher_p_value !== undefined && (
              <p className="mt-2 text-xs text-slate-500">
                Fisher&apos;s exact p-value: {misuse.demographics.sex.fisher_p_value.toExponential(2)}
              </p>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
