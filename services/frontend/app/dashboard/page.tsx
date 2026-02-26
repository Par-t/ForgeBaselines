'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, DatasetListItem, ExperimentListItem } from '@/lib/api';
import { ProtectedRoute } from '@/components/protected-route';

function formatDate(iso: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function ConfirmModal({
  message,
  onConfirm,
  onCancel,
}: {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-sm w-full mx-4">
        <p className="text-gray-200 mb-5">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function DashboardContent() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ type: 'dataset' | 'experiment'; id: string } | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [ds, exps] = await Promise.all([api.listDatasets(), api.listExperiments()]);
      setDatasets(ds.datasets);
      setExperiments(exps.experiments);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async () => {
    if (!confirm) return;
    setDeleting(confirm.id);
    setConfirm(null);
    try {
      if (confirm.type === 'dataset') {
        await api.deleteDataset(confirm.id);
      } else {
        await api.deleteExperiment(confirm.id);
      }
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  // Build dataset_id → filename map for the experiments table
  const datasetNames: Record<string, string> = {};
  for (const d of datasets) datasetNames[d.dataset_id] = d.filename;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950/50 border border-red-900 text-red-400 rounded-xl p-5 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {confirm && (
        <ConfirmModal
          message={`Delete this ${confirm.type}? This cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Datasets</h2>
          <Link
            href="/upload"
            className="text-sm px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
          >
            + Upload
          </Link>
        </div>

        {datasets.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500 text-sm">
            No datasets yet.{' '}
            <Link href="/upload" className="text-indigo-400 hover:text-white transition-colors">
              Upload your first dataset →
            </Link>
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-5 py-3 text-gray-500 font-medium">File</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Rows</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Cols</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Runs</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Uploaded</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.dataset_id} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40 transition-colors">
                    <td className="px-5 py-3 font-medium text-white">
                      <Link
                        href={`/experiment/new?dataset_id=${d.dataset_id}`}
                        className="hover:text-indigo-400 transition-colors"
                      >
                        {d.filename}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">{d.rows.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">{d.cols}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">{d.experiment_count}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{formatDate(d.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setConfirm({ type: 'dataset', id: d.dataset_id })}
                        disabled={deleting === d.dataset_id}
                        className="text-xs text-red-600 hover:text-red-400 transition-colors disabled:opacity-40"
                      >
                        {deleting === d.dataset_id ? '…' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Experiments</h2>

        {experiments.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500 text-sm">
            No experiments yet. Upload a dataset and run one.
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-5 py-3 text-gray-500 font-medium">Experiment</th>
                  <th className="text-left px-4 py-3 text-gray-500 font-medium">Dataset</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Date</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {experiments.map((e) => (
                  <tr key={e.experiment_id} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-indigo-400">
                      <Link
                        href={`/experiment/${e.experiment_id}/results`}
                        className="hover:text-indigo-300 transition-colors"
                      >
                        {e.experiment_id.slice(0, 8)}…
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {datasetNames[e.dataset_id] ? (
                        <Link
                          href={`/experiment/new?dataset_id=${e.dataset_id}`}
                          className="hover:text-indigo-400 transition-colors"
                        >
                          {datasetNames[e.dataset_id]}
                        </Link>
                      ) : (
                        <span className="text-gray-600 font-mono text-xs">{e.dataset_id.slice(0, 8)}…</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500">{formatDate(e.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setConfirm({ type: 'experiment', id: e.experiment_id })}
                        disabled={deleting === e.experiment_id}
                        className="text-xs text-red-600 hover:text-red-400 transition-colors disabled:opacity-40"
                      >
                        {deleting === e.experiment_id ? '…' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">Dashboard</h1>
        <DashboardContent />
      </div>
    </ProtectedRoute>
  );
}
