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
  }));

  const sexTable = misuse.demographics.sex.table;
  const sexes = Object.keys(sexTable);

  return (
    <div className="space-y-6">
      <Card title="Therapeutic vs. Misuse">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <AnalysisLabelBadge label="SECONDARY" />
          <ProvenanceBadge kind="DERIVED" />
          <span className="text-sm text-slate-600">
            H3: reports coded (by indication/route/reporter-narrative signals, see Methods) as
            misuse/non-medical-use vs. therapeutic/medical use, compared on outcome severity and
            adverse-event category. Odds ratios via Fisher&apos;s exact test.
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
          group. Red = p &lt; 0.05 (uncorrected). Death shows no significant difference; serious
          and hospitalization outcomes are reported significantly more often in the misuse group.
        </p>
      </Card>

      <Card title="Adverse-event category: misuse vs. therapeutic (odds ratio)">
        <ChartExplainer>
          Same reading as the chart above, now broken out by adverse-event category instead of by
          outcome severity: a category to the right of the dashed line at OR=1 is reported
          proportionally more often among misuse-coded reports; to the left, more often among
          therapeutic-coded reports. The x-axis is log-scaled (equal visual distance = equal
          multiplicative difference) since these odds ratios range from about 0.4x to nearly 8x.
        </ChartExplainer>
        <ForestPlot rows={categoryRows} height={420} />
        <p className="mt-2 text-xs text-slate-500">
          Not corrected for multiple comparisons across the {categoryRows.length} categories --
          treat individual category p-values as exploratory (see Limitations).
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
