import Link from "next/link";
import { Card, Stat } from "@/components/Card";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getCompound, getCompounds } from "@/lib/api";

export async function generateStaticParams() {
  const compounds = await getCompounds();
  return compounds.map((c) => ({ name: c.canonical_name }));
}

export default async function CompoundDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const compound = await getCompound(name);

  return (
    <div className="space-y-6">
      <Link href="/compounds" className="text-sm text-blue-700 hover:underline">
        &larr; Back to Compound Explorer
      </Link>

      <Card>
        <h1 className="text-2xl font-bold capitalize text-slate-900">{compound.canonical_name}</h1>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Molecular formula" value={compound.molecular_formula ?? "--"} />
          <Stat label="Molecular weight" value={compound.molecular_weight?.toFixed(2) ?? "--"} sub="g/mol" />
          <Stat label="PubChem CID" value={compound.pubchem_cid ?? "--"} />
          <Stat label="ChEMBL ID" value={compound.chembl_id ?? "--"} />
        </div>
        <div className="mt-4 space-y-1 text-sm">
          <div>
            <span className="font-medium text-slate-700">Canonical SMILES: </span>
            <code className="break-all rounded bg-slate-100 px-1">{compound.smiles}</code>
          </div>
          {compound.isomeric_smiles && (
            <div>
              <span className="font-medium text-slate-700">Isomeric SMILES: </span>
              <code className="break-all rounded bg-slate-100 px-1">{compound.isomeric_smiles}</code>
            </div>
          )}
          <div>
            <span className="font-medium text-slate-700">InChIKey: </span>
            <code className="rounded bg-slate-100 px-1">{compound.inchikey}</code>
          </div>
        </div>
      </Card>

      <Card
        title={
          <span>
            Aliases &amp; formulations <ProvenanceBadge kind="OBSERVED" />
          </span>
        }
      >
        {compound.aliases.length === 0 ? (
          <p className="text-sm text-slate-500">No aliases recorded.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Alias</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Scope</th>
                <th className="py-2 pr-4">Verified</th>
                <th className="py-2 pr-4">Source</th>
              </tr>
            </thead>
            <tbody>
              {compound.aliases.map((a, i) => {
                const formulation = compound.formulations.find((f) => f.id === a.formulation_id);
                return (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium">{a.alias}</td>
                    <td className="py-2 pr-4">{a.alias_type}</td>
                    <td className="py-2 pr-4">
                      {formulation ? formulation.formulation_name : <span className="text-slate-400">parent compound</span>}
                    </td>
                    <td className="py-2 pr-4">{a.verified ? "✓" : "pending"}</td>
                    <td className="py-2 pr-4 text-xs text-slate-500">{a.source ?? "--"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      <Card
        title={
          <span>
            Receptor bioactivity <ProvenanceBadge kind="OBSERVED" />
          </span>
        }
      >
        {compound.bioactivities.length === 0 ? (
          <p className="text-sm text-slate-500">
            No receptor bioactivity measurements found in ChEMBL/BindingDB for this compound (a
            real data-coverage gap, not a missing lookup -- see the Methods page).
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Target</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Relation</th>
                <th className="py-2 pr-4">Value (nM)</th>
                <th className="py-2 pr-4">pActivity</th>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Assay confidence</th>
              </tr>
            </thead>
            <tbody>
              {compound.bioactivities.map((b, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-2 pr-4">
                    {b.target_name} {b.target_gene_symbol && `(${b.target_gene_symbol})`}
                  </td>
                  <td className="py-2 pr-4">{b.measurement_type}</td>
                  <td className="py-2 pr-4 font-mono">{b.relation}</td>
                  <td className="py-2 pr-4">{b.standardized_value_nm?.toFixed(2) ?? "--"}</td>
                  <td className="py-2 pr-4">{b.p_activity?.toFixed(2) ?? "--"}</td>
                  <td className="py-2 pr-4">{b.source}</td>
                  <td className="py-2 pr-4">{b.assay_confidence_score ?? "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="FAERS coverage">
        <p className="text-sm text-slate-700">
          <strong>{compound.n_faers_reports.toLocaleString()}</strong> deduplicated FAERS reports
          mention this compound (Phase 6). See the{" "}
          <Link href="/safety" className="text-blue-700 hover:underline">
            Safety Phenotype
          </Link>{" "}
          page for per-category signal detail.
        </p>
      </Card>
    </div>
  );
}
