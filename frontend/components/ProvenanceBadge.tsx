/**
 * Project brief Sec. 37: "Separate OBSERVED DATA from DERIVED STATISTICS from MODEL OUTPUT from
 * INTERPRETATION. Use labels." This component is that label, used consistently across every page
 * that shows a number derived from FAERS/ChEMBL/BindingDB data.
 */
const STYLES: Record<string, string> = {
  OBSERVED: "bg-slate-100 text-slate-700 border-slate-300",
  DERIVED: "bg-blue-50 text-blue-800 border-blue-300",
  "MODEL OUTPUT": "bg-purple-50 text-purple-800 border-purple-300",
  INTERPRETATION: "bg-amber-50 text-amber-900 border-amber-300",
};

export function ProvenanceBadge({
  kind,
}: {
  kind: "OBSERVED" | "DERIVED" | "MODEL OUTPUT" | "INTERPRETATION";
}) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STYLES[kind]}`}
    >
      {kind}
    </span>
  );
}

export function AnalysisLabelBadge({
  label,
}: {
  label: "PRIMARY" | "SECONDARY" | "EXPLORATORY" | string;
}) {
  const styles: Record<string, string> = {
    PRIMARY: "bg-red-50 text-red-800 border-red-300",
    SECONDARY: "bg-blue-50 text-blue-800 border-blue-300",
    EXPLORATORY: "bg-slate-100 text-slate-600 border-slate-300",
  };
  const style = styles[label] ?? styles.EXPLORATORY;
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}
