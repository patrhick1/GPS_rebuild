import { useState, useEffect, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { PasswordInput } from '../components/PasswordInput';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import hexBg from '../../Graphics for Dev/Images/hex-background.webp';

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
  'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
  'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
  'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
];

const inputClass =
  'w-full h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 placeholder:font-bold focus:outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20 transition-colors';

export function Register() {
  const [searchParams] = useSearchParams();
  const orgKey = searchParams.get('org') ?? '';
  const [orgName, setOrgName] = useState('');

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    country: 'United States',
    city: '',
    state: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const { register, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!orgKey) return;
    api.get(`/auth/org/${orgKey}`)
      .then((res) => setOrgName(res.data.name))
      .catch(() => {/* invalid key — silently ignore */});
  }, [orgKey]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (passwordError) setPasswordError('');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();

    if (formData.password !== formData.confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }

    try {
      const { confirmPassword, country, city, state, ...registerData } = formData;
      await register({ ...registerData, ...(orgKey ? { organization_key: orgKey } : {}) });
      navigate('/verify-email');
    } catch (err) {
      // Error is handled by auth context
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 relative">
        {/* Hexagonal background */}
        <img
          src={hexBg}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-[0.22] pointer-events-none"
        />

        <div className="relative z-10 flex flex-col items-center px-6 pt-16 pb-20">
          {/* Page heading */}
          <h1 className="font-heading font-black text-[32px] md:text-[48px] md:leading-[73px] text-brand-charcoal text-center max-w-[905px] mb-8">
            Register as Individual to Take Free Assessments
          </h1>

          {/* Form card */}
          <div className="register-card w-full max-w-[559px] bg-white border border-brand-gray-light rounded-xl shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] px-[50px] py-12">
            <h2 className="font-heading font-medium text-[24px] md:text-[32px] leading-[41px] text-brand-teal text-center mb-8">
              Enter Your Information to Create a Free Account
            </h2>

            {orgName && (
              <div className="mb-4 px-4 py-3 rounded-lg bg-brand-teal/10 border border-brand-teal text-brand-charcoal font-body text-sm">
                You are registering as a member of <strong>{orgName}</strong>.
              </div>
            )}

            {error && <div className="error-message mb-4">{error}</div>}
            {passwordError && <div className="error-message mb-4">{passwordError}</div>}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                placeholder="First Name"
                required
                className={inputClass}
              />

              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                placeholder="Last Name"
                required
                className={inputClass}
              />

              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="Email Address"
                className={inputClass}
              />

              <PasswordInput
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Password"
                required
                showStrengthMeter={true}
                email={formData.email}
                firstName={formData.first_name}
                lastName={formData.last_name}
              />

              <PasswordInput
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Confirm Password"
                required
              />

              {/* Location divider */}
              <div className="border-t border-brand-gray-light mt-2 pt-4">
                <p className="font-body font-bold text-lg text-brand-charcoal mb-3">
                  Location
                </p>

                <select
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  className={`${inputClass} w-full md:w-[219px] appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%227%22%20viewBox%3D%220%200%2012%207%22%3E%3Cpath%20d%3D%22M1%201l5%205%205-5%22%20stroke%3D%22%233f4644%22%20stroke-width%3D%222%22%20fill%3D%22none%22%2F%3E%3C%2Fsvg%3E')] bg-[length:12px_7px] bg-[right_16px_center] bg-no-repeat pr-10`}
                >
                  <option value="United States">United States</option>
                  <option value="Canada">Canada</option>
                  <option value="United Kingdom">United Kingdom</option>
                  <option value="Australia">Australia</option>
                  <option value="Other">Other</option>
                </select>

                <div className="grid grid-cols-2 gap-4 mt-4">
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    placeholder="City"
                    className={inputClass}
                  />

                  <select
                    name="state"
                    value={formData.state}
                    onChange={handleChange}
                    className={`${inputClass} appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%227%22%20viewBox%3D%220%200%2012%207%22%3E%3Cpath%20d%3D%22M1%201l5%205%205-5%22%20stroke%3D%22%233f4644%22%20stroke-width%3D%222%22%20fill%3D%22none%22%2F%3E%3C%2Fsvg%3E')] bg-[length:12px_7px] bg-[right_16px_center] bg-no-repeat pr-10`}
                  >
                    <option value="">State</option>
                    {US_STATES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="mx-auto mt-4 w-[219px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Creating...' : 'Submit'}
              </button>
            </form>
          </div>

          {/* Sign in link */}
          <p className="font-body font-bold text-lg text-brand-teal text-center mt-10">
            Already have an account?{' '}
            <Link to="/login" className="underline hover:opacity-80">
              Sign In
            </Link>
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}
