import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import adminHeroImg from '../../Graphics for Dev/Images/Admin Accounts Hero.webp';
import churchIcon from '../../Graphics for Dev/Icons/Church Icon.svg';
import computerMockups from '../../Graphics for Dev/Images/Computer_Mockups.webp';
import tealArrowIcon from '../../Graphics for Dev/Icons/Dark Teal Arrow Circle Icon.svg';

export function Upgrade() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const handleUpgrade = () => {
    const promo = new URLSearchParams(location.search).get('promo')?.trim();
    if (promo) {
      sessionStorage.setItem('toolkitPromotionCode', promo.slice(0, 64));
    }

    if (user?.is_primary_admin) {
      // Already an admin — go straight to billing
      navigate({ pathname: '/admin/billing', search: location.search });
    } else if (user) {
      // Logged in but not yet an admin — upgrade existing account
      navigate({ pathname: '/upgrade/church', search: location.search });
    } else {
      // Not logged in — new signup flow
      navigate({ pathname: '/register/church', search: location.search });
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
        <div className="absolute inset-0 flex items-center justify-center px-6">
          <h1 className="font-heading font-black text-3xl md:text-[48px] md:leading-[52px] lg:text-[56px] lg:leading-[64px] text-white text-center max-w-4xl">
            Help Your Church Grow in Character and Calling
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

        {/* ── Intro / pitch band ── */}
        <section className="w-full bg-[rgba(227,227,227,0.24)]">
          <div className="max-w-6xl mx-auto px-6 py-14 lg:py-20 flex flex-col lg:flex-row items-center gap-8 lg:gap-12">
            <img src={churchIcon} alt="" className="w-[100px] md:w-[116px] lg:w-[149px] h-auto shrink-0" />

            <div className="flex-1 text-center lg:text-left">
              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal">
                You may already be using the Disciples Made Impact Dashboard to take assessments and view your own results. But what if you want to help your whole church take the next step?
              </p>
              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mt-4">
                Do you want to see your members&apos; assessment results so your team can support clearer next steps? Do you want practical resources for making personal calling development more normal in your church?
              </p>
              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mt-4">
                The Calling Development Toolkit helps your church move from personal assessment results to church-wide calling development.
              </p>
            </div>

            <button
              onClick={handleUpgrade}
              className="shrink-0 w-[281px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
            >
              Get Toolkit Access
            </button>
          </div>
        </section>

        {/* ── Features / Unlock access band ── */}
        <section className="max-w-6xl mx-auto px-6 py-16 lg:py-24">
          <div className="flex flex-col lg:flex-row items-start gap-12 lg:gap-16">
            <div className="flex-1">
              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mb-6">
                Your purchase includes access to the Calling Development Toolkit in the Fully Alive App, plus a Church Administrator Account for the Disciples Made Impact Dashboard.
              </p>

              <h2 className="font-heading font-black text-3xl md:text-[40px] md:leading-[41px] lg:text-[48px] lg:leading-[55px] text-brand-charcoal mb-6">
                Unlock access to:
              </h2>

              {/* Bullet: Calling Development Toolkit Resources */}
              <div className="flex items-start gap-3 mb-5">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">Calling Development Toolkit Resources</span>
                  <span className="font-bold"> — Access campaign guides, small group tools, message outlines, manuscripts, and director/coach resources to help your church lead Develop Your Calling: Find Your Place with clarity.</span>
                </p>
              </div>

              {/* Bullet: Church Administrator Dashboard */}
              <div className="flex items-start gap-3 mb-5">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">Church Administrator Dashboard</span>
                  <span className="font-bold"> — View and export individual GPS and MyImpact assessment results so your team can provide more personal and meaningful follow-up.</span>
                </p>
              </div>

              {/* Bullet: Unique Assessment Invitation Link */}
              <div className="flex items-start gap-3 mb-5">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">Unique Assessment Invitation Link</span>
                  <span className="font-bold"> — Share a church-specific link so members can complete assessments and connect their results to your church dashboard.</span>
                </p>
              </div>

              {/* Bullet: GPS and MyImpact Assessments */}
              <div className="flex items-start gap-3 mb-8">
                <img src={tealArrowIcon} alt="" className="w-[22px] h-[22px] mt-1 shrink-0" />
                <p className="font-body text-lg leading-[26px] text-brand-charcoal">
                  <span className="font-black">GPS and MyImpact Assessments</span>
                  <span className="font-bold"> — Help your members discover their gifts, passions, story, character growth, calling clarity, and next steps.</span>
                </p>
              </div>

              <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mb-8">
                Cost: $10 per month or $99 paid annually
              </p>

              <button
                onClick={handleUpgrade}
                className="w-[281px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
              >
                Get Toolkit Access
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
