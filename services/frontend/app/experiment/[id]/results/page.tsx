'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, ExperimentResultsResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'

const MODEL_LABELS: Record<string, string> = {
  logistic_regression: 'Logistic Regression',
  random_forest: 'Random Forest',
  gradient_boosting: 'Gradient Boosting',
}

function pct(n: number) {
  return (n * 100).toFixed(1) + '%'
}

function ResultsPageContent() {
  const params = useParams()
  const experimentId = params.id as string

  const [results, setResults] = useState<ExperimentResultsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await api.downloadResults(experimentId)
    } catch {
      // ignore
    } finally {
      setDownloading(false)
    }
  }

  useEffect(() => {
    if (!experimentId) return

    const poll = async () => {
      try {
        const data = await api.getResults(experimentId)
        if (data.leaderboard.length > 0) {
          setResults(data)
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load results')
      }
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => clearInterval(interval)
  }, [experimentId])

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-950/50 border border-red-900 text-red-400 rounded-xl p-6 mb-5 text-sm">
          {error}
        </div>
        <Link href="/upload" className="text-indigo-400 hover:text-white transition-colors text-sm">
          ← Upload a new dataset
        </Link>
      </div>
    )
  }

  if (!results) {
    return (
      <div className="max-w-2xl mx-auto flex flex-col items-center gap-6 py-20">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-center">
          <p className="text-gray-200 font-medium">Running experiment...</p>
          <p className="text-gray-500 text-sm mt-1">Training models and logging metrics to MLflow</p>
        </div>
        <p className="text-xs font-mono text-gray-700">{experimentId}</p>
      </div>
    )
  }

  const labelClasses = Object.values(results.label_mapping)

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold mb-1">Results</h1>
          <p className="text-xs font-mono text-gray-600 truncate max-w-xs">{experimentId}</p>
        </div>
        {labelClasses.length > 0 && (
          <div className="text-right">
            <div className="text-xs text-gray-500 mb-1">Classes</div>
            <div className="text-sm text-gray-300">{labelClasses.join(', ')}</div>
          </div>
        )}
      </div>

      {/* Leaderboard table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-5 py-3.5 text-gray-500 font-medium">Model</th>
              <th className="text-right px-4 py-3.5 text-gray-500 font-medium">Accuracy</th>
              <th className="text-right px-4 py-3.5 text-gray-500 font-medium">Precision</th>
              <th className="text-right px-4 py-3.5 text-gray-500 font-medium">Recall</th>
              <th className="text-right px-4 py-3.5 text-gray-500 font-medium">F1</th>
              <th className="text-right px-5 py-3.5 text-gray-500 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {results.leaderboard.map((model, idx) => (
              <tr
                key={model.model_name}
                className={`border-b border-gray-800 last:border-0 ${
                  idx === 0 ? 'bg-indigo-950/25' : ''
                }`}
              >
                <td className="px-5 py-3.5 font-medium text-white">
                  {idx === 0 && (
                    <span className="text-amber-400 mr-2 text-xs">★</span>
                  )}
                  {MODEL_LABELS[model.model_name] ?? model.model_name}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-gray-300">
                  {pct(model.accuracy)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-gray-300">
                  {pct(model.precision)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-gray-300">
                  {pct(model.recall)}
                </td>
                <td
                  className={`px-4 py-3.5 text-right font-mono font-semibold ${
                    idx === 0 ? 'text-indigo-400' : 'text-gray-300'
                  }`}
                >
                  {pct(model.f1)}
                </td>
                <td className="px-5 py-3.5 text-right font-mono text-xs text-gray-600">
                  {model.training_time.toFixed(2)}s
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Best model callout */}
      {results.leaderboard[0] && (
        <div className="bg-gray-900 border border-indigo-900/50 rounded-xl px-5 py-4 mb-6 flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Best model</div>
            <div className="font-medium text-white">
              {MODEL_LABELS[results.leaderboard[0].model_name] ?? results.leaderboard[0].model_name}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500 mb-0.5">F1 Score</div>
            <div className="text-2xl font-bold text-indigo-400">
              {pct(results.leaderboard[0].f1)}
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Link
          href="/dashboard"
          className="flex-1 text-center bg-gray-800 hover:bg-gray-700 text-gray-300 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          Dashboard
        </Link>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex-1 text-center bg-gray-800 hover:bg-gray-700 text-gray-300 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {downloading ? 'Downloading…' : 'Download CSV'}
        </button>
        <Link
          href="/experiment/new"
          className="flex-1 text-center bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          Run Another
        </Link>
      </div>
    </div>
  )
}

export default function ResultsPage() {
  return (
    <ProtectedRoute>
      <ResultsPageContent />
    </ProtectedRoute>
  )
}
