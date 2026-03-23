import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { AssessmentHistory } from '../components/AssessmentHistory';
import { ChurchLinking } from '../components/ChurchLinking';
import './Dashboard.css';

export function Dashboard() {
  const { user, logout } = useAuth();
  const { summary, fetchSummary, isLoading } = useDashboard();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'church'>('overview');

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const handleExport = async () => {
    const { exportCSV } = useDashboard();
    await exportCSV();
  };

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
        {/* Navigation Tabs */}
        <div className="dashboard-tabs">
          <button
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History ({summary?.stats.total_assessments || 0})
          </button>
          <button
            className={`tab ${activeTab === 'church' ? 'active' : ''}`}
            onClick={() => setActiveTab('church')}
          >
            Church
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="tab-content">
            {/* Quick Actions */}
            <div className="quick-actions">
              <button
                className="btn-primary btn-large"
                onClick={() => navigate('/assessment')}
              >
                <span className="icon">📝</span>
                Take New Assessment
              </button>
              
              {summary && summary.stats.total_assessments > 0 && (
                <button
                  className="btn-secondary"
                  onClick={handleExport}
                >
                  <span className="icon">📊</span>
                  Export CSV
                </button>
              )}
            </div>

            {/* Summary Cards */}
            <div className="dashboard-cards">
              {/* Latest Assessment Card */}
              <div className="dashboard-card featured">
                <h3>Latest Assessment</h3>
                {isLoading ? (
                  <p>Loading...</p>
                ) : summary?.latest_assessment ? (
                  <div className="latest-assessment">
                    <div className="assessment-date">
                      {new Date(summary.latest_assessment.completed_at).toLocaleDateString()}
                    </div>
                    
                    {summary.latest_assessment.top_gifts && (
                      <div className="top-gifts">
                        <h4>Top Gifts</h4>
                        <div className="gift-tags">
                          {summary.latest_assessment.top_gifts.map((gift, idx) => (
                            <span key={idx} className="gift-tag">
                              {gift.name} ({gift.score})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {summary.latest_assessment.top_passions && (
                      <div className="top-passions">
                        <h4>Influencing Styles</h4>
                        <div className="passion-tags">
                          {summary.latest_assessment.top_passions.map((passion, idx) => (
                            <span key={idx} className="passion-tag">
                              {passion.name} ({passion.score})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <button
                      className="btn-view"
                      onClick={() => navigate(`/assessment-results? id=${summary.latest_assessment!.id}`)}
                    >
                      View Results
                    </button>
                  </div>
                ) : (
                  <div className="no-assessment">
                    <p>You haven't taken any assessments yet.</p>
                    <button
                      className="btn-primary"
                      onClick={() => navigate('/assessment')}
                    >
                      Start Your First Assessment
                    </button>
                  </div>
                )}
              </div>

              {/* Stats Card */}
              <div className="dashboard-card">
                <h3>Your Stats</h3>
                <div className="stats-grid">
                  <div className="stat-item">
                    <span className="stat-value">{summary?.stats.total_assessments || 0}</span>
                    <span className="stat-label">Total Assessments</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">
                      {summary?.organization ? summary.organization.name : 'Independent'}
                    </span>
                    <span className="stat-label">Organization</span>
                  </div>
                </div>
              </div>

              {/* Profile Card */}
              <div className="dashboard-card">
                <h3>Profile</h3>
                <div className="profile-info">
                  <p><strong>Name:</strong> {summary?.user.first_name} {summary?.user.last_name}</p>
                  <p><strong>Email:</strong> {summary?.user.email}</p>
                  <p><strong>Status:</strong> Active</p>
                </div>
                <button className="btn-secondary" disabled>
                  Edit Profile (Coming Soon)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="tab-content">
            <AssessmentHistory />
          </div>
        )}

        {/* Church Tab */}
        {activeTab === 'church' && (
          <div className="tab-content">
            <ChurchLinking />
          </div>
        )}
      </main>
    </div>
  );
}
