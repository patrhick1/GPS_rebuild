import { useState } from 'react';
import './SystemExport.css';

export function SystemExport() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleExport = async (type: 'users' | 'assessments' | 'full') => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/master/export/${type}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      // Download the CSV
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `gps_export_${type}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess(`${type === 'full' ? 'Full system' : type} export downloaded!`);
    } catch (err) {
      setError('Failed to export data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="system-export">
      <div className="page-header">
        <h1>System Data Export</h1>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      {success && (
        <div className="success-banner">
          {success}
          <button onClick={() => setSuccess('')}>×</button>
        </div>
      )}

      <div className="export-cards">
        <div className="export-card">
          <h2>Users Export</h2>
          <p>Export all users with their basic info and church associations.</p>
          <button 
            className="btn-export"
            onClick={() => handleExport('users')}
            disabled={loading}
          >
            {loading ? 'Exporting...' : 'Download Users CSV'}
          </button>
        </div>

        <div className="export-card">
          <h2>Assessments Export</h2>
          <p>Export all completed assessments with scores and results.</p>
          <button 
            className="btn-export"
            onClick={() => handleExport('assessments')}
            disabled={loading}
          >
            {loading ? 'Exporting...' : 'Download Assessments CSV'}
          </button>
        </div>

        <div className="export-card">
          <h2>Full System Export</h2>
          <p>Complete export including all users, assessments, churches, and audit logs.</p>
          <button 
            className="btn-export"
            onClick={() => handleExport('full')}
            disabled={loading}
          >
            {loading ? 'Exporting...' : 'Download Full Export'}
          </button>
        </div>
      </div>

      <div className="warning-box">
        <h3>⚠️ Important Notice</h3>
        <ul>
          <li>Exports contain sensitive user data</li>
          <li>Downloads are logged in the audit system</li>
          <li>Store exports securely and delete when no longer needed</li>
          <li>Comply with data protection regulations</li>
        </ul>
      </div>
    </div>
  );
}
