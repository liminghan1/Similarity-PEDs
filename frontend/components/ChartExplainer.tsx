/**
 * Plain-language "how to read this" callout, placed directly above/below a chart or result
 * table. Distinct from ProvenanceBadge (which labels what KIND of data something is) -- this
 * explains HOW to interpret it, for a reader with no prior context on this project's methods.
 */
export function ChartExplainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-4 rounded border border-blue-100 bg-blue-50/60 px-3 py-2 text-sm text-slate-700">
      <span className="font-semibold text-blue-900">How to read this: </span>
      {children}
    </div>
  );
}
