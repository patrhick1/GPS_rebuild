import { useState, type FormEvent } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../context/AuthContext';
import { PasswordInput } from '../components/PasswordInput';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  // Guard: no token in URL
  if (!token) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Invalid Reset Link</h1>
          <p>This password reset link is missing or invalid.</p>
          <Link to="/forgot-password" className="btn-primary">
            Request a New Link
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/auth/password-reset', {
        token,
        new_password: newPassword,
      });
      setIsSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Failed to reset password. The link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Password Reset</h1>
          <p>Your password has been reset successfully. Redirecting to login&hellip;</p>
          <Link to="/login" className="btn-primary">
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Choose a New Password</h1>
        <p>Enter a new password for your account.</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <PasswordInput
            id="new-password"
            name="new_password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            label="New Password"
            placeholder="Enter new password"
            required
            showStrengthMeter
          />

          <div className="form-group">
            <label htmlFor="confirm-password">Confirm Password</label>
            <input
              type="password"
              id="confirm-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder="Confirm new password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary"
          >
            {isLoading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/login">Back to Login</Link>
        </div>
      </div>
    </div>
  );
}
