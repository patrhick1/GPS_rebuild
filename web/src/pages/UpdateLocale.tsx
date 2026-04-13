import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function UpdateLocale() {
  const [searchParams] = useSearchParams();
  const { user, updateLocale } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const locale = searchParams.get('locale') || 'en';

    (async () => {
      if (user) {
        await updateLocale(locale);
      } else {
        localStorage.setItem('preferred_locale', locale);
      }
      // Go back to the previous page; fallback to dashboard if no history
      if (window.history.length > 1) {
        navigate(-1);
      } else {
        navigate('/dashboard', { replace: true });
      }
    })();
  }, []);

  return null;
}
