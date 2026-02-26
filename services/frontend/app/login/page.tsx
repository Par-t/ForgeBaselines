'use client';

import { useAuth } from '@/lib/auth-context';
import { isSignInWithEmailLink } from 'firebase/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function LoginPage() {
  const { user, sendMagicLink, completeMagicLink } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [linkSent, setLinkSent] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      router.replace('/');
    }
  }, [user, router]);

  // Handle magic link completion
  useEffect(() => {
    const completeSignIn = async () => {
      if (!isSignInWithEmailLink(undefined as any, window.location.href)) {
        return;
      }

      setCompleting(true);

      // Try to get email from localStorage (same device)
      let emailForSignIn = window.localStorage.getItem('emailForSignIn');

      if (!emailForSignIn) {
        // Email not in localStorage, show form asking for email
        setCompleting(false);
        setEmail('');
        setLinkSent(false);
        return;
      }

      try {
        await completeMagicLink(emailForSignIn, window.location.href);
        // Success will be handled by useAuth hook which redirects via user state change
      } catch (err) {
        setError('Failed to complete sign in. Please try again.');
        setCompleting(false);
      }
    };

    completeSignIn();
  }, [completeMagicLink]);

  const handleSendMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await sendMagicLink(email);
      setLinkSent(true);
    } catch (err) {
      setError('Failed to send magic link. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (completing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400">Completing sign in...</p>
        </div>
      </div>
    );
  }

  if (linkSent) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md w-full">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            <h1 className="text-2xl font-bold mb-2">Check your email</h1>
            <p className="text-gray-400 mb-6">We sent a magic link to:</p>
            <p className="font-semibold text-indigo-400 mb-8 break-words">{email}</p>
            <p className="text-sm text-gray-500 mb-6">
              Click the link in the email to sign in. You'll be redirected here automatically.
            </p>
            <button
              onClick={() => {
                setLinkSent(false);
                setEmail('');
                setError('');
              }}
              className="text-indigo-400 hover:text-indigo-300 text-sm"
            >
              Try a different email
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
          <h1 className="text-2xl font-bold mb-2">Sign in</h1>
          <p className="text-gray-400 text-sm mb-8">
            Enter your email to receive a magic sign-in link
          </p>

          {error && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-700 rounded text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSendMagicLink} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email}
              className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
            >
              {loading ? 'Sending...' : 'Send magic link'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
