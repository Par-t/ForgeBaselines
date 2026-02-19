import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ForgeBaselines',
  description: 'Instant ML baselines for tabular classification',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-full`}>
        <nav className="border-b border-gray-800 px-6 py-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <Link href="/" className="font-semibold text-lg tracking-tight">
              <span className="text-indigo-400">Forge</span>
              <span className="text-white">Baselines</span>
            </Link>
            <div className="flex gap-6 text-sm text-gray-400">
              <Link href="/upload" className="hover:text-white transition-colors">
                Upload
              </Link>
            </div>
          </div>
        </nav>
        <main className="max-w-4xl mx-auto px-6 py-10">
          {children}
        </main>
      </body>
    </html>
  )
}
