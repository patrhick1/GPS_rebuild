import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './AdminLayout.css';

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="admin-layout">
      {/* Sidebar */}
      <aside className="admin-sidebar">
        <div className="sidebar-header">
          <h2>Admin Dashboard</h2>
          <p>{user?.email}</p>
        </div>

        <nav className="sidebar-nav">
          <Link
            to="/admin"
            className={isActive('/admin') && !isActive('/admin/members') && !isActive('/admin/invites') ? 'active' : ''}
          >
            <span className="icon">📊</span>
            Overview
          </Link>
          <Link
            to="/admin/members"
            className={isActive('/admin/members') ? 'active' : ''}
          >
            <span className="icon">👥</span>
            Members
          </Link>
          <Link
            to="/admin/invites"
            className={isActive('/admin/invites') ? 'active' : ''}
          >
            <span className="icon">✉️</span>
            Invites
          </Link>
          <Link
            to="/admin/settings"
            className={isActive('/admin/settings') ? 'active' : ''}
          >
            <span className="icon">⚙️</span>
            Settings
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
      <main className="admin-main">
        {children}
      </main>
    </div>
  );
}
