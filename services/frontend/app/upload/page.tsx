'use client'

import { useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { api, DatasetUploadResponse } from '@/lib/api'

function Spinner({ size = 5 }: { size?: number }) {
  return (
    <div
      className={`w-${size} h-${size} border-2 border-indigo-400 border-t-transparent rounded-full animate-spin`}
    />
  )
}

export default function UploadPage() {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [result, setResult] = useState<DatasetUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  const uploadFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setError('Only CSV files are supported.')
      return
    }
    setIsUploading(true)
    setError(null)
    try {
      const data = await api.uploadDataset(file)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) uploadFile(file)
  }, [])

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  // Success state
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
          onClick={() => { setResult(null); setError(null) }}
          className="w-full text-gray-500 hover:text-gray-300 text-sm transition-colors py-1"
        >
          Upload another file
        </button>
      </div>
    )
  }

  // Upload state
  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-1">Upload Dataset</h1>
      <p className="text-gray-500 text-sm mb-8">CSV files only · max 50 MB</p>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={() => setIsDragging(false)}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-20 text-center transition-colors
          ${isUploading ? 'border-gray-700 cursor-default' : 'cursor-pointer'}
          ${isDragging
            ? 'border-indigo-500 bg-indigo-950/20'
            : 'border-gray-700 hover:border-gray-500'}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f) }}
          className="hidden"
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-3">
            <Spinner size={8} />
            <p className="text-gray-400 text-sm">Uploading...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="text-5xl text-gray-700">↑</div>
            <p className="text-gray-300 font-medium">Drop a CSV file here</p>
            <p className="text-gray-600 text-sm">or click to browse</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 bg-red-950/50 border border-red-900 text-red-400 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}
