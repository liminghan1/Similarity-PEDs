// Mirrors backend/app/schemas/*.py and the artifact JSON shapes written by analysis/*.py.
// Kept as plain interfaces (not generated) since the backend is small and stable; if the API
// surface grows, consider generating these from the FastAPI OpenAPI schema instead.

export interface CompoundSummary {
  canonical_name: string;
  pubchem_cid: number | null;
  chembl_id: string | null;
  molecular_formula: string | null;
  molecular_weight: number | null;
  drug_class: string | null;
  n_aliases: number;
  n_formulations: number;
  n_bioactivities: number;
  n_faers_reports: number;
}

export interface AliasOut {
  alias: string;
  alias_type: string;
  formulation_id: number | null;
  source: string | null;
  verified: boolean;
}

export interface FormulationOut {
  id: number;
  formulation_name: string;
  ester_name: string | null;
  route: string | null;
  source: string | null;
}

export interface BioactivityOut {
  target_name: string;
  target_gene_symbol: string | null;
  measurement_type: string;
  relation: string;
  standardized_value_nm: number | null;
  p_activity: number | null;
  source: string;
  assay_confidence_score: number | null;
}

export interface CompoundDetail {
  canonical_name: string;
  pubchem_cid: number | null;
  chembl_id: string | null;
  smiles: string | null;
  isomeric_smiles: string | null;
  inchikey: string | null;
  molecular_formula: string | null;
  molecular_weight: number | null;
  drug_class: string | null;
  source: string | null;
  retrieved_at: string | null;
  aliases: AliasOut[];
  formulations: FormulationOut[];
  bioactivities: BioactivityOut[];
  n_faers_reports: number;
}

export interface MatrixResponse {
  labels: string[];
  columns: string[];
  values: (number | null)[][];
}

export interface SafetySignalRow {
  canonical_name: string;
  category: string;
  a: number;
  b: number;
  c: number;
  d: number;
  total_compound_reports: number;
  ror: number;
  log_ror: number;
  se_log_ror: number;
  ci_low: number;
  ci_high: number;
  continuity_correction_applied: boolean;
  sparse_cell: boolean;
  compound_meets_minimum: boolean;
}

export interface MantelResult {
  label: string;
  description: string;
  computable: boolean;
  reason?: string;
  statistic_spearman_rho?: number;
  p_value_one_sided?: number;
  p_value_two_sided?: number;
  n_permutations?: number;
  n_objects?: number;
  objects?: string[];
  bootstrap_ci_low?: number;
  bootstrap_ci_high?: number;
  n_compounds_eligible?: number;
}

export interface MatrixAssociationResults {
  n_permutations: number;
  seed: number;
  results: MantelResult[];
}

export interface ClusteringResults {
  label: string;
  n_compounds: number;
  compounds: string[];
  structure_clustering: {
    method: string;
    k: number;
    cluster_labels: Record<string, number>;
    cophenetic_correlation: number;
  };
  safety_clustering: {
    method: string;
    k: number;
    cluster_labels: Record<string, number>;
    cophenetic_correlation: number;
  };
  receptor_clustering: string;
  cluster_agreement: {
    adjusted_rand_index: number;
    normalized_mutual_information: number;
  };
  pca_kmeans_exploratory: {
    note: string;
    cluster_labels: Record<string, number>;
  };
}

export interface SeriousnessOutcome {
  outcome: string;
  misuse_n: number;
  therapeutic_n: number;
  misuse_count: number;
  misuse_proportion: number;
  therapeutic_count: number;
  therapeutic_proportion: number;
  odds_ratio: number;
  ci_low: number;
  ci_high: number;
  fisher_p_value: number;
}

export interface MisuseAnalysisResults {
  label: string;
  group_sizes: Record<string, number>;
  strata_meet_minimum_20_reports: boolean;
  seriousness_outcomes: SeriousnessOutcome[];
  ae_category_comparison: AeCategoryComparisonRow[];
  demographics: {
    age: {
      misuse_n_with_age: number;
      therapeutic_n_with_age: number;
      misuse_median_age: number | null;
      therapeutic_median_age: number | null;
      mannwhitney_p_value: number | null;
      note?: string;
    };
    sex: {
      table: Record<string, Record<string, number>>;
      fisher_p_value?: number;
    };
  };
}

export interface AeCategoryComparisonRow {
  category: string;
  misuse_count: number;
  misuse_n: number;
  therapeutic_count: number;
  therapeutic_n: number;
  odds_ratio: number;
  ci_low: number;
  ci_high: number;
  fisher_p_value: number;
}

export interface MultivariateCategoryResult {
  category: string;
  n?: number;
  observed_loocv_r2?: number;
  p_value?: number;
  n_permutations?: number;
  skipped_reason?: string;
}

export interface MultivariateResults {
  label: string;
  predictor_features: string[];
  model: string;
  results: MultivariateCategoryResult[];
}

export type SensitivityResults = Record<string, MantelResult>;

export interface DatasetManifest {
  generated_at: string;
  git_commit: string;
  min_compound_reports: number;
  min_cell_reports: number;
  primary_confidence_threshold: number;
  compounds: string[];
  ae_categories: string[];
  receptor_matrix_primary_shape: [number, number];
  receptor_matrix_primary_nonnull_cells: number;
  safety_matrix_shape: [number, number];
  safety_matrix_nonnull_cells: number;
  compounds_meeting_minimum_reports: string[];
}

export interface AimSummary {
  aim: number;
  title: string;
  summary: string;
}

export interface HypothesisSummary {
  id: string;
  label: string;
  statement: string;
  status: string;
}

export interface OverviewResponse {
  research_question: string;
  aims: AimSummary[];
  hypotheses: HypothesisSummary[];
  dataset_sizes: {
    n_compounds: number;
    n_faers_reports: number;
    n_compounds_meeting_faers_minimum: number | null;
    n_ae_categories: number | null;
  };
  major_limitations: string[];
  not_a_ped_tool_notice: string;
}
