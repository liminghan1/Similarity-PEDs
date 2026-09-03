"use client";

import { PlotlyChart } from "@/components/PlotlyChart";

export function ScatterPlot({
  x,
  y,
  text,
  xTitle,
  yTitle,
  height = 420,
}: {
  x: number[];
  y: number[];
  text?: string[];
  xTitle?: string;
  yTitle?: string;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <PlotlyChart
        data={[
          {
            type: "scatter",
            mode: "markers",
            x,
            y,
            text,
            hoverinfo: text ? "text+x+y" : "x+y",
            marker: { size: 10, color: "#4477aa", line: { color: "#1e293b", width: 1 } },
          },
        ]}
        layout={{
          margin: { l: 60, r: 20, t: 10, b: 50 },
          xaxis: { title: xTitle ? { text: xTitle } : undefined },
          yaxis: { title: yTitle ? { text: yTitle } : undefined },
        }}
      />
    </div>
  );
}
