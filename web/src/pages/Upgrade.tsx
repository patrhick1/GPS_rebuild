import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import adminHeroImg from '../../Graphics for Dev/Images/Admin Accounts Hero.webp';
import churchIcon from '../../Graphics for Dev/Icons/Church Icon.svg';
import computerMockups from '../../Graphics for Dev/Images/Computer_Mockups.webp';
import tealArrowIcon from '../../Graphics for Dev/Icons/Dark Teal Arrow Circle Icon.svg';

export function Upgrade() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleUpgrade = () => {
    if (user?.is_primary_admin) {
      // Already an admin — go straight to billing
      navigate('/admin/billing');
    } else if (user) {
      // Logged in but not yet an admin — upgrade existing account
      navigate('/upgrade/church');
    } else {
      // Not logged in — new signup flow
      navigate('/register/church');
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ── Hero Section ── */}
      <div className="relative w-full h-[200px] md:h-[170px] lg:h-[362px] overflow-hidden">
        <img
          src={adminHeroImg}
          alt=""
          className="absolute inset-0 w-full h-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-[rgba(63,70,68,0.84)] mix-blend-multiply" />
        <div className="absolute inset-0 flex items-center justify-center">
          <h1 className="font-heading font-black text-4xl md:text-[60px] md:leading-[65px] lg:text-[64px] lg:leading-[73px] text-white text-center">
            Admin Accounts
          </h1>
        </div>
      </div>

      <main className="flex-1 bg-white">
        <div className="max-w-6xl mx-auto px-6 pt-6">
          <Link
            to={user ? '/dashboard' : '/login'}
            className="inline-flex items-center gap-1 font-body font-bold text-sm text-brand-teal hover:text-brand-teal/80 transition-colors"
          >
            <span className="text-base">←</span> Back{user ? ' to Dashboard' : ''}
          </Link>
        </div>
        {/* ── Track & Manage Band ── */}
        <section className="w-full bg-[rgba(227,227,227,0.24)]">
          <div className="max-w-6xl mx-auto px-6 py-14 lg:py-20 flex flex-col lg:flex-row items-center gap-8 lg:gap-12">
            {/* Church icon */}
            <img src={churchIcon} alt="" className="w-[100px] md:w-[116px] lg:w-[149px] h-auto shrink-0" />

            {/* Text */}
            <div className="flex-1 text-center lg:text-left">
              <h2 className="font-heading font-black text-3xl md:text-[40px] md:leading-[41px] lg:text-[48px] lg:leading-[55px] text-brand-charcoal">
                Track and Manage Your Church's Assessment Results
              </h2>
              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mt-4">
                Wonder if your church already has an Admin account?{' '}
                <a
                  href="mailto:support@giftpassionstory.com"
                  className="text-brand-teal underline hover:text-brand-teal/80 transition-colors"
                >
                  Email us to ask.
                </a>
              </p>
            </div>

            {/* CTA button */}
            <button
              onClick={handleUpgrade}
              className="shrink-0 w-[281px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
            >
              Upgrade to Church Admin
            </button>
          </div>
        </section>

        {/* ── Upgrade Details Section ── */}
        <section className="max-w-6xl mx-auto px-6 py-16 lg:py-24">
          <div className="flex flex-col lg:flex-row items-start gap-12 lg:gap-16">
            {/* Left: Text content */}
            <div className="flex-1">
              <h2 className="font-heading font-black text-3xl md:text-[40px] md:leading-[41px] lg:text-[48px] lg:leading-[55px] text-brand-charcoal mb-6">
                Upgrade to a Church Administrator Account
              </h2>

              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mb-6">
                Unlock the Full Potential of Personal Calling in Your Organization With:
              </p>

              {/* Bullet: Exclusive Dashboard Access */}
              <div className="flex items-start gap-3 mb-5">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">Exclusive Dashboard Access</span>
                  <span className="font-bold"> – View and export individual assessment results.</span>
                </p>
              </div>

              {/* Bullet: Unique Invitation Link */}
              <div className="flex items-start gap-3 mb-8">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">A Unique Invitation Link for Your Members</span>
                  <span className="font-bold"> – Share on your website or in church communications to invite members to complete the assessments.</span>
                </p>
              </div>

              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mb-8">
                Cost: $10 per month or $100 paid annually
              </p>

              <button
                onClick={handleUpgrade}
                className="w-[281px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
              >
                Upgrade to Church Admin
              </button>
            </div>

            {/* Right: Computer mockups image */}
            <div className="md:w-[601px] md:mx-auto lg:mx-0 shrink-0">
              <img
                src={computerMockups}
                alt="GPS Admin Dashboard on multiple devices"
                className="w-full h-auto"
              />
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
