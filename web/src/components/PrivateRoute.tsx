import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface PrivateRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'master' | 'admin_or_master';
  allowUnverified?: boolean;
}

export function PrivateRoute({ children, requiredRole, allowUnverified }: PrivateRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect unverified users to the verification page
  if (!allowUnverified && user?.email_verified !== 'Y') {
    return <Navigate to="/verify-email" replace />;
  }

  const role = user?.role;
  const home = role === 'master' ? '/master' : '/dashboard';

  // Master admins should not access user-facing pages (dashboard, assessments, etc.)
  if (!requiredRole && role === 'master') {
    return <Navigate to="/master" replace />;
  }

  if (requiredRole) {
    if (requiredRole === 'admin_or_master' && role !== 'admin' && role !== 'master') {
      return <Navigate to={home} replace />;
    } else if (requiredRole === 'admin' && role !== 'admin') {
      return <Navigate to={home} replace />;
    } else if (requiredRole === 'master' && role !== 'master') {
      return <Navigate to={home} replace />;
    }
  }

  return <>{children}</>;
}
