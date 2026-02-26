'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { api, SuggestColumnsResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'

const MODELS = [
  { id: 'logistic_regression', label: 'Logistic Regression' },
  { id: 'random_forest', label: 'Random Forest' },
  { id: 'gradient_boosting', label: 'Gradient Boosting' },
]

function Spinner({ size = 5 }: { size?: number }) {
  return (
    <div
      className={`w-${size} h-${size} border-2 border-indigo-400 border-t-transparent rounded-full animate-spin`}
    />
  )
}

function NewExperimentForm() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const datasetId = searchParams.get('dataset_id')

  const [columns, setColumns] = useState<string[]>([])
  const [targetColumn, setTargetColumn] = useState('')
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'logistic_regression',
    'random_forest',
    'gradient_boosting',
  ])
  const [testSize, setTestSize] = useState(0.2)
  const [suggestions, setSuggestions] = useState<SuggestColumnsResponse | null>(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [runtimeEstimate, setRuntimeEstimate] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [profileLoading, setProfileLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load column names from profile
  useEffect(() => {
    if (!datasetId) return
    api
      .getProfile(datasetId)
      .then(r => setColumns(r.profile.column_names))
      .catch(() => setError('Failed to load dataset profile.'))
      .finally(() => setProfileLoading(false))
  }, [datasetId])

  // Fetch column suggestions when target changes
  useEffect(() => {
    if (!datasetId || !targetColumn) {
      setSuggestions(null)
      return
    }
    api
      .suggestColumns(datasetId, targetColumn)
      .then(setSuggestions)
      .catch(() => {})
  }, [datasetId, targetColumn])

  // Runtime estimate (debounced 400 ms)
  useEffect(() => {
    if (!datasetId || !targetColumn || selectedModels.length === 0) {
      setRuntimeEstimate(null)
      return
    }
    const t = setTimeout(() => {
      api
        .estimateRuntime(datasetId, selectedModels)
        .then(r => setRuntimeEstimate(r.overall_estimate))
        .catch(() => {})
    }, 400)
    return () => clearTimeout(t)
  }, [datasetId, targetColumn, selectedModels])

  const toggleModel = (id: string) =>
    setSelectedModels(prev =>
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    )

  const handleRun = async () => {
    if (!datasetId || !targetColumn || selectedModels.length === 0) return
    setIsRunning(true)
    setError(null)
    try {
      const result = await api.runExperiment({
        dataset_id: datasetId,
        target_column: targetColumn,
        model_names: selectedModels,
        test_size: testSize,
        // Pass suggestions back with source="user" so V2 agent flow is honoured
        column_config: suggestions?.column_config
          ? { ...suggestions.column_config, source: 'user' }
          : undefined,
      })
      router.push(`/experiment/${result.experiment_id}/results`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Experiment failed')
      setIsRunning(false)
    }
  }

  if (!datasetId) {
    return (
      <p className="text-gray-400">
        No dataset selected.{' '}
        <a href="/upload" className="text-indigo-400 underline">
          Upload one first
        </a>
        .
      </p>
    )
  }

  if (profileLoading) {
    return (
      <div className="flex items-center gap-3 text-gray-400">
        <Spinner />
        Loading dataset...
      </div>
    )
  }

  const flaggedCount = suggestions?.column_config.ignore_columns.length ?? 0
  const canRun = !!targetColumn && selectedModels.length > 0 && !isRunning

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-1">Configure Experiment</h1>
      <p className="text-gray-500 text-sm mb-8 font-mono truncate">{datasetId}</p>

      {/* Target column */}
      <section className="mb-7">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Target Column
        </label>
        <select
          value={targetColumn}
          onChange={e => setTargetColumn(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 text-white"
        >
          <option value="">Select a column...</option>
          {columns.map(col => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </select>
      </section>

      {/* Column suggestions */}
      {suggestions && flaggedCount > 0 && (
        <section className="mb-7">
          <button
            onClick={() => setShowSuggestions(v => !v)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors w-full text-left"
          >
            <span className="text-amber-400">⚠</span>
            <span>
              {flaggedCount} column{flaggedCount !== 1 ? 's' : ''} will be
              auto-excluded before training
            </span>
            <span className="ml-auto text-xs text-gray-600">
              {showSuggestions ? '▲' : '▼'}
            </span>
          </button>
          {showSuggestions && (
            <div className="mt-2 bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-2">
              {suggestions.column_config.ignore_columns.map(col => (
                <div key={col} className="text-sm">
                  <span className="font-mono text-gray-200">{col}</span>
                  <span className="text-gray-500 ml-2 text-xs">
                    {suggestions.column_notes[col] || 'auto-excluded'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Models */}
      <section className="mb-7">
        <label className="block text-sm font-medium text-gray-300 mb-3">Models</label>
        <div className="space-y-2">
          {MODELS.map(({ id, label }) => (
            <label key={id} className="flex items-center gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={selectedModels.includes(id)}
                onChange={() => toggleModel(id)}
                className="w-4 h-4 accent-indigo-500"
              />
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                {label}
              </span>
            </label>
          ))}
        </div>
      </section>

      {/* Test split */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-300">Test Split</label>
          <span className="text-sm font-mono text-indigo-400">
            {Math.round(testSize * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0.1"
          max="0.5"
          step="0.05"
          value={testSize}
          onChange={e => setTestSize(parseFloat(e.target.value))}
          className="w-full accent-indigo-500"
        />
        <div className="flex justify-between text-xs text-gray-700 mt-1">
          <span>10%</span>
          <span>50%</span>
        </div>
      </section>

      {/* Runtime estimate */}
      {runtimeEstimate && (
        <div className="flex items-center gap-2 text-sm mb-6">
          <span className="text-gray-500">Estimated runtime:</span>
          <span className="bg-indigo-950 text-indigo-300 border border-indigo-900 px-2 py-0.5 rounded font-mono text-xs">
            {runtimeEstimate}
          </span>
        </div>
      )}

      {error && (
        <div className="mb-5 bg-red-950/50 border border-red-900 text-red-400 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      <button
        onClick={handleRun}
        disabled={!canRun}
        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors text-sm"
      >
        {isRunning ? (
          <>
            <Spinner size={4} />
            Running experiment...
          </>
        ) : (
          'Run Experiment →'
        )}
      </button>
    </div>
  )
}

export default function NewExperimentPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="flex items-center gap-3 text-gray-400">
            <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            Loading...
          </div>
        }
      >
        <NewExperimentForm />
      </Suspense>
    </ProtectedRoute>
  )
}
