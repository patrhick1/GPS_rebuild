import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import dmLogo from '../../Graphics for Dev/Logos/Disciples+Made+Logo+Horizontal 1.svg';
import gpsLogo from '../../Graphics for Dev/Logos/gps-logo 1.svg';
import myImpactLogo from '../../Graphics for Dev/Logos/MyImpact Logo.svg';
import hamburgerIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  const homePath = user?.role === 'master' ? '/master' : '/dashboard';

  return (
    <nav className="w-full bg-white border-b-[3px] border-brand-teal">
      <div className="flex items-center justify-between px-8 lg:px-16 h-[72px]">
        {/* Left: Disciples Made logo */}
        <button onClick={() => navigate(homePath)} className="cursor-pointer">
          <img src={dmLogo} alt="Disciples Made" className="h-10" />
        </button>

        {/* Right: GPS + MyImpact logos (desktop) */}
        <div className="hidden md:flex items-center gap-6">
          <img src={gpsLogo} alt="GPS" className="h-[35px]" />
          <img src={myImpactLogo} alt="MyImpact" className="h-[35px]" />
        </div>

        {/* Hamburger (mobile) */}
        <button
          className="md:hidden p-2"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <img src={hamburgerIcon} alt="Menu" className="h-6 w-6" />
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden flex flex-col items-center gap-4 py-4 border-t border-brand-gray-light bg-white">
          <img src={gpsLogo} alt="GPS" className="h-8" />
          <img src={myImpactLogo} alt="MyImpact" className="h-8" />
        </div>
      )}
    </nav>
  );
}
