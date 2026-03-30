import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PasswordInput } from '../components/PasswordInput';
import { Navbar } from '../components/Navbar';
import { HeroBanner } from '../components/HeroBanner';
import { UpgradeBanner } from '../components/UpgradeBanner';
import { Footer } from '../components/Footer';
import dmLogo from '../../Graphics for Dev/Logos/Disciples+Made+Logo+Horizontal 1.svg';
import coupleImg from '../../Graphics for Dev/Images/Couple Rounded Corners.webp';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      const loggedInUser = await login(email, password);
      if (loggedInUser.role === 'admin') {
        navigate('/admin');
      } else if (loggedInUser.role === 'master') {
        navigate('/master');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      // Error is handled by auth context
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <HeroBanner />

      <main className="flex-1 bg-white">
        <section className="max-w-6xl mx-auto px-6 py-16 lg:py-20 flex flex-col md:flex-row gap-8 lg:gap-10 items-start">

          {/* Login Form Card */}
          <div className="bg-brand-gray-lightest rounded-lg shadow-sm p-10 lg:p-12 w-full md:w-[420px] shrink-0">
            <img src={dmLogo} alt="Disciples Made" className="h-10 mx-auto mb-4" />

            <h2 className="font-heading font-bold text-2xl lg:text-3xl text-brand-teal text-center mb-6">
              Login
            </h2>

            {error && (
              <div className="error-message">{error}</div>
            )}

            <form onSubmit={handleSubmit}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="Email Address"
                className="w-full h-11 px-4 mb-3 border border-brand-gray-light rounded bg-white font-body text-sm text-brand-charcoal placeholder:text-brand-gray-med focus:outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20 transition-colors"
              />

              <PasswordInput
                id="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
              />

              <button
                type="submit"
                disabled={isLoading}
                className="block mx-auto mt-4 mb-3 bg-brand-teal text-white font-body font-semibold text-sm rounded-full px-10 py-2.5 hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Logging in...' : 'Login'}
              </button>
            </form>

            <Link
              to="/forgot-password"
              className="block text-center font-body text-sm text-brand-teal underline mb-4"
            >
              Forgot Password
            </Link>

            <p className="text-center font-body text-sm mb-2">
              <span className="text-brand-charcoal">New Here? </span>
              <Link to="/register" className="text-brand-teal hover:underline">
                Register Now
              </Link>
            </p>

            <Link
              to="/upgrade"
              className="block text-center font-body text-sm text-brand-teal hover:underline mt-1"
            >
              Upgrade to a Church Administrator account
            </Link>
          </div>

          {/* Couple photo */}
          <div className="hidden md:block flex-1 self-stretch min-h-[400px]">
            <img
              src={coupleImg}
              alt=""
              className="w-full h-full object-cover rounded-xl"
            />
          </div>
        </section>
      </main>

      <UpgradeBanner />
      <Footer />
    </div>
  );
}
