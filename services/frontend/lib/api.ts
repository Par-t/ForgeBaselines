const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

export interface ExperimentRunRequest {
  dataset_id: string;
  target_column: string;
  model_names: string[];
  test_size: number;
  column_config?: ColumnConfig;
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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
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
};
