import { Card } from "@/components/Card";
import { ChartExplainer } from "@/components/ChartExplainer";
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

  const h1 = assoc.results.find((r) => r.description.startsWith("H1"));
  const h2a = assoc.results.find((r) => r.description.startsWith("H2a"));
  const h2b = assoc.results.find((r) => r.description.startsWith("H2b"));

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
              H1, receptor pharmacology vs. safety:{" "}
              {h1?.computable ? "computable" : <strong>NOT COMPUTABLE</strong>} -- {h1?.reason}
            </span>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <AnalysisLabelBadge label="SECONDARY" />
            <span>
              H2a, structure-only vs. safety: n={h2a?.n_objects}, Spearman rho=
              {h2a?.statistic_spearman_rho?.toFixed(3)}, one-sided p=
              {h2a?.p_value_one_sided?.toFixed(3)} -- no significant positive association found.
            </span>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <AnalysisLabelBadge label="SECONDARY" />
            <span>
              H2b, combined structure+receptor vs. safety:{" "}
              {h2b?.computable ? "computable" : <strong>NOT COMPUTABLE</strong>} -- {h2b?.reason}
            </span>
          </div>
        </div>
        <ChartExplainer>
          H1 (does receptor pharmacology similarity predict safety-profile similarity?) and H2b
          (does adding receptor pharmacology to structure explain more than structure alone?) both
          require the combined/receptor-only distance matrices, which need receptor-bioactivity
          data this cohort mostly lacks (7/10 compounds have zero measurements) -- both are{" "}
          <strong>not computable</strong>, not negative results. H2a (structure-only, below) is the
          one fully computable test. <strong>Spearman rho</strong> measures how consistently one
          distance ranks alongside the other, from -1 (perfectly opposite -- more structurally
          similar pairs tend to have <em>more</em> different safety profiles) through 0 (no
          relationship) to +1 (perfectly matching, which is what H2a predicted). A negative or
          near-zero rho, as found here, is evidence against the hypothesis. The{" "}
          <strong>p-value</strong> is the probability of seeing a rho this extreme by random chance
          alone if there were truly no relationship -- it comes from comparing the observed rho
          against 9,999 random relabelings of the same data (a permutation test), not a textbook
          formula. Smaller p = stronger evidence; a one-sided p=0.956 here means the data point in
          the opposite direction from what was predicted.
        </ChartExplainer>
      </Card>

      <Card title="All compound pairs: structural vs. safety distance">
        <ChartExplainer>
          Each dot is one pair of compounds (e.g. &quot;testosterone vs. trenbolone&quot;). The x-axis is how
          structurally different the two compounds are (0 = essentially identical, 1 = very
          different). The y-axis is how different their FAERS safety-reporting profiles are (0 =
          nearly identical reporting patterns, higher = more different). If molecular similarity
          predicted safety-profile similarity, structurally-similar pairs (left side) would cluster
          toward the bottom (low safety distance too), producing a rising trend left-to-right. The
          statistical test above (Spearman rho, not a visual read of this scatter) found no such
          trend in this data.
        </ChartExplainer>
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
