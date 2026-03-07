'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/protected-route';
import { api, DatasetListItem, IRExperimentRunRequest, TextPreprocessingConfig } from '@/lib/api';
import { DatasetUploader } from '@/components/dataset-uploader';

const DEFAULT_TEXT_PREPROCESSING: TextPreprocessingConfig = {
  lowercase: true,
  remove_punctuation: true,
  remove_stopwords: false,
  stemming: false,
  lemmatization: false,
};

export default function NewIRExperimentPage() {
  const router = useRouter();

  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [corpusDatasetId, setCorpusDatasetId] = useState('');
  const [queriesDatasetId, setQueriesDatasetId] = useState('');
  // Corpus column mapping
  const [corpusDocIdCol, setCorpusDocIdCol] = useState('doc_id');
  const [textColumn, setTextColumn] = useState('text');
  // Queries column mapping
  const [queriesQueryIdCol, setQueriesQueryIdCol] = useState('');
  const [queriesQueryCol, setQueriesQueryCol] = useState('query');
  const [queriesDocIdCol, setQueriesDocIdCol] = useState('doc_id');
  const [queriesRelevanceCol, setQueriesRelevanceCol] = useState('');
  const [kValues, setKValues] = useState<number[]>([10, 100]);
  const [enableTextPreprocessing, setEnableTextPreprocessing] = useState(false);
  const [textPreprocessing, setTextPreprocessing] = useState<TextPreprocessingConfig>(DEFAULT_TEXT_PREPROCESSING);
  const [showCorpusUpload, setShowCorpusUpload] = useState(false);
  const [showQueriesUpload, setShowQueriesUpload] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets()
      .then(res => setDatasets(res.datasets))
      .catch(() => setError('Failed to load datasets'))
      .finally(() => setLoadingDatasets(false));
  }, []);

  function toggleK(k: number) {
    setKValues(prev =>
      prev.includes(k) ? prev.filter(v => v !== k) : [...prev, k].sort((a, b) => a - b)
    );
  }

  function setMorphology(mode: 'none' | 'stemming' | 'lemmatization') {
    setTextPreprocessing(prev => ({
      ...prev,
      stemming: mode === 'stemming',
      lemmatization: mode === 'lemmatization',
    }));
  }

  async function handleRun() {
    if (!corpusDatasetId || !queriesDatasetId || !textColumn) {
      setError('Select corpus dataset, queries dataset, and text column.');
      return;
    }
    if (kValues.length === 0) {
      setError('Select at least one k value.');
      return;
    }

    setLoading(true);
    setError(null);

    const req: IRExperimentRunRequest = {
      corpus_dataset_id: corpusDatasetId,
      queries_dataset_id: queriesDatasetId,
      corpus_doc_id_col: corpusDocIdCol,
      text_column: textColumn,
      queries_query_id_col: queriesQueryIdCol || undefined,
      queries_query_col: queriesQueryCol,
      queries_doc_id_col: queriesDocIdCol,
      queries_relevance_col: queriesRelevanceCol || undefined,
      k_values: kValues,
      preprocessing_config: enableTextPreprocessing
        ? { scaling: 'none', class_balancing: 'none', text: textPreprocessing }
        : undefined,
    };

    try {
      const result = await api.runIRExperiment(req);
      router.push(`/experiment/${result.experiment_id}/results`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start experiment');
      setLoading(false);
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl font-bold mb-1">New IR Experiment</h1>
          <p className="text-gray-400 text-sm mb-8">BM25 retrieval baseline — select or upload corpus and queries datasets.</p>

          {error && (
            <div className="mb-6 p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* Dataset Selection */}
          <div className="bg-gray-900 rounded-xl p-6 mb-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Datasets</h2>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Corpus dataset <span className="text-gray-600 text-xs">(doc_id, text columns)</span></label>
              {loadingDatasets ? (
                <div className="h-10 bg-gray-800 rounded animate-pulse" />
              ) : (
                <select
                  value={corpusDatasetId}
                  onChange={e => setCorpusDatasetId(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select corpus dataset...</option>
                  {datasets.map(d => (
                    <option key={d.dataset_id} value={d.dataset_id}>
                      {d.filename} ({d.rows.toLocaleString()} rows)
                    </option>
                  ))}
                </select>
              )}
              <button
                type="button"
                onClick={() => setShowCorpusUpload(v => !v)}
                className="mt-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                {showCorpusUpload ? '▲ hide upload' : '↑ or upload new'}
              </button>
              {showCorpusUpload && (
                <div className="mt-3">
                  <DatasetUploader onUploadComplete={r => { setCorpusDatasetId(r.dataset_id); setDatasets(prev => [...prev, { dataset_id: r.dataset_id, filename: r.filename, rows: r.rows, cols: r.cols, created_at: '', experiment_count: 0 }]); setShowCorpusUpload(false); }} />
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Queries dataset <span className="text-gray-600 text-xs">(query, doc_id required — query_id and relevance optional)</span></label>
              {loadingDatasets ? (
                <div className="h-10 bg-gray-800 rounded animate-pulse" />
              ) : (
                <select
                  value={queriesDatasetId}
                  onChange={e => setQueriesDatasetId(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select queries dataset...</option>
                  {datasets.map(d => (
                    <option key={d.dataset_id} value={d.dataset_id}>
                      {d.filename} ({d.rows.toLocaleString()} rows)
                    </option>
                  ))}
                </select>
              )}
              <button
                type="button"
                onClick={() => setShowQueriesUpload(v => !v)}
                className="mt-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                {showQueriesUpload ? '▲ hide upload' : '↑ or upload new'}
              </button>
              {showQueriesUpload && (
                <div className="mt-3">
                  <DatasetUploader onUploadComplete={r => { setQueriesDatasetId(r.dataset_id); setDatasets(prev => [...prev, { dataset_id: r.dataset_id, filename: r.filename, rows: r.rows, cols: r.cols, created_at: '', experiment_count: 0 }]); setShowQueriesUpload(false); }} />
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-gray-800">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Corpus column mapping</p>
              {([
                ['corpusDocIdCol', corpusDocIdCol, setCorpusDocIdCol, 'document ID'],
                ['textColumn', textColumn, setTextColumn, 'document body'],
              ] as [string, string, (v: string) => void, string][]).map(([, val, setter, role]) => (
                <div key={role} className="flex items-center gap-3 mb-2">
                  <input
                    type="text"
                    value={val}
                    onChange={e => setter(e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-gray-500 text-xs whitespace-nowrap">→ {role}</span>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-gray-800">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Queries column mapping</p>
              {([
                [queriesQueryIdCol, setQueriesQueryIdCol, 'query ID', 'auto (uses query text)'],
                [queriesQueryCol, setQueriesQueryCol, 'query text', ''],
                [queriesDocIdCol, setQueriesDocIdCol, 'relevant doc ID', ''],
                [queriesRelevanceCol, setQueriesRelevanceCol, 'relevance score', 'optional (not used by BM25)'],
              ] as [string, (v: string) => void, string, string][]).map(([val, setter, role, placeholder]) => (
                <div key={role} className="flex items-center gap-3 mb-2">
                  <input
                    type="text"
                    value={val}
                    placeholder={placeholder}
                    onChange={e => setter(e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-indigo-500 placeholder:text-gray-600"
                  />
                  <span className="text-gray-500 text-xs whitespace-nowrap">→ {role}</span>
                </div>
              ))}
            </div>
          </div>

          {/* k values */}
          <div className="bg-gray-900 rounded-xl p-6 mb-6">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Retrieval cutoffs (k)</h2>
            <div className="flex gap-3">
              {[10, 100].map(k => (
                <button
                  key={k}
                  onClick={() => toggleK(k)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    kValues.includes(k)
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}
                >
                  k={k}
                </button>
              ))}
            </div>
          </div>

          {/* Text Preprocessing */}
          <div className="bg-gray-900 rounded-xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Text preprocessing</h2>
              <button
                onClick={() => setEnableTextPreprocessing(p => !p)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  enableTextPreprocessing ? 'bg-indigo-600' : 'bg-gray-700'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enableTextPreprocessing ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {enableTextPreprocessing && (
              <div className="space-y-3">
                {([
                  ['lowercase', 'Lowercase'],
                  ['remove_punctuation', 'Remove punctuation'],
                  ['remove_stopwords', 'Remove stopwords'],
                ] as [keyof TextPreprocessingConfig, string][]).map(([key, label]) => (
                  <label key={key} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={textPreprocessing[key] as boolean}
                      onChange={e => setTextPreprocessing(prev => ({ ...prev, [key]: e.target.checked }))}
                      className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-indigo-600"
                    />
                    <span className="text-sm text-gray-300">{label}</span>
                  </label>
                ))}

                <div className="mt-4">
                  <p className="text-xs text-gray-500 mb-2">Morphological analysis</p>
                  <div className="flex gap-2">
                    {(['none', 'stemming', 'lemmatization'] as const).map(mode => (
                      <button
                        key={mode}
                        onClick={() => setMorphology(mode)}
                        className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors capitalize ${
                          (mode === 'none' && !textPreprocessing.stemming && !textPreprocessing.lemmatization) ||
                          (mode === 'stemming' && textPreprocessing.stemming) ||
                          (mode === 'lemmatization' && textPreprocessing.lemmatization)
                            ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                        }`}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <button
            onClick={handleRun}
            disabled={loading || loadingDatasets}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-semibold transition-colors"
          >
            {loading ? 'Running experiment...' : 'Run IR Experiment'}
          </button>
        </div>
      </div>
    </ProtectedRoute>
  );
}
