"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";
import createPlotlyComponent from "react-plotly.js/factory";

// plotly.js-dist-min (not the full plotly.js) keeps the client bundle smaller; it touches
// `window`/canvas APIs at import time, so it (and the component built from it) must never be
// imported during server rendering -- next/dynamic(..., { ssr: false }) enforces that.
const Plot = dynamic(
  async () => {
    const Plotly = (await import("plotly.js-dist-min")).default;
    return createPlotlyComponent(Plotly);
  },
  { ssr: false, loading: () => <ChartSkeleton /> },
);

function ChartSkeleton() {
  return (
    <div className="flex h-96 items-center justify-center rounded border border-dashed border-slate-300 text-sm text-slate-400">
      Loading chart...
    </div>
  );
}

export type PlotlyChartProps = ComponentProps<typeof Plot>;

export function PlotlyChart(props: PlotlyChartProps) {
  return (
    <Plot
      useResizeHandler
      style={{ width: "100%", height: "100%" }}
      config={{ displaylogo: false, responsive: true }}
      {...props}
    />
  );
}
