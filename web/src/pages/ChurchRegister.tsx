import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PasswordInput } from '../components/PasswordInput';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import hexBg from '../../Graphics for Dev/Images/hex-background.webp';
import churchIcon from '../../Graphics for Dev/Icons/Church Icon.svg';

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

const selectClass =
  `${inputClass} appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%227%22%20viewBox%3D%220%200%2012%207%22%3E%3Cpath%20d%3D%22M1%201l5%205%205-5%22%20stroke%3D%22%233f4644%22%20stroke-width%3D%222%22%20fill%3D%22none%22%2F%3E%3C%2Fsvg%3E')] bg-[length:12px_7px] bg-[right_16px_center] bg-no-repeat pr-10`;

export function ChurchRegister() {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirmPassword: '',
    org_name: '',
    org_city: '',
    org_state: '',
    org_country: 'United States',
  });
  const [passwordError, setPasswordError] = useState('');
  const { registerChurch, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();

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

    try {
      const { confirmPassword, ...submitData } = formData;
      await registerChurch(submitData);
      navigate('/verify-email');
    } catch {
      // Error handled by AuthContext
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 relative">
        <img
          src={hexBg}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-[0.22] pointer-events-none"
        />

        <div className="relative z-10 flex flex-col items-center px-6 pt-14 pb-20">
          {/* Heading */}
          <div className="flex flex-col items-center gap-3 mb-8">
            <img src={churchIcon} alt="" className="w-[64px] h-auto" />
            <h1 className="font-heading font-black text-[32px] md:text-[48px] md:leading-[58px] text-brand-charcoal text-center max-w-[700px]">
              Create Your Church Admin Account
            </h1>
            <p className="font-body font-semibold text-lg text-brand-gray-med text-center max-w-[500px]">
              Set up your organization and unlock the full dashboard — $10/month or $100/year.
            </p>
          </div>

          {/* Form card */}
          <div className="w-full max-w-[600px] bg-white border border-brand-gray-light rounded-xl shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] px-[50px] py-12">

            {(error || passwordError) && (
              <div className="error-message mb-6">
                {passwordError || error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">

              {/* ── Your Info ── */}
              <p className="font-body font-black text-lg text-brand-charcoal">Your Info</p>

              <div className="grid grid-cols-2 gap-4">
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
              </div>

              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email Address"
                required
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

              {/* ── Church Info ── */}
              <div className="border-t border-brand-gray-light mt-2 pt-4">
                <p className="font-body font-black text-lg text-brand-charcoal mb-3">Church Info</p>

                <div className="flex flex-col gap-4">
                  <input
                    type="text"
                    name="org_name"
                    value={formData.org_name}
                    onChange={handleChange}
                    placeholder="Church Name"
                    required
                    className={inputClass}
                  />

                  <select
                    name="org_country"
                    value={formData.org_country}
                    onChange={handleChange}
                    className={selectClass}
                  >
                    <option value="United States">United States</option>
                    <option value="Canada">Canada</option>
                    <option value="United Kingdom">United Kingdom</option>
                    <option value="Australia">Australia</option>
                    <option value="Other">Other</option>
                  </select>

                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="text"
                      name="org_city"
                      value={formData.org_city}
                      onChange={handleChange}
                      placeholder="City"
                      className={inputClass}
                    />
                    <select
                      name="org_state"
                      value={formData.org_state}
                      onChange={handleChange}
                      className={selectClass}
                    >
                      <option value="">State</option>
                      {US_STATES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="mx-auto mt-4 w-full h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Creating Account...' : 'Create Church Admin Account'}
              </button>
            </form>
          </div>

          {/* Links */}
          <div className="flex flex-col items-center gap-2 mt-8">
            <p className="font-body font-bold text-base text-brand-teal text-center">
              Already have an account?{' '}
              <Link to="/login" className="underline hover:opacity-80">
                Sign In
              </Link>
            </p>
            <p className="font-body font-bold text-base text-brand-gray-med text-center">
              Just want to take assessments?{' '}
              <Link to="/register" className="text-brand-teal underline hover:opacity-80">
                Create a free account
              </Link>
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
