"use client";

import { useMemo, useState } from "react";
import { ChartExplainer } from "@/components/ChartExplainer";
import { BarChart } from "@/components/charts/BarChart";
import type { MatrixResponse } from "@/types/api";

function lookup(matrix: MatrixResponse, rowLabel: string, colLabel: string): number | null {
  const i = matrix.labels.indexOf(rowLabel);
  const j = matrix.columns.indexOf(colLabel);
  if (i === -1 || j === -1) return null;
  return matrix.values[i][j];
}

export function CompoundPairComparison({
  compoundNames,
  structureSimilarity,
  safetySimilarity,
  molecularDescriptors,
  safetyPhenotype,
}: {
  compoundNames: string[];
  structureSimilarity: MatrixResponse;
  safetySimilarity: MatrixResponse;
  molecularDescriptors: MatrixResponse;
  safetyPhenotype: MatrixResponse;
}) {
  const [compoundA, setCompoundA] = useState(compoundNames[0]);
  const [compoundB, setCompoundB] = useState(compoundNames[1] ?? compoundNames[0]);

  const structureDist = lookup(structureSimilarity, compoundA, compoundB);
  const safetyDist = lookup(safetySimilarity, compoundA, compoundB);

  const descriptorRows = useMemo(() => {
    const iA = molecularDescriptors.labels.indexOf(compoundA);
    const iB = molecularDescriptors.labels.indexOf(compoundB);
    if (iA === -1 || iB === -1) return [];
    return molecularDescriptors.columns.map((col, j) => ({
      column: col,
      a: molecularDescriptors.values[iA][j],
      b: molecularDescriptors.values[iB][j],
    }));
  }, [molecularDescriptors, compoundA, compoundB]);

  const safetyBarData = useMemo(() => {
    const iA = safetyPhenotype.labels.indexOf(compoundA);
    const iB = safetyPhenotype.labels.indexOf(compoundB);
    if (iA === -1 || iB === -1) return { a: [], b: [] };
    return {
      a: safetyPhenotype.columns.map((col, j) => ({
        label: col,
        value: safetyPhenotype.values[iA][j] ?? 0,
        computable: safetyPhenotype.values[iA][j] !== null,
      })),
      b: safetyPhenotype.columns.map((col, j) => ({
        label: col,
        value: safetyPhenotype.values[iB][j] ?? 0,
        computable: safetyPhenotype.values[iB][j] !== null,
      })),
    };
  }, [safetyPhenotype, compoundA, compoundB]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Compound A</span>
          <select
            value={compoundA}
            onChange={(e) => setCompoundA(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5 capitalize"
          >
            {compoundNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Compound B</span>
          <select
            value={compoundB}
            onChange={(e) => setCompoundB(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5 capitalize"
          >
            {compoundNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Structural distance</div>
          <div className="text-2xl font-semibold text-slate-900">
            {structureDist !== null ? structureDist.toFixed(3) : "N/A"}
          </div>
          <div className="text-xs text-slate-500">0 = identical, 1 = maximally distant</div>
        </div>
        <div className="rounded border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Safety-phenotype distance</div>
          <div className="text-2xl font-semibold text-slate-900">
            {safetyDist !== null ? safetyDist.toFixed(3) : "Not computable (<3 shared categories)"}
          </div>
          <div className="text-xs text-slate-500">1 - Pearson correlation on shared logROR categories</div>
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Molecular descriptors</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="py-1.5 pr-4">Descriptor</th>
              <th className="py-1.5 pr-4 capitalize">{compoundA}</th>
              <th className="py-1.5 pr-4 capitalize">{compoundB}</th>
            </tr>
          </thead>
          <tbody>
            {descriptorRows.map((row) => (
              <tr key={row.column} className="border-b border-slate-100">
                <td className="py-1 pr-4 text-slate-600">{row.column}</td>
                <td className="py-1 pr-4">{typeof row.a === "number" ? row.a.toFixed(3) : row.a}</td>
                <td className="py-1 pr-4">{typeof row.b === "number" ? row.b.toFixed(3) : row.b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ChartExplainer>
        Bars above zero mean that adverse-event category is reported more often for this compound
        than for the rest of the cohort; bars below zero mean less often (same logROR measure as
        the heatmap on the Safety Phenotype page). Gray bars mean there wasn&apos;t enough data
        (fewer than 3 reports) to compute a reliable number for that category.
      </ChartExplainer>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold capitalize text-slate-700">{compoundA}: safety profile (logROR)</h3>
          <BarChart data={safetyBarData.a} height={320} valueLabel="logROR" />
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold capitalize text-slate-700">{compoundB}: safety profile (logROR)</h3>
          <BarChart data={safetyBarData.b} height={320} valueLabel="logROR" />
        </div>
      </div>
    </div>
  );
}
