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
}: {
  labels: string[];
  columns: string[];
  values: (number | null)[][];
  colorscale?: string | Array<[number, string]>;
  zmin?: number;
  zmax?: number;
  height?: number;
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
