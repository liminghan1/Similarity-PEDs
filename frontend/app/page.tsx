import { AnalysisLabelBadge } from "@/components/ProvenanceBadge";
import { Card, Stat } from "@/components/Card";
import { getOverview } from "@/lib/api";

export default async function OverviewPage() {
  const overview = await getOverview();

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="text-2xl font-bold text-slate-900">Structure-to-Safety</h1>
        <p className="mt-1 text-sm text-slate-500">
          Multimodal computational pharmacology of anabolic-androgenic steroids
        </p>
        <p className="mt-4 text-lg text-slate-800">{overview.research_question}</p>
      </Card>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Cohort compounds" value={overview.dataset_sizes.n_compounds} />
        <Stat label="Deduplicated FAERS reports" value={overview.dataset_sizes.n_faers_reports.toLocaleString()} />
        <Stat
          label="Compounds meeting FAERS minimum"
          value={overview.dataset_sizes.n_compounds_meeting_faers_minimum ?? "N/A"}
        />
        <Stat label="Research-defined AE categories" value={overview.dataset_sizes.n_ae_categories ?? "N/A"} />
      </div>

      <Card title="Specific aims">
        <ol className="space-y-3">
          {overview.aims.map((aim) => (
            <li key={aim.aim} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-white">
                {aim.aim}
              </span>
              <div>
                <div className="font-medium text-slate-900">{aim.title}</div>
                <div className="text-sm text-slate-600">{aim.summary}</div>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <Card title="Hypotheses and status">
        <div className="space-y-3">
          {overview.hypotheses.map((h) => (
            <div key={h.id} className="rounded border border-slate-200 p-3">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">{h.id}</span>
                <AnalysisLabelBadge label={h.label} />
              </div>
              <p className="mt-1 text-sm text-slate-700">{h.statement}</p>
              <p className="mt-1 text-sm text-slate-500 italic">{h.status}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Full pre-specified plan: <code>research/hypotheses.md</code>, <code>research/analysis_plan.md</code>.
        </p>
      </Card>

      <Card title="Major limitations" className="border-amber-200">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          {overview.major_limitations.map((limitation, i) => (
            <li key={i}>{limitation}</li>
          ))}
        </ul>
        <p className="mt-3 text-sm font-medium text-amber-800">{overview.not_a_ped_tool_notice}</p>
      </Card>
    </div>
  );
}
