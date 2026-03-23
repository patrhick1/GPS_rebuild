import { useAuth } from '../context/AuthContext';

export function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>GPS Assessment Platform</h1>
        <div className="user-menu">
          <span>Welcome, {user?.first_name || user?.email}</span>
          <button onClick={logout} className="btn-secondary">
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        <h2>Dashboard</h2>
        <p>This is your personal dashboard. More features coming soon!</p>

        <div className="dashboard-cards">
          <div className="card">
            <h3>My Assessments</h3>
            <p>View your assessment history and results.</p>
            <button className="btn-primary" disabled>
              Coming Soon
            </button>
          </div>

          <div className="card">
            <h3>Take Assessment</h3>
            <p>Start a new GPS assessment.</p>
            <button className="btn-primary" disabled>
              Coming Soon
            </button>
          </div>

          <div className="card">
            <h3>Profile</h3>
            <p>Manage your account settings.</p>
            <button className="btn-primary" disabled>
              Coming Soon
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
