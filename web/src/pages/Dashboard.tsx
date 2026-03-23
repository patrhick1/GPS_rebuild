import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

export function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>GPS Assessment Platform</h1>
        <div className="user-menu">
          <span>Welcome, {user?.first_name || user?.email}</span>
          <button onClick={logout} className="btn-logout">
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        <h2>Dashboard</h2>
        <p>Welcome to your personal dashboard. What would you like to do?</p>

        <div className="dashboard-cards">
          <div className="dashboard-card featured">
            <div className="card-icon">📝</div>
            <h3>Take Assessment</h3>
            <p>Start a new GPS assessment to discover your spiritual gifts and passions.</p>
            <button 
              className="btn-primary" 
              onClick={() => navigate('/assessment')}
            >
              Start Assessment
            </button>
          </div>

          <div className="dashboard-card">
            <div className="card-icon">📊</div>
            <h3>My Results</h3>
            <p>View your assessment history and results.</p>
            <button className="btn-secondary" disabled>
              Coming Soon
            </button>
          </div>

          <div className="dashboard-card">
            <div className="card-icon">👤</div>
            <h3>Profile</h3>
            <p>Manage your account settings and information.</p>
            <button className="btn-secondary" disabled>
              Coming Soon
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
