import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMaster } from '../context/MasterContext';
import './MasterDashboard.css';

export function MasterDashboard() {
  const { stats, fetchStats, isLoading } = useMaster();
  const navigate = useNavigate();

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="master-dashboard">
      <header className="page-header">
        <h1>System Overview</h1>
      </header>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <>
          {/* Main Stats */}
          <div className="stats-grid main-stats">
            <div className="stat-card large">
              <div className="stat-icon">👤</div>
              <div className="stat-content">
                <span className="stat-value">{stats?.total_users || 0}</span>
                <span className="stat-label">Total Users</span>
              </div>
            </div>

            <div className="stat-card large">
              <div className="stat-icon">⛪</div>
              <div className="stat-content">
                <span className="stat-value">{stats?.total_churches || 0}</span>
                <span className="stat-label">Total Churches</span>
              </div>
            </div>

            <div className="stat-card large">
              <div className="stat-icon">📝</div>
              <div className="stat-content">
                <span className="stat-value">{stats?.total_assessments || 0}</span>
                <span className="stat-label">Total Assessments</span>
              </div>
            </div>

            <div className="stat-card large">
              <div className="stat-icon">✅</div>
              <div className="stat-content">
                <span className="stat-value">{stats?.active_churches || 0}</span>
                <span className="stat-label">Active Churches</span>
              </div>
            </div>
          </div>

          {/* Recent Activity Stats */}
          <div className="recent-stats">
            <h2>Recent Activity</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <h3>Last 30 Days</h3>
                <div className="stat-row">
                  <span>New Users:</span>
                  <strong>{stats?.recent_stats?.["30_days"]?.new_users || 0}</strong>
                </div>
                <div className="stat-row">
                  <span>Assessments:</span>
                  <strong>{stats?.recent_stats?.["30_days"]?.assessments || 0}</strong>
                </div>
              </div>

              <div className="stat-card">
                <h3>Last 90 Days</h3>
                <div className="stat-row">
                  <span>New Users:</span>
                  <strong>{stats?.recent_stats?.["90_days"]?.new_users || 0}</strong>
                </div>
                <div className="stat-row">
                  <span>Assessments:</span>
                  <strong>{stats?.recent_stats?.["90_days"]?.assessments || 0}</strong>
                </div>
              </div>

              <div className="stat-card">
                <h3>Last 365 Days</h3>
                <div className="stat-row">
                  <span>New Users:</span>
                  <strong>{stats?.recent_stats?.["365_days"]?.new_users || 0}</strong>
                </div>
                <div className="stat-row">
                  <span>Assessments:</span>
                  <strong>{stats?.recent_stats?.["365_days"]?.assessments || 0}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h2>Quick Actions</h2>
            <div className="action-buttons">
              <button
                className="action-btn"
                onClick={() => navigate('/master/churches')}
              >
                <span className="icon">⛪</span>
                Manage Churches
              </button>
              <button
                className="action-btn"
                onClick={() => navigate('/master/users')}
              >
                <span className="icon">👤</span>
                Manage Users
              </button>
              <button
                className="action-btn"
                onClick={() => navigate('/master/audit')}
              >
                <span className="icon">📋</span>
                View Audit Log
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
