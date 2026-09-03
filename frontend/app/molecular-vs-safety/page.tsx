import { Card } from "@/components/Card";
import { CompoundPairComparison } from "@/components/CompoundPairComparison";
import { ScatterPlot } from "@/components/charts/ScatterPlot";
import { AnalysisLabelBadge, ProvenanceBadge } from "@/components/ProvenanceBadge";
import {
  getMatrixAssociation,
  getMolecularPhenotype,
  getSafetyPhenotype,
  getSimilarityMatrix,
} from "@/lib/api";

export default async function MolecularVsSafetyPage() {
  const [structureSimilarity, safetySimilarity, molecularDescriptors, safetyPhenotype, assoc] =
    await Promise.all([
      getSimilarityMatrix("structure"),
      getSimilarityMatrix("safety"),
      getMolecularPhenotype(),
      getSafetyPhenotype(),
      getMatrixAssociation(),
    ]);

  const h2 = assoc.results.find((r) => r.description.includes("structure-only"));
  const h1 = assoc.results.find((r) => r.label === "PRIMARY");

  const labels = structureSimilarity.labels;
  const scatterX: number[] = [];
  const scatterY: number[] = [];
  const scatterText: string[] = [];
  for (let i = 0; i < labels.length; i++) {
    for (let j = i + 1; j < labels.length; j++) {
      const sd = safetySimilarity.values[i][j];
      if (sd !== null) {
        scatterX.push(structureSimilarity.values[i][j] ?? 0);
        scatterY.push(sd);
        scatterText.push(`${labels[i]} vs. ${labels[j]}`);
      }
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Molecular vs. Safety Similarity">
        <p className="text-sm text-slate-600">
          <ProvenanceBadge kind="INTERPRETATION" /> The central research question: do compounds
          more similar in molecular structure/receptor pharmacology also show more similar FAERS
          safety-reporting profiles? Statistical inference is the permutation-based matrix-
          association test below, not this scatter (illustration only).
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <AnalysisLabelBadge label="PRIMARY" />
            <span>
              Combined structure+receptor vs. safety:{" "}
              {h1?.computable ? "computable" : <strong>NOT COMPUTABLE</strong>} -- {h1?.reason}
            </span>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <AnalysisLabelBadge label="SECONDARY" />
            <span>
              Structure-only vs. safety: n={h2?.n_objects}, Spearman rho=
              {h2?.statistic_spearman_rho?.toFixed(3)}, one-sided p=
              {h2?.p_value_one_sided?.toFixed(3)} -- no significant positive association found.
            </span>
          </div>
        </div>
      </Card>

      <Card title="All compound pairs: structural vs. safety distance">
        <ScatterPlot
          x={scatterX}
          y={scatterY}
          text={scatterText}
          xTitle="Structural distance"
          yTitle="Safety-phenotype distance"
          height={420}
        />
        <p className="mt-2 text-xs text-slate-500">
          {scatterX.length} compound pairs with a defined safety distance (out of {(labels.length * (labels.length - 1)) / 2}
          {" "}total pairs).
        </p>
      </Card>

      <Card title="Compare two compounds directly">
        <CompoundPairComparison
          compoundNames={labels}
          structureSimilarity={structureSimilarity}
          safetySimilarity={safetySimilarity}
          molecularDescriptors={molecularDescriptors}
          safetyPhenotype={safetyPhenotype}
        />
      </Card>
    </div>
  );
}
