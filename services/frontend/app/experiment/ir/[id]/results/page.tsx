'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ProtectedRoute } from '@/components/protected-route';
import { api, IRResultsResponse, ProgressStatus } from '@/lib/api';

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-800 rounded-xl p-5 text-center">
      <div className="text-2xl font-bold text-indigo-400">{value.toFixed(4)}</div>
      <div className="text-xs text-gray-400 mt-1 font-medium">{label}</div>
    </div>
  );
}

export default function IRResultsPage() {
  const params = useParams();
  const experimentId = params.id as string;

  const [progress, setProgress] = useState<ProgressStatus | null>(null);
  const [results, setResults] = useState<IRResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
  };

  useEffect(() => {
    async function poll() {
      try {
        const status = await api.getIRStatus(experimentId);
        setProgress(status);
        if (status.status === 'completed') {
          stopPolling();
          const data = await api.getIRResults(experimentId);
          setResults(data);
        } else if (status.status === 'failed') {
          stopPolling();
          setError(status.message);
        }
      } catch (err) {
        stopPolling();
        setError(err instanceof Error ? err.message : 'Failed to load results');
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => stopPolling();
  }, [experimentId]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
        <div className="max-w-3xl mx-auto">
          {error ? (
            <div className="p-6 bg-red-950/50 border border-red-800 rounded-xl text-red-300">
              <p className="font-semibold mb-2">Error</p>
              <p className="text-sm">{error}</p>
              <Link href="/dashboard" className="mt-4 inline-block text-sm text-indigo-400 hover:text-indigo-300">
                ← Back to Dashboard
              </Link>
            </div>
          ) : !results ? (
            <div className="flex flex-col items-center gap-6 py-24">
              <div className="inline-block w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <div className="w-full max-w-sm">
                <div className="flex justify-between text-xs text-gray-400 mb-2">
                  <span>{progress?.message ?? 'Starting experiment...'}</span>
                  <span className="font-mono">{progress?.pct ?? 0}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-1.5">
                  <div
                    className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${progress?.pct ?? 0}%` }}
                  />
                </div>
              </div>
              <p className="text-xs text-gray-600 font-mono">{experimentId}</p>
            </div>
          ) : (
            <>
              <div className="mb-8">
                <h1 className="text-2xl font-bold">IR Results</h1>
                <p className="text-sm text-gray-400 mt-1">
                  BM25 · {results.n_docs.toLocaleString()} docs · {results.n_queries.toLocaleString()} queries
                </p>
                <p className="text-xs text-gray-600 font-mono mt-1">{experimentId}</p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
                <MetricCard label="MAP" value={results.metrics.map} />
                <MetricCard label="nDCG@10" value={results.metrics.ndcg_10} />
                <MetricCard label="Recall@10" value={results.metrics.recall_10} />
                <MetricCard label="Recall@100" value={results.metrics.recall_100} />
                <MetricCard label="MRR" value={results.metrics.mrr} />
              </div>

              <div className="flex gap-3">
                <Link
                  href="/dashboard"
                  className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
                >
                  Dashboard
                </Link>
                <Link
                  href="/experiment/new-ir"
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium transition-colors"
                >
                  Run Another
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
