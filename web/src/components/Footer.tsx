import { Link } from 'react-router-dom';
import { useTranslation } from '../hooks/useTranslation';

export function Footer() {
  const { isEs } = useTranslation();

  // Toggle text reads in the *opposite* language so users can find it whether
  // they're currently looking at English or Spanish.
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
