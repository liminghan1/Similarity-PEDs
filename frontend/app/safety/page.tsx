import { Card } from "@/components/Card";
import { ChartExplainer } from "@/components/ChartExplainer";
import { Heatmap } from "@/components/charts/Heatmap";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getSafetyPhenotype, getSafetySignalTable } from "@/lib/api";

export default async function SafetyPhenotypePage() {
  const [matrix, signalTable] = await Promise.all([getSafetyPhenotype(), getSafetySignalTable()]);

  const sortedRows = [...signalTable].sort(
    (a, b) => a.canonical_name.localeCompare(b.canonical_name) || a.category.localeCompare(b.category),
  );

  return (
    <div className="space-y-6">
      <Card title="Safety Phenotype">
        <p className="text-sm text-slate-600">
          <ProvenanceBadge kind="DERIVED" /> log Reporting Odds Ratio (logROR) per compound x
          research-defined adverse-event category, computed against a cohort-relative background
          (compound vs. the rest of the 10-compound cohort&apos;s FAERS reports). This is a{" "}
          <strong>reporting association</strong>, not a measure of clinical risk or incidence --
          see the Methods and Limitations pages.
        </p>
      </Card>

      <Card title="logROR heatmap">
        <ChartExplainer>
          Each cell compares one compound (row) to the rest of the 10-compound cohort, for one
          adverse-event category (column). <strong>Red means that category is reported more often
          for this compound than for the cohort average; blue means less often</strong> -- the
          deeper the color, the bigger the difference. Light gray (near 0) means roughly no
          difference. A cell being red does not mean that reaction is common or dangerous for this
          compound in absolute terms, only that it shows up disproportionately more in FAERS
          reports for this compound versus the others. Hover a cell for the exact number.
        </ChartExplainer>
        <Heatmap
          labels={matrix.labels}
          columns={matrix.columns}
          values={matrix.values}
          colorscale="RdBu"
          zmin={-3}
          zmax={3}
          height={480}
          valueLabel="logROR"
        />
        <p className="mt-2 text-xs text-slate-500">
          White/blank cells: sparse (fewer than 3 reports for that cell) or the compound falls
          below the 20-report minimum -- excluded as unreliable, not shown as zero.
        </p>
      </Card>

      <Card title="Full signal table (a/b/c/d, ROR, CI)">
        <ChartExplainer>
          This is the raw arithmetic behind every cell in the heatmap above, so nothing is a &quot;black
          box.&quot; <strong>a/b/c/d</strong> are the four counts of a 2x2 table: a = reports of this
          compound with this reaction category, b = reports of this compound without it, c =
          reports of other cohort compounds with it, d = reports of other cohort compounds without
          it. <strong>ROR</strong> (Reporting Odds Ratio) = (a/b) &divide; (c/d) -- how many times
          more (or less) often this reaction is reported for this compound versus the rest of the
          cohort. <strong>logROR</strong> is just log(ROR): 0 = no difference, positive = reported
          more, negative = reported less (this is what&apos;s colored in the heatmap). The 95% CI is the
          range of plausible ROR values; when it includes 1, the apparent difference could be
          chance.
        </ChartExplainer>
        <p className="mb-3 text-xs text-slate-500">
          Per research/analysis_plan.md Sec. 1: report count, serious/hospitalization/death
          counts, and the full 2x2 contingency table are always shown alongside logROR, never a
          bare number. Sparse cells (fewer than 3 reports) are flagged, not hidden.
        </p>
        <div className="max-h-[600px] overflow-auto">
          <table className="w-full min-w-[900px] border-collapse text-xs">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-slate-300 text-left uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">Compound</th>
                <th className="py-2 pr-3">Category</th>
                <th className="py-2 pr-3">a</th>
                <th className="py-2 pr-3">b</th>
                <th className="py-2 pr-3">c</th>
                <th className="py-2 pr-3">d</th>
                <th className="py-2 pr-3">ROR</th>
                <th className="py-2 pr-3">logROR</th>
                <th className="py-2 pr-3">95% CI</th>
                <th className="py-2 pr-3">Sparse?</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row, i) => (
                <tr
                  key={i}
                  className={`border-b border-slate-100 ${row.sparse_cell || !row.compound_meets_minimum ? "text-slate-400" : ""}`}
                >
                  <td className="py-1.5 pr-3 capitalize">{row.canonical_name}</td>
                  <td className="py-1.5 pr-3">{row.category}</td>
                  <td className="py-1.5 pr-3">{row.a}</td>
                  <td className="py-1.5 pr-3">{row.b}</td>
                  <td className="py-1.5 pr-3">{row.c}</td>
                  <td className="py-1.5 pr-3">{row.d}</td>
                  <td className="py-1.5 pr-3">{row.ror.toFixed(2)}</td>
                  <td className="py-1.5 pr-3">{row.log_ror.toFixed(2)}</td>
                  <td className="py-1.5 pr-3">
                    [{row.ci_low.toFixed(2)}, {row.ci_high.toFixed(2)}]
                  </td>
                  <td className="py-1.5 pr-3">
                    {row.sparse_cell ? "sparse" : !row.compound_meets_minimum ? "compound<20" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
