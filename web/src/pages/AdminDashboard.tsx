import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdmin } from '../context/AdminContext';
import './AdminDashboard.css';

export function AdminDashboard() {
  const { stats, pending, fetchStats, fetchPending, isLoading } = useAdmin();
  const navigate = useNavigate();

  useEffect(() => {
    fetchStats();
    fetchPending();
  }, [fetchStats, fetchPending]);

  return (
    <div className="admin-dashboard">
      <header className="admin-header">
        <h1>Church Admin Overview</h1>
      </header>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <span className="stat-value">{stats?.total_members || 0}</span>
            <span className="stat-label">Total Members</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <span className="stat-value">{stats?.active_members || 0}</span>
            <span className="stat-label">Active Members</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-content">
            <span className="stat-value">{stats?.pending_members || 0}</span>
            <span className="stat-label">Pending Requests</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📝</div>
          <div className="stat-content">
            <span className="stat-value">{stats?.total_assessments || 0}</span>
            <span className="stat-label">Total Assessments</span>
          </div>
        </div>
      </div>

      {/* Pending Requests */}
      <section className="pending-section">
        <h2>Pending Membership Requests</h2>
        
        {isLoading ? (
          <p>Loading...</p>
        ) : pending.length > 0 ? (
          <div className="pending-list">
            {pending.map((request) => (
              <div key={request.membership_id} className="pending-card">
                <div className="pending-info">
                  <h3>{request.first_name} {request.last_name}</h3>
                  <p>{request.email}</p>
                  <span className="pending-date">
                    Requested {new Date(request.requested_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="pending-actions">
                  <button
                    className="btn-approve"
                    onClick={() => navigate('/admin/members')}
                  >
                    Review
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-pending">
            <p>No pending membership requests</p>
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="action-buttons">
          <button
            className="action-btn"
            onClick={() => navigate('/admin/invites')}
          >
            <span className="icon">✉️</span>
            Invite Members
          </button>
          <button
            className="action-btn"
            onClick={() => navigate('/admin/members')}
          >
            <span className="icon">👥</span>
            Manage Members
          </button>
        </div>
      </section>
    </div>
  );
}
