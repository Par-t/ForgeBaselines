'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { DatasetUploadResponse } from '@/lib/api'
import { DatasetUploader } from '@/components/dataset-uploader'
import { ProtectedRoute } from '@/components/protected-route'

function UploadPageContent() {
  const [result, setResult] = useState<DatasetUploadResponse | null>(null)
  const router = useRouter()

  if (result) {
    return (
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">Dataset Uploaded</h1>

        <div className="bg-gray-900 border border-emerald-900 rounded-xl p-6 mb-5">
          <div className="flex items-center gap-2 mb-5">
            <span className="text-emerald-400 text-xl">✓</span>
            <span className="font-medium text-white">{result.filename}</span>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Rows</div>
              <div className="text-2xl font-semibold text-white">
                {result.rows.toLocaleString()}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Columns</div>
              <div className="text-2xl font-semibold text-white">{result.cols}</div>
            </div>
          </div>

          <div className="text-xs text-gray-600 font-mono truncate">
            {result.dataset_id}
          </div>
        </div>

        <button
          onClick={() => router.push(`/experiment/new?dataset_id=${result.dataset_id}`)}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-lg font-medium transition-colors text-sm mb-3"
        >
          Configure Experiment →
        </button>

        <button
          onClick={() => setResult(null)}
          className="w-full text-gray-500 hover:text-gray-300 text-sm transition-colors py-1"
        >
          Upload another file
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-1">Upload Dataset</h1>
      <p className="text-gray-500 text-sm mb-8">CSV files only</p>
      <DatasetUploader onUploadComplete={setResult} />
    </div>
  )
}

export default function UploadPage() {
  return (
    <ProtectedRoute>
      <UploadPageContent />
    </ProtectedRoute>
  )
}
