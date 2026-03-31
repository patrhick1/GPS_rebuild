import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface PrivateRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'master' | 'admin_or_master';
}

export function PrivateRoute({ children, requiredRole }: PrivateRouteProps) {
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

  if (requiredRole) {
    const role = user?.role;
    if (requiredRole === 'admin_or_master' && role !== 'admin' && role !== 'master') {
      return <Navigate to="/dashboard" replace />;
    } else if (requiredRole === 'admin' && role !== 'admin') {
      return <Navigate to="/dashboard" replace />;
    } else if (requiredRole === 'master' && role !== 'master') {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
}
