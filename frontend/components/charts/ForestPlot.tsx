"use client";

import { PlotlyChart } from "@/components/PlotlyChart";

export interface ForestPlotRow {
  label: string;
  oddsRatio: number;
  ciLow: number;
  ciHigh: number;
  pValue: number;
  /** Overrides the default `pValue < 0.05` red/gray split -- pass this whenever a corrected
   * significance flag (e.g. FDR q<0.05) is available, so the plot never highlights a result on
   * an uncorrected p-value alone. */
  significant?: boolean;
  /** Corrected p-value (e.g. FDR q-value), shown alongside the raw p-value on hover when given. */
  qValue?: number;
}

/** Odds-ratio forest plot on a log x-axis, matching Figure 9's convention (project brief Sec. 22:
 * report effect sizes + CI, not p-values alone). Points are highlighted red using `significant`
 * when provided, else raw `pValue < 0.05`. */
export function ForestPlot({ rows, height = 420 }: { rows: ForestPlotRow[]; height?: number }) {
  const sorted = [...rows].sort((a, b) => a.oddsRatio - b.oddsRatio);
  const colors = sorted.map((r) => ((r.significant ?? r.pValue < 0.05) ? "#b91c1c" : "#64748b"));

  return (
    <div style={{ height }}>
      <PlotlyChart
        data={[
          {
            type: "scatter",
            mode: "markers",
            x: sorted.map((r) => r.oddsRatio),
            y: sorted.map((r) => r.label),
            error_x: {
              type: "data",
              symmetric: false,
              array: sorted.map((r) => r.ciHigh - r.oddsRatio),
              arrayminus: sorted.map((r) => r.oddsRatio - r.ciLow),
              color: "#94a3b8",
            },
            marker: { color: colors, size: 10 },
            text: sorted.map((r) =>
              r.qValue !== undefined
                ? `OR=${r.oddsRatio.toFixed(2)}, p=${r.pValue.toFixed(4)}, FDR q=${r.qValue.toFixed(4)}`
                : `OR=${r.oddsRatio.toFixed(2)}, p=${r.pValue.toFixed(4)}`,
            ),
            hoverinfo: "text+y",
          },
        ]}
        layout={{
          margin: { l: 130, r: 30, t: 10, b: 40 },
          xaxis: { type: "log", title: { text: "Odds Ratio (log scale)" }, zeroline: false },
          shapes: [
            {
              type: "line",
              x0: 1,
              x1: 1,
              y0: -0.5,
              y1: sorted.length - 0.5,
              line: { color: "#0f172a", width: 1, dash: "dash" },
            },
          ],
        }}
      />
    </div>
  );
}
