"use client";

import { PlotlyChart } from "@/components/PlotlyChart";

export interface BarDatum {
  label: string;
  value: number;
  annotation?: string;
  computable?: boolean;
}

export function BarChart({ data, yAxisTitle, height = 420 }: { data: BarDatum[]; yAxisTitle?: string; height?: number }) {
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
            hoverinfo: "x+y+text",
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
