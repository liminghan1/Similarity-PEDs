import { Card } from "@/components/Card";
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
        <Heatmap
          labels={matrix.labels}
          columns={matrix.columns}
          values={matrix.values}
          colorscale="RdBu"
          zmin={-3}
          zmax={3}
          height={480}
        />
        <p className="mt-2 text-xs text-slate-500">
          Gray/blank cells: sparse (fewer than 3 reports for that cell) or the compound falls
          below the 20-report minimum -- excluded as unreliable, not shown as zero.
        </p>
      </Card>

      <Card title="Full signal table (a/b/c/d, ROR, CI)">
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
