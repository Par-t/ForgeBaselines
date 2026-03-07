const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Token getter — set by AuthContext after mount
let tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(fn: () => Promise<string | null>) {
  tokenGetter = fn;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  filename: string;
  rows: number;
  cols: number;
  user_id: string;
}

export interface DatasetProfile {
  n_rows: number;
  n_cols: number;
  numeric_cols: number;
  categorical_cols: number;
  column_names: string[];
  column_types: Record<string, string>;
  missing_values: number;
  missing_by_column: Record<string, number>;
  cardinality: Record<string, number>;
  memory_mb: number;
}

export interface DatasetProfileResponse {
  dataset_id: string;
  user_id: string;
  profile: DatasetProfile;
}

export interface ColumnConfig {
  ignore_columns: string[];
  feature_columns: string[];
  source: 'auto' | 'user';
}

export interface SuggestColumnsResponse {
  dataset_id: string;
  column_config: ColumnConfig;
  column_notes: Record<string, string>;
}

export interface RuntimeEstimateResponse {
  dataset_id: string;
  overall_estimate: string;
  per_model: Record<string, string>;
  complexity_factors: Record<string, unknown>;
}

export interface TextPreprocessingConfig {
  lowercase: boolean;
  remove_punctuation: boolean;
  remove_stopwords: boolean;
  stemming: boolean;
  lemmatization: boolean;
}

export interface PreprocessingConfig {
  scaling: 'standard' | 'minmax' | 'none';
  class_balancing: 'none' | 'class_weight' | 'smote';
  text?: TextPreprocessingConfig;
}

export interface ExperimentRunRequest {
  dataset_id: string;
  target_column: string;
  model_names: string[];
  test_size: number;
  column_config?: ColumnConfig;
  preprocessing_config?: PreprocessingConfig;
}

export interface ExperimentRunResponse {
  experiment_id: string;
  dataset_id: string;
  status: string;
  estimated_runtime: string;
  models: string[];
  column_config_used: ColumnConfig | null;
}

export interface ModelResult {
  model_name: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  training_time: number;
}

export interface ExperimentResultsResponse {
  experiment_id: string;
  user_id: string;
  status: string;
  label_mapping: Record<string, string>;
  leaderboard: ModelResult[];
}

export interface DatasetListItem {
  dataset_id: string;
  filename: string;
  rows: number;
  cols: number;
  created_at: string;
  experiment_count: number;
}

export interface DatasetListResponse {
  datasets: DatasetListItem[];
}

export interface ExperimentListItem {
  experiment_id: string;
  dataset_id: string;
  status: string;
  run_count: number;
  created_at: string;
}

export interface ExperimentListResponse {
  experiments: ExperimentListItem[];
}

export interface DeleteResponse {
  message: string;
}

export interface IRExperimentRunRequest {
  corpus_dataset_id: string;
  queries_dataset_id: string;
  corpus_doc_id_col?: string;
  text_column: string;
  queries_query_id_col?: string;
  queries_query_col?: string;
  queries_doc_id_col?: string;
  queries_relevance_col?: string;
  k_values: number[];
  preprocessing_config?: PreprocessingConfig;
}

export interface IRMetrics {
  map: number;
  ndcg_10: number;
  recall_10: number;
  recall_100: number;
  mrr: number;
}

export interface IRExperimentRunResponse {
  experiment_id: string;
  corpus_dataset_id: string;
  queries_dataset_id: string;
  status: string;
}

export interface IRResultsResponse {
  experiment_id: string;
  user_id: string;
  status: string;
  metrics: IRMetrics;
  n_docs: number;
  n_queries: number;
}

export interface IRExperimentListItem {
  experiment_id: string;
  corpus_dataset_id: string;
  queries_dataset_id: string;
  status: string;
  created_at: string;
}

export interface IRExperimentListResponse {
  experiments: IRExperimentListItem[];
}

export interface ProgressStatus {
  stage: string;
  pct: number;
  status: string;
  message: string;
}

export interface UnifiedExperimentListItem {
  experiment_id: string;
  task_type: 'classification' | 'ir';
  status: string;
  created_at: string;
  dataset_id?: string;
  corpus_dataset_id?: string;
  queries_dataset_id?: string;
}

export interface UnifiedExperimentListResponse {
  experiments: UnifiedExperimentListItem[];
}

export type UnifiedResultsResponse =
  | {
      experiment_id: string;
      task_type: 'classification';
      label_mapping: Record<string, string>;
      leaderboard: ModelResult[];
    }
  | {
      experiment_id: string;
      task_type: 'ir';
      metrics: IRMetrics;
      n_docs: number;
      n_queries: number;
    };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);

  // Attach auth token if available
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : res.statusText;
    } catch {
      detail = res.statusText;
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  uploadDataset: (file: File): Promise<DatasetUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    return request('/datasets/upload', { method: 'POST', body: form });
  },

  getProfile: (datasetId: string): Promise<DatasetProfileResponse> =>
    request(`/datasets/${datasetId}/profile`),

  suggestColumns: (datasetId: string, targetColumn: string): Promise<SuggestColumnsResponse> =>
    request(`/datasets/${datasetId}/suggest-columns?target_column=${encodeURIComponent(targetColumn)}`),

  estimateRuntime: (datasetId: string, modelNames: string[]): Promise<RuntimeEstimateResponse> =>
    request('/experiments/estimate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, model_names: modelNames }),
    }),

  runExperiment: (req: ExperimentRunRequest): Promise<ExperimentRunResponse> =>
    request('/experiments/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),

  getResults: (experimentId: string): Promise<ExperimentResultsResponse> =>
    request(`/experiments/${experimentId}/results`),

  listDatasets: (): Promise<DatasetListResponse> =>
    request('/datasets'),

  listExperiments: (): Promise<ExperimentListResponse> =>
    request('/experiments'),

  deleteDataset: (datasetId: string): Promise<DeleteResponse> =>
    request(`/datasets/${datasetId}`, { method: 'DELETE' }),

  deleteExperiment: (experimentId: string): Promise<DeleteResponse> =>
    request(`/experiments/${experimentId}`, { method: 'DELETE' }),

  downloadResults: async (experimentId: string): Promise<void> => {
    const headers = new Headers();
    if (tokenGetter) {
      const token = await tokenGetter();
      if (token) headers.set('Authorization', `Bearer ${token}`);
    }
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/results/download`, { headers });
    if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${experimentId.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  },

  runIRExperiment: (req: IRExperimentRunRequest): Promise<IRExperimentRunResponse> =>
    request('/experiments/ir/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),

  getIRResults: (experimentId: string): Promise<IRResultsResponse> =>
    request(`/experiments/ir/${experimentId}/results`),

  listIRExperiments: (): Promise<IRExperimentListResponse> =>
    request('/experiments/ir'),

  getExperimentStatus: (experimentId: string): Promise<ProgressStatus> =>
    request(`/experiments/${experimentId}/status`),

  getIRStatus: (experimentId: string): Promise<ProgressStatus> =>
    request(`/experiments/ir/${experimentId}/status`),

  listAllExperiments: (): Promise<UnifiedExperimentListResponse> =>
    request('/experiments/all'),

  getUnifiedResults: (experimentId: string): Promise<UnifiedResultsResponse> =>
    request(`/experiments/${experimentId}/results`),
};
