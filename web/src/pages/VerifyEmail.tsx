import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export function VerifyEmail() {
  const { user, resendVerification, logout } = useAuth();
  const navigate = useNavigate();
  const [cooldown, setCooldown] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // If already verified, redirect to appropriate page
  useEffect(() => {
    if (user?.email_verified === 'Y') {
      if (user.role === 'admin') {
        navigate('/admin');
      } else if (user.role === 'master') {
        navigate('/master');
      } else {
        navigate('/dashboard');
      }
    }
  }, [user, navigate]);

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleResend = async () => {
    setError('');
    setMessage('');
    try {
      await resendVerification();
      setMessage('Verification email sent! Check your inbox.');
      setCooldown(60);
    } catch (err: any) {
      if (err.response?.status === 429) {
        setError('Too many requests. Please try again later.');
      } else {
        setError(err.response?.data?.detail || 'Failed to resend. Please try again.');
      }
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center bg-white px-6">
        <div className="max-w-md w-full text-center py-16">
          {/* Email icon */}
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-brand-teal/10 flex items-center justify-center">
            <svg className="w-10 h-10 text-brand-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
            </svg>
          </div>

          <h1 className="font-heading font-bold text-2xl text-brand-teal mb-3">
            Check Your Email
          </h1>

          <p className="text-brand-charcoal/70 mb-2">
            We sent a verification link to
          </p>
          <p className="font-bold text-brand-charcoal mb-6">
            {user?.email}
          </p>

          <p className="text-brand-charcoal/60 text-sm mb-8">
            Click the link in the email to verify your account. The link expires in 24 hours.
          </p>

          {message && (
            <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-700 text-sm">
              {message}
            </div>
          )}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleResend}
            disabled={cooldown > 0}
            className="w-full h-[50px] bg-brand-teal text-white font-bold rounded-xl hover:bg-brand-teal-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed mb-4"
          >
            {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Verification Email'}
          </button>

          <button
            onClick={handleLogout}
            className="text-brand-charcoal/60 hover:text-brand-charcoal text-sm underline"
          >
            Sign out
          </button>
        </div>
      </main>
      <Footer />
    </div>
  );
}
