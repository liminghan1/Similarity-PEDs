"use client";

import { PlotlyChart } from "@/components/PlotlyChart";

export function Heatmap({
  labels,
  columns,
  values,
  colorscale = "Viridis",
  zmin,
  zmax,
  height = 500,
  valueLabel = "value",
}: {
  labels: string[];
  columns: string[];
  values: (number | null)[][];
  colorscale?: string | Array<[number, string]>;
  zmin?: number;
  zmax?: number;
  height?: number;
  /** What the color/number represents, e.g. "logROR" -- shown in the colorbar title and on hover
   * instead of Plotly's default generic "x/y/z" labels. */
  valueLabel?: string;
}) {
  return (
    <div style={{ height }}>
      <PlotlyChart
        data={[
          {
            type: "heatmap",
            z: values,
            x: columns,
            y: labels,
            colorscale,
            zmin,
            zmax,
            hoverongaps: false,
            texttemplate: "%{z:.2f}",
            textfont: { size: 9 },
            hovertemplate: `%{y} × %{x}<br>${valueLabel}: %{z:.2f}<extra></extra>`,
            colorbar: { title: { text: valueLabel, side: "right" } },
          },
        ]}
        layout={{
          margin: { l: 110, r: 40, t: 20, b: 90 },
          xaxis: { tickangle: -45 },
          autosize: true,
        }}
      />
    </div>
  );
}
