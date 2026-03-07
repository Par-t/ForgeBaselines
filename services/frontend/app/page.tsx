'use client'

import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const steps = [
  {
    num: '01',
    title: 'Select Task',
    desc: 'Choose classification or information retrieval. Upload your dataset inline — no separate upload page.',
  },
  {
    num: '02',
    title: 'Configure',
    desc: 'Choose your target column and models. Get a runtime estimate before running anything.',
  },
  {
    num: '03',
    title: 'Results',
    desc: 'Leaderboard for classification, or MAP/nDCG/MRR metrics for IR — all tracked in MLflow.',
  },
]

export default function Home() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col items-center text-center py-16 gap-10">
      <div>
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          <span className="text-indigo-400">Forge</span>Baselines
        </h1>
        <p className="text-lg text-gray-400 max-w-lg mx-auto">
          Generate reproducible ML baselines for classification and information retrieval in seconds.
          No setup, no boilerplate — just results.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl">
        {steps.map(({ num, title, desc }) => (
          <div
            key={num}
            className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-left"
          >
            <div className="text-xs font-mono text-indigo-400 mb-2">{num}</div>
            <div className="font-semibold mb-1 text-white">{title}</div>
            <div className="text-sm text-gray-400 leading-relaxed">{desc}</div>
          </div>
        ))}
      </div>

      {user ? (
        <Link
          href="/select"
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-lg font-medium transition-colors text-sm"
        >
          New Experiment <span aria-hidden>→</span>
        </Link>
      ) : (
        <Link
          href="/login"
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-lg font-medium transition-colors text-sm"
        >
          Get Started <span aria-hidden>→</span>
        </Link>
      )}
    </div>
  )
}
