import { useState, useEffect } from 'react';

interface PasswordStrength {
  score: number;
  strength_label: string;
  color: string;
  is_valid: boolean;
  errors: string[];
  requirements: string;
}

interface PasswordInputProps {
  id: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  required?: boolean;
  minLength?: number;
  label?: string;
  showStrengthMeter?: boolean;
  email?: string;
  firstName?: string;
  lastName?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function PasswordInput({
  id,
  name,
  value,
  onChange,
  placeholder = 'Enter password',
  required = false,
  minLength = 8,
  label = 'Password',
  showStrengthMeter = false,
  email = '',
  firstName = '',
  lastName = '',
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [strength, setStrength] = useState<PasswordStrength | null>(null);
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  // Debounced strength check
  useEffect(() => {
    if (!showStrengthMeter || !value) {
      setStrength(null);
      return;
    }

    // Clear previous timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // Set new timer for debounced API call
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          password: value,
          email,
          first_name: firstName,
          last_name: lastName,
        });

        const response = await fetch(`${API_URL}/auth/password-strength`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params,
        });

        if (response.ok) {
          const data = await response.json();
          setStrength(data);
        }
      } catch (err) {
        // Silently fail - strength meter is optional UX enhancement
        console.error('Failed to check password strength:', err);
      }
    }, 300);

    setDebounceTimer(timer);

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [value, showStrengthMeter, email, firstName, lastName]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  }, [debounceTimer]);

  // Get color class for strength bar
  const getStrengthColor = (score: number): string => {
    if (score <= 20) return 'bg-red-500';
    if (score <= 40) return 'bg-orange-500';
    if (score <= 60) return 'bg-yellow-500';
    if (score <= 80) return 'bg-blue-500';
    return 'bg-green-500';
  };

  // Get text color class
  const getStrengthTextColor = (score: number): string => {
    if (score <= 20) return 'text-red-600';
    if (score <= 40) return 'text-orange-600';
    if (score <= 60) return 'text-yellow-600';
    if (score <= 80) return 'text-blue-600';
    return 'text-green-600';
  };

  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      <div className="password-input-wrapper">
        <input
          type={showPassword ? 'text' : 'password'}
          id={id}
          name={name}
          value={value}
          onChange={onChange}
          required={required}
          placeholder={placeholder}
          minLength={minLength}
          className="password-input"
        />
        <button
          type="button"
          className="password-toggle-btn"
          onClick={() => setShowPassword(!showPassword)}
          tabIndex={-1}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          title={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            // Eye-off icon (password is visible, clicking will hide it)
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            // Eye icon (password is hidden, clicking will show it)
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>

      {/* Password Strength Meter */}
      {showStrengthMeter && value && strength && (
        <div className="password-strength-meter">
          {/* Strength Bar */}
          <div className="strength-bar-container">
            <div
              className={`strength-bar ${getStrengthColor(strength.score)}`}
              style={{ width: `${strength.score}%` }}
            />
          </div>
          
          {/* Strength Label */}
          <span className={`strength-label ${getStrengthTextColor(strength.score)}`}>
            {strength.strength_label}
          </span>

          {/* Error Messages */}
          {!strength.is_valid && strength.errors.length > 0 && (
            <ul className="password-requirements">
              {strength.errors.map((error, index) => (
                <li key={index} className="requirement-item requirement-failed">
                  <span className="requirement-icon">✗</span>
                  {error}
                </li>
              ))}
            </ul>
          )}

          {/* Show all requirements when password is empty or weak */}
          {strength.score < 60 && (
            <details className="password-requirements-help">
              <summary>Password requirements</summary>
              <div className="requirements-text">
                {strength.requirements.split('\n').map((line, index) => (
                  <p key={index}>{line}</p>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
