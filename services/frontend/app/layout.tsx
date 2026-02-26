import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'
import { Navbar } from '@/components/navbar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ForgeBaselines',
  description: 'Instant ML baselines for tabular classification',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-full`}>
        <AuthProvider>
          <Navbar />
          <main className="max-w-4xl mx-auto px-6 py-10">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  )
}
