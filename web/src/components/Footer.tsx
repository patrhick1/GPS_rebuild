import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function Footer() {
  const { locale } = useAuth();
  const isEs = locale === 'es';

  return (
    <footer className="w-full bg-brand-charcoal h-14 flex items-center justify-center">
      <Link
        to={isEs ? '/update-locale?locale=en' : '/update-locale?locale=es'}
        className="font-body text-sm text-white underline hover:text-brand-teal-light transition-colors"
      >
        {isEs ? 'In English?' : '¿En español?'}
      </Link>
    </footer>
  );
}
