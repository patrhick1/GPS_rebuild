import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './MasterLayout.css';

export function MasterLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="master-layout">
      {/* Sidebar */}
      <aside className="master-sidebar">
        <div className="sidebar-header">
          <h2>Master Admin</h2>
          <p>{user?.email}</p>
        </div>

        <nav className="sidebar-nav">
          <Link
            to="/master"
            className={isActive('/master') && !isActive('/master/churches') && !isActive('/master/users') && !isActive('/master/audit') ? 'active' : ''}
          >
            <span className="icon">📊</span>
            Overview
          </Link>
          <Link
            to="/master/churches"
            className={isActive('/master/churches') ? 'active' : ''}
          >
            <span className="icon">⛪</span>
            Churches
          </Link>
          <Link
            to="/master/users"
            className={isActive('/master/users') ? 'active' : ''}
          >
            <span className="icon">👤</span>
            Users
          </Link>
          <Link
            to="/master/audit"
            className={isActive('/master/audit') ? 'active' : ''}
          >
            <span className="icon">📋</span>
            Audit Log
          </Link>
          <Link
            to="/master/export"
            className={isActive('/master/export') ? 'active' : ''}
          >
            <span className="icon">📥</span>
            Export Data
          </Link>
        </nav>

        <div className="sidebar-footer">
          <button className="btn-back" onClick={() => navigate('/dashboard')}>
            ← Back to Dashboard
          </button>
          <button className="btn-logout" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="master-main">
        {children}
      </main>
    </div>
  );
}
