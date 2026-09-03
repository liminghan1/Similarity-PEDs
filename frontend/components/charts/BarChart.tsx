"use client";

import { PlotlyChart } from "@/components/PlotlyChart";

export interface BarDatum {
  label: string;
  value: number;
  annotation?: string;
  computable?: boolean;
}

export function BarChart({
  data,
  yAxisTitle,
  height = 420,
  valueLabel,
}: {
  data: BarDatum[];
  yAxisTitle?: string;
  height?: number;
  /** What each bar's value represents, e.g. "logROR" -- shown on hover instead of Plotly's
   * default generic "x/y" labels. Falls back to yAxisTitle, then "value". */
  valueLabel?: string;
}) {
  const label = valueLabel ?? yAxisTitle ?? "value";
  return (
    <div style={{ height }}>
      <PlotlyChart
        data={[
          {
            type: "bar",
            x: data.map((d) => d.label),
            y: data.map((d) => d.value),
            marker: { color: data.map((d) => (d.computable === false ? "#cbd5e1" : "#4477aa")) },
            text: data.map((d) => d.annotation ?? ""),
            textposition: "outside",
            customdata: data.map((d) => (d.computable === false ? " (not computable)" : "")),
            hovertemplate: `%{x}<br>${label}: %{y:.2f}%{customdata}<extra></extra>`,
          },
        ]}
        layout={{
          margin: { l: 60, r: 20, t: 20, b: 100 },
          xaxis: { tickangle: -35 },
          yaxis: { title: yAxisTitle ? { text: yAxisTitle } : undefined, zeroline: true },
        }}
      />
    </div>
  );
}
