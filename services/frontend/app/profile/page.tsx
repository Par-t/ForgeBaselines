'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api';
import { ProtectedRoute } from '@/components/protected-route';

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric',
  });
}

function ProfileContent() {
  const { user } = useAuth();
  const [datasetCount, setDatasetCount] = useState<number | null>(null);
  const [experimentCount, setExperimentCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [ds, exps] = await Promise.all([api.listDatasets(), api.listExperiments()]);
        setDatasetCount(ds.datasets.length);
        setExperimentCount(exps.experiments.length);
      } catch {
        setDatasetCount(0);
        setExperimentCount(0);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const creationTime = user?.metadata?.creationTime;

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-4 mb-5">
          <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-lg select-none">
            {user?.email?.[0]?.toUpperCase() ?? '?'}
          </div>
          <div>
            <div className="font-medium text-white">{user?.email}</div>
            <div className="text-xs text-gray-500 mt-0.5">Member since {formatDate(creationTime)}</div>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-5 grid grid-cols-2 gap-4">
          <div className="bg-gray-800/50 rounded-lg px-4 py-3 text-center">
            <div className="text-2xl font-bold text-white">
              {loading ? <span className="inline-block w-8 h-6 bg-gray-700 rounded animate-pulse" /> : datasetCount}
            </div>
            <div className="text-xs text-gray-500 mt-1">Datasets uploaded</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg px-4 py-3 text-center">
            <div className="text-2xl font-bold text-white">
              {loading ? <span className="inline-block w-8 h-6 bg-gray-700 rounded animate-pulse" /> : experimentCount}
            </div>
            <div className="text-xs text-gray-500 mt-1">Experiments run</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">Profile</h1>
        <ProfileContent />
      </div>
    </ProtectedRoute>
  );
}
