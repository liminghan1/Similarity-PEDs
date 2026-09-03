// Server-only fetch helpers -- called from Server Components (async page.tsx / layout.tsx),
// never from the browser, so BACKEND_API_URL does not need a NEXT_PUBLIC_ prefix.
import type {
  ClusteringResults,
  CompoundDetail,
  CompoundSummary,
  DatasetManifest,
  MatrixAssociationResults,
  MatrixResponse,
  MisuseAnalysisResults,
  MultivariateResults,
  OverviewResponse,
  SafetySignalRow,
  SensitivityResults,
} from "@/types/api";

const BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function apiFetch<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`);
  } catch {
    throw new ApiError(
      0,
      `Could not reach the backend API at ${BASE_URL}${path}. Is the FastAPI server running ` +
        `(\`make api\`)?`,
    );
  }
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(response.status, `${path} -> HTTP ${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const getOverview = () => apiFetch<OverviewResponse>("/api/overview");
export const getCompounds = () => apiFetch<CompoundSummary[]>("/api/compounds");
export const getCompound = (name: string) =>
  apiFetch<CompoundDetail>(`/api/compounds/${encodeURIComponent(name)}`);

export const getMolecularPhenotype = () => apiFetch<MatrixResponse>("/api/phenotypes/molecular");
export const getReceptorPhenotype = () => apiFetch<MatrixResponse>("/api/phenotypes/receptor");
export const getSafetyPhenotype = () => apiFetch<MatrixResponse>("/api/phenotypes/safety");
export const getSafetySignalTable = () =>
  apiFetch<SafetySignalRow[]>("/api/phenotypes/safety/signal-table");

export type SimilarityRepresentation =
  | "structure"
  | "descriptor"
  | "fingerprint"
  | "receptor"
  | "combined"
  | "safety";

export const getSimilarityMatrix = (representation: SimilarityRepresentation) =>
  apiFetch<MatrixResponse>(`/api/similarity/${representation}`);

export const getMatrixAssociation = () =>
  apiFetch<MatrixAssociationResults>("/api/analysis/matrix-association");
export const getClustering = () => apiFetch<ClusteringResults>("/api/analysis/clustering");
export const getMisuseAnalysis = () => apiFetch<MisuseAnalysisResults>("/api/analysis/misuse");
export const getMultivariate = () => apiFetch<MultivariateResults>("/api/analysis/multivariate");
export const getSensitivity = () => apiFetch<SensitivityResults>("/api/analysis/sensitivity");
export const getDatasetManifest = () => apiFetch<DatasetManifest>("/api/analysis/dataset-manifest");
