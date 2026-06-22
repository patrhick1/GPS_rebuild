import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { NotificationBell } from './NotificationBell';
import { HelpLink } from './HelpLink';
import dmLogo from '../../Graphics for Dev/Logos/Disciples+Made+Logo+Horizontal 1.svg';
import gpsLogo from '../../Graphics for Dev/Logos/gps-logo 1.svg';
import myImpactLogo from '../../Graphics for Dev/Logos/MyImpact Logo.svg';
import impactLogo from '../../Graphics for Dev/Logos/Impact Dashboard Logo.png';

export function Navbar() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const homePath = user?.role === 'master' ? '/master' : '/dashboard';

  return (
    <nav className="w-full bg-white border-b-[3px] border-brand-teal">
      <div className="flex items-center justify-between px-8 lg:px-16 h-[72px]">
        {/* Left: Disciples Made logo + Impact Dashboard wordmark.
           Wordmark added per Sherri's 2026-06-22 brand placement mockup —
           hidden on mobile to keep the right-side cluster (Help + Bell)
           from wrapping. */}
        <button onClick={() => navigate(homePath)} className="cursor-pointer flex items-center gap-4">
          <img src={dmLogo} alt="Disciples Made" className="h-10" />
          <img src={impactLogo} alt="Impact Dashboard" className="hidden md:block h-8" />
        </button>

        {/* Right: GPS + MyImpact logos + Help + notification bell (desktop) */}
        <div className="hidden md:flex items-center gap-6">
          <img src={gpsLogo} alt="GPS" className="h-[35px]" />
          <img src={myImpactLogo} alt="MyImpact" className="h-[35px]" />
          <HelpLink />
          {user && user.email_verified === 'Y' && <NotificationBell />}
        </div>

        {/* Mobile: Help + notification bell only. The hamburger menu was
           removed per Chelsie 2026-06-17 — it duplicated the page-level
           hamburger on Dashboard/AdminDashboard. Locale toggle lives in
           the page hamburger and the Footer. */}
        <div className="md:hidden flex items-center gap-3">
          <HelpLink className="font-body font-bold text-sm text-brand-charcoal hover:text-brand-teal transition-colors" />
          {user && user.email_verified === 'Y' && <NotificationBell />}
        </div>
      </div>
    </nav>
  );
}
