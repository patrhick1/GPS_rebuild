import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { PasswordInput } from '../components/PasswordInput';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';

export function UpdatePassword() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);

  const [menuOpen, setMenuOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccess(true);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join(' '));
      } else {
        setError(detail || 'Failed to update password. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        {/* ── Header ── */}
        <section className="max-w-[1230px] mx-auto px-6 pt-12 pb-4">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="font-heading font-black text-3xl md:text-[48px] md:leading-[55px] text-brand-charcoal">
                Update Password
              </h1>
              <p className="font-body font-semibold italic text-lg leading-[26px] text-brand-charcoal mt-2">
                Keep your account secure
              </p>
            </div>

            {/* Gold hamburger menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-2 hover:opacity-80 transition-opacity"
                aria-label="Menu"
              >
                <img src={menuOpen ? goldXIcon : goldMenuIcon} alt="" className="w-[50px] h-auto" />
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-[307px] bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] z-50">
                  <nav className="py-1">
                    {[
                      ...(user?.role !== 'master' ? [
                        { label: 'GPS Assessments', to: '/dashboard' },
                        { label: 'MyImpact Assessments', to: '/dashboard' },
                      ] : []),
                      { label: 'Account', to: '/account' },
                    ].map((item) => (
                      <div key={item.label}>
                        <button
                          onClick={() => { setMenuOpen(false); navigate(item.to); }}
                          className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                        >
                          {item.label}
                        </button>
                        <hr className="border-brand-gray-light mx-4" />
                      </div>
                    ))}
                    {/* Active item */}
                    <button
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-teal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                      onClick={() => setMenuOpen(false)}
                    >
                      Update Password
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); logout(); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest rounded-b-xl transition-colors"
                    >
                      Logout
                    </button>
                  </nav>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── Content ── */}
        <section className="max-w-[1230px] mx-auto px-6 pb-16">
          <div className="max-w-[600px]">
            {success ? (
              /* ── Success state ── */
              <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-10 text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="font-heading font-black text-[28px] text-brand-charcoal mb-3">
                  Password Updated!
                </h2>
                <p className="font-body text-base text-brand-gray-med mb-8">
                  Your password has been changed successfully.
                </p>
                <button
                  onClick={() => navigate('/account')}
                  className="w-[219px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                >
                  Back to Account
                </button>
              </div>
            ) : (
              /* ── Form card ── */
              <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-8 md:p-10">
                <p className="font-body font-semibold italic text-base text-brand-charcoal mb-6">
                  Enter your current password, then choose a strong new one.
                </p>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl font-body text-base mb-6">
                    {error}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                  <PasswordInput
                    id="current-password"
                    name="currentPassword"
                    label="Current Password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter your current password"
                    required
                  />

                  <PasswordInput
                    id="new-password"
                    name="newPassword"
                    label="New Password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter a new password"
                    required
                    showStrengthMeter
                    email={user?.email}
                    firstName={user?.first_name}
                    lastName={user?.last_name}
                  />

                  <PasswordInput
                    id="confirm-password"
                    name="confirmPassword"
                    label="Confirm New Password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                    required
                  />

                  <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => navigate('/account')}
                      className="font-body font-bold text-base text-brand-teal hover:underline"
                    >
                      ← Back to Account
                    </button>
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-[219px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 disabled:opacity-50 transition-colors"
                    >
                      {isLoading ? 'Updating...' : 'Update Password'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
