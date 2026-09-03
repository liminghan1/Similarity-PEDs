import { Card, Stat } from "@/components/Card";
import { ChartExplainer } from "@/components/ChartExplainer";
import { AnalysisLabelBadge, ProvenanceBadge } from "@/components/ProvenanceBadge";
import { getClustering } from "@/lib/api";

export default async function ClusteringPage() {
  const clustering = await getClustering();

  const compounds = [...clustering.compounds].sort();

  return (
    <div className="space-y-6">
      <Card title="Clustering">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <AnalysisLabelBadge label="SECONDARY" />
          <ProvenanceBadge kind="MODEL OUTPUT" />
          <span className="text-sm text-slate-600">
            Hierarchical clustering (average linkage), k chosen by max silhouette over k=2..5, run
            independently on the structure and safety distance matrices, then compared.
          </span>
        </div>
        <ChartExplainer>
          Two separate groupings were made -- one from molecular structure, one from FAERS safety
          profiles -- each sorting the 10 compounds into a small number of groups (k) of compounds
          that are most similar to each other on that axis, using no information about the other
          axis. If molecular structure predicted safety-reporting behavior, compounds grouped
          together by structure should tend to also be grouped together by safety profile. The
          three numbers below measure whether that happened.
        </ChartExplainer>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Compounds clustered" value={clustering.n_compounds} />
          <Stat
            label="Structure cophenetic corr."
            value={clustering.structure_clustering.cophenetic_correlation.toFixed(3)}
            sub={`k=${clustering.structure_clustering.k}`}
          />
          <Stat
            label="Safety cophenetic corr."
            value={clustering.safety_clustering.cophenetic_correlation.toFixed(3)}
            sub={`k=${clustering.safety_clustering.k}`}
          />
          <Stat
            label="Cluster agreement (ARI)"
            value={clustering.cluster_agreement.adjusted_rand_index.toFixed(3)}
            sub={`NMI=${clustering.cluster_agreement.normalized_mutual_information.toFixed(3)}`}
          />
        </div>
        <p className="mt-3 text-sm text-slate-600">
          <strong>Cophenetic correlation</strong> (0-1) is a quality check on the clustering itself:
          how faithfully the grouping preserves the actual pairwise distances -- closer to 1 means
          the groups are a good summary of the underlying data, independent of whether the two
          groupings agree with each other. <strong>Adjusted Rand Index (ARI)</strong> and{" "}
          <strong>Normalized Mutual Information (NMI)</strong> both measure that agreement between
          the structure-based and safety-based groupings: 1 = identical groupings, 0 = no better
          than randomly guessing which compounds go together, and (for ARI specifically) negative
          values mean the two groupings disagree more than random chance would. A negative ARI
          here means the structure-based and safety-based clusters agree{" "}
          <strong>no better than chance</strong> -- this is a negative/null result, reported as
          such, not reframed as a positive finding.
        </p>
      </Card>

      <Card title="Receptor-based clustering">
        <p className="text-sm text-slate-700">{clustering.receptor_clustering}</p>
      </Card>

      <Card title="Cluster assignments: structure vs. safety">
        <ChartExplainer>
          The cluster numbers themselves are arbitrary labels (1, 2, ...) with no inherent order or
          meaning -- what matters is which compounds share the same number within a column.
          Compounds with the same &quot;Structure cluster&quot; number were grouped together based on
          molecular similarity; compounds with the same &quot;Safety cluster&quot; number were grouped
          together based on FAERS reporting-profile similarity. If the two columns told the same
          story, compounds sharing a structure cluster would also tend to share a safety cluster --
          here, most compounds share safety cluster 1 regardless of their structure cluster,
          which is the low-agreement result summarized above.
        </ChartExplainer>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-4">Compound</th>
              <th className="py-2 pr-4">Structure cluster</th>
              <th className="py-2 pr-4">Safety cluster</th>
            </tr>
          </thead>
          <tbody>
            {compounds.map((name) => {
              const sCluster = clustering.structure_clustering.cluster_labels[name];
              const safetyCluster = clustering.safety_clustering.cluster_labels[name];
              return (
                <tr key={name} className="border-b border-slate-100">
                  <td className="py-1.5 pr-4 capitalize">{name}</td>
                  <td className="py-1.5 pr-4">{sCluster}</td>
                  <td className="py-1.5 pr-4">{safetyCluster}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card
        title={
          <span className="flex items-center gap-2">
            PCA + k-means <AnalysisLabelBadge label="EXPLORATORY" />
          </span>
        }
      >
        <p className="mb-3 text-sm text-slate-600">
          {clustering.pca_kmeans_exploratory.note}. Shown for completeness; not used for any
          hypothesis test or headline claim.
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-4">Compound</th>
              <th className="py-2 pr-4">PCA+k-means cluster</th>
            </tr>
          </thead>
          <tbody>
            {compounds.map((name) => (
              <tr key={name} className="border-b border-slate-100">
                <td className="py-1.5 pr-4 capitalize">{name}</td>
                <td className="py-1.5 pr-4">{clustering.pca_kmeans_exploratory.cluster_labels[name]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
