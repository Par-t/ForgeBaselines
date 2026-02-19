import Link from 'next/link'

const steps = [
  {
    num: '01',
    title: 'Upload',
    desc: 'Drop any CSV. We profile column types, detect missing values, and flag ID columns automatically.',
  },
  {
    num: '02',
    title: 'Configure',
    desc: 'Choose your target column and models. Get a runtime estimate before running anything.',
  },
  {
    num: '03',
    title: 'Results',
    desc: 'Logistic regression, random forest, and gradient boosting — ranked by F1 score.',
  },
]

export default function Home() {
  return (
    <div className="flex flex-col items-center text-center py-16 gap-10">
      <div>
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          <span className="text-indigo-400">Forge</span>Baselines
        </h1>
        <p className="text-lg text-gray-400 max-w-lg mx-auto">
          Generate reproducible ML baselines for tabular classification in seconds.
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

      <Link
        href="/upload"
        className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-lg font-medium transition-colors text-sm"
      >
        Upload Dataset <span aria-hidden>→</span>
      </Link>
    </div>
  )
}
