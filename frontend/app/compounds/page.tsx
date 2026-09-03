import Link from "next/link";
import { Card } from "@/components/Card";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getCompounds } from "@/lib/api";

export default async function CompoundsPage() {
  const compounds = await getCompounds();

  return (
    <div className="space-y-6">
      <Card title="Compound Explorer">
        <p className="text-sm text-slate-600">
          <ProvenanceBadge kind="OBSERVED" /> Structure and receptor bioactivity data are as
          retrieved from PubChem/ChEMBL/BindingDB. FAERS report counts are deduplicated, matched
          counts (Phase 6). Click a compound for full detail, aliases, and bioactivity records.
        </p>
      </Card>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Compound</th>
                <th className="py-2 pr-4">Formula</th>
                <th className="py-2 pr-4">MW (g/mol)</th>
                <th className="py-2 pr-4">Aliases</th>
                <th className="py-2 pr-4">Formulations</th>
                <th className="py-2 pr-4">Bioactivity records</th>
                <th className="py-2 pr-4">FAERS reports</th>
              </tr>
            </thead>
            <tbody>
              {compounds.map((c) => (
                <tr key={c.canonical_name} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 pr-4">
                    <Link
                      href={`/compounds/${encodeURIComponent(c.canonical_name)}`}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {c.canonical_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs">{c.molecular_formula ?? "--"}</td>
                  <td className="py-2 pr-4">{c.molecular_weight?.toFixed(2) ?? "--"}</td>
                  <td className="py-2 pr-4">{c.n_aliases}</td>
                  <td className="py-2 pr-4">{c.n_formulations}</td>
                  <td className="py-2 pr-4">
                    {c.n_bioactivities > 0 ? (
                      c.n_bioactivities
                    ) : (
                      <span className="text-slate-400">0 (no receptor data)</span>
                    )}
                  </td>
                  <td className="py-2 pr-4">{c.n_faers_reports.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
