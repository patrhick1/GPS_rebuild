import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../context/AuthContext';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/password-reset-request', { email });
      setIsSubmitted(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset request');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Check Your Email</h1>
          <p>
            If an account exists for <strong>{email}</strong>, you will receive
            a password reset link shortly.
          </p>
          <Link to="/login" className="btn-primary">
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Reset Password</h1>
        <p>Enter your email address and we'll send you a link to reset your password.</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="Enter your email"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary"
          >
            {isLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/login">Back to Login</Link>
        </div>
      </div>
    </div>
  );
}
