'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ProtectedRoute } from '@/components/protected-route'
import { DatasetUploader } from '@/components/dataset-uploader'
import { DatasetUploadResponse } from '@/lib/api'

function UploadContent() {
  const [uploaded, setUploaded] = useState<DatasetUploadResponse | null>(null)

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-1">Upload Dataset</h1>
      <p className="text-gray-500 text-sm mb-8">Upload a CSV to use in classification or IR experiments.</p>

      {uploaded ? (
        <>
          <div className="flex items-start gap-3 bg-gray-900 border border-green-900 rounded-xl p-5 mb-6">
            <span className="text-green-400 text-base mt-0.5">✓</span>
            <div>
              <p className="font-medium text-white text-sm">{uploaded.filename}</p>
              <p className="text-gray-500 text-xs mt-0.5">
                {uploaded.rows.toLocaleString()} rows · {uploaded.cols} columns
              </p>
            </div>
          </div>

          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Start an experiment</p>
          <div className="flex flex-col gap-2 mb-6">
            <Link
              href={`/experiment/new?dataset_id=${uploaded.dataset_id}`}
              className="flex items-center justify-between px-4 py-3 bg-gray-900 border border-gray-800 hover:border-indigo-700 rounded-xl text-sm font-medium text-white transition-colors group"
            >
              <span>Classification</span>
              <span className="text-gray-600 group-hover:text-indigo-400 transition-colors">→</span>
            </Link>
            <Link
              href="/experiment/new-ir"
              className="flex items-center justify-between px-4 py-3 bg-gray-900 border border-gray-800 hover:border-indigo-700 rounded-xl text-sm font-medium text-white transition-colors group"
            >
              <span>Information Retrieval</span>
              <span className="text-gray-600 group-hover:text-indigo-400 transition-colors">→</span>
            </Link>
          </div>

          <button
            onClick={() => setUploaded(null)}
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            ← Upload another
          </button>
        </>
      ) : (
        <DatasetUploader onUploadComplete={(r: DatasetUploadResponse) => setUploaded(r)} />
      )}
    </div>
  )
}

export default function UploadPage() {
  return (
    <ProtectedRoute>
      <UploadContent />
    </ProtectedRoute>
  )
}
