import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export function VerifyEmailCallback() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setErrorMessage('No verification token provided.');
      return;
    }

    api
      .get(`/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(() => setStatus('success'))
      .catch((err) => {
        setStatus('error');
        setErrorMessage(
          err.response?.data?.detail || 'Verification failed. The link may have expired.'
        );
      });
  }, [token]);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center bg-white px-6">
        <div className="max-w-md w-full text-center py-16">
          {status === 'loading' && (
            <>
              <div className="w-12 h-12 mx-auto mb-6 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
              <p className="text-brand-charcoal/70">Verifying your email...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="font-heading font-bold text-2xl text-brand-teal mb-3">
                Email Verified!
              </h1>
              <p className="text-brand-charcoal/70 mb-8">
                Your email has been verified successfully. You can now access your account.
              </p>
              <Link
                to="/login"
                className="inline-block w-full h-[50px] leading-[50px] bg-brand-teal text-white font-bold rounded-xl hover:bg-brand-teal-dark transition-colors"
              >
                Continue to Login
              </Link>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-10 h-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="font-heading font-bold text-2xl text-red-600 mb-3">
                Verification Failed
              </h1>
              <p className="text-brand-charcoal/70 mb-8">{errorMessage}</p>
              <Link
                to="/login"
                className="inline-block w-full h-[50px] leading-[50px] bg-brand-teal text-white font-bold rounded-xl hover:bg-brand-teal-dark transition-colors"
              >
                Go to Login
              </Link>
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
