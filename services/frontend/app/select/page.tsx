'use client'

import Link from 'next/link'
import { ProtectedRoute } from '@/components/protected-route'

function SelectContent() {
  return (
    <div className="max-w-2xl mx-auto py-8">
      <h1 className="text-2xl font-bold mb-2">New Experiment</h1>
      <p className="text-gray-500 text-sm mb-10">Choose a task type to get started</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href="/experiment/new"
          className="group bg-gray-900 border border-gray-800 hover:border-indigo-700 rounded-xl p-6 transition-colors"
        >
          <div className="text-2xl mb-3">📊</div>
          <div className="font-semibold text-white mb-1 group-hover:text-indigo-300 transition-colors">
            Classification
          </div>
          <p className="text-sm text-gray-500 leading-relaxed">
            Train and compare ML classifiers on tabular or text data. Get a leaderboard ranked by F1.
          </p>
        </Link>

        <Link
          href="/experiment/new-ir"
          className="group bg-gray-900 border border-gray-800 hover:border-indigo-700 rounded-xl p-6 transition-colors"
        >
          <div className="text-2xl mb-3">🔍</div>
          <div className="font-semibold text-white mb-1 group-hover:text-indigo-300 transition-colors">
            Information Retrieval
          </div>
          <p className="text-sm text-gray-500 leading-relaxed">
            Evaluate BM25 retrieval on your corpus and queries. Get MAP, nDCG, MRR, and Recall metrics.
          </p>
        </Link>
      </div>
    </div>
  )
}

export default function SelectPage() {
  return (
    <ProtectedRoute>
      <SelectContent />
    </ProtectedRoute>
  )
}
