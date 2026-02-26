'use client';

import { useAuth } from '@/lib/auth-context';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export function Navbar() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  return (
    <nav className="border-b border-gray-800 px-6 py-4">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <Link href="/" className="font-semibold text-lg tracking-tight">
          <span className="text-indigo-400">Forge</span>
          <span className="text-white">Baselines</span>
        </Link>

        <div className="flex gap-6 items-center text-sm">
          {loading ? (
            <div className="h-4 w-20 bg-gray-700 rounded animate-pulse" />
          ) : user ? (
            <>
              <Link href="/upload" className="text-gray-400 hover:text-white transition-colors">
                Upload
              </Link>
              <div className="flex items-center gap-4">
                <span className="text-gray-500 text-xs">{user.email}</span>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                >
                  Logout
                </button>
              </div>
            </>
          ) : (
            <Link
              href="/login"
              className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded transition-colors"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
