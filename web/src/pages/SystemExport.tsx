import { useState, useEffect } from 'react';
import { useMaster } from '../context/MasterContext';
import './SystemExport.css';

export function SystemExport() {
  const { churches, fetchChurches } = useMaster();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filter state
  const [churchId, setChurchId] = useState('');
  const [instrument, setInstrument] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Confirmation modal
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingType, setPendingType] = useState<'users' | 'assessments' | 'full'>('users');

  useEffect(() => {
    fetchChurches();
  }, [fetchChurches]);

  const buildParams = () => {
    const params = new URLSearchParams();
    if (churchId) params.set('church_id', churchId);
    if (instrument) params.set('instrument', instrument);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return params.toString();
  };

  const getFilterSummary = () => {
    const parts: string[] = [];
    if (churchId) {
      const church = churches.find(c => String(c.id) === churchId);
      parts.push(`Church: ${church?.name || churchId}`);
    } else {
      parts.push('All churches');
    }
    if (instrument) {
      parts.push(`Instrument: ${instrument === 'gps' ? 'GPS' : 'MyImpact'}`);
    } else {
      parts.push('All instruments');
    }
    if (dateFrom || dateTo) {
      parts.push(`Date: ${dateFrom || 'beginning'} — ${dateTo || 'present'}`);
    } else {
      parts.push('All dates');
    }
    return parts;
  };

  const handleExportClick = (type: 'users' | 'assessments' | 'full') => {
    setPendingType(type);
    setShowConfirm(true);
  };

  const handleConfirmExport = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    setShowConfirm(false);

    try {
      const token = localStorage.getItem('access_token');
      const qs = buildParams();
      const response = await fetch(`/api/master/export/${pendingType}${qs ? `?${qs}` : ''}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `gps_export_${pendingType}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess(`${pendingType === 'full' ? 'Full system' : pendingType} export downloaded!`);
    } catch (err) {
      setError('Failed to export data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const hasFilters = churchId || instrument || dateFrom || dateTo;

  return (
    <div className="system-export">
      <div className="page-header">
        <h1>System Data Export</h1>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>&times;</button>
        </div>
      )}

      {success && (
        <div className="success-banner">
          {success}
          <button onClick={() => setSuccess('')}>&times;</button>
        </div>
      )}

      {/* Filter Controls */}
      <div className="filter-section">
        <h2>Export Filters</h2>
        <p className="filter-description">
          Apply filters before exporting. Filters apply to assessments and full system exports.
        </p>

        <div className="filter-grid">
          <div className="filter-field">
            <label>Church</label>
            <select value={churchId} onChange={(e) => setChurchId(e.target.value)}>
              <option value="">All Churches</option>
              {churches.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="filter-field">
            <label>Assessment Type</label>
            <select value={instrument} onChange={(e) => setInstrument(e.target.value)}>
              <option value="">All Types</option>
              <option value="gps">GPS</option>
              <option value="myimpact">MyImpact</option>
            </select>
          </div>

          <div className="filter-field">
            <label>From Date</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>

          <div className="filter-field">
            <label>To Date</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>

        {hasFilters && (
          <div className="filter-summary">
            <strong>Active filters:</strong>
            <ul>
              {getFilterSummary().map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
            <button className="btn-clear-filters" onClick={() => { setChurchId(''); setInstrument(''); setDateFrom(''); setDateTo(''); }}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      <div className="export-cards">
        <div className="export-card">
          <h2>Users Export</h2>
          <p>Export all users with their basic info and church associations.</p>
          <button
            className="btn-export"
            onClick={() => handleExportClick('users')}
            disabled={loading}
          >
            {loading && pendingType === 'users' ? 'Exporting...' : 'Download Users CSV'}
          </button>
        </div>

        <div className="export-card">
          <h2>Assessments Export</h2>
          <p>Export all completed assessments with scores and results.</p>
          <button
            className="btn-export"
            onClick={() => handleExportClick('assessments')}
            disabled={loading}
          >
            {loading && pendingType === 'assessments' ? 'Exporting...' : 'Download Assessments CSV'}
          </button>
        </div>

        <div className="export-card">
          <h2>Full System Export</h2>
          <p>Complete export including all users, assessments, churches, and audit logs.</p>
          <button
            className="btn-export"
            onClick={() => handleExportClick('full')}
            disabled={loading}
          >
            {loading && pendingType === 'full' ? 'Exporting...' : 'Download Full Export'}
          </button>
        </div>
      </div>

      <div className="warning-box">
        <h3>Important Notice</h3>
        <ul>
          <li>Exports contain sensitive user data</li>
          <li>Downloads are logged in the audit system</li>
          <li>Store exports securely and delete when no longer needed</li>
          <li>Comply with data protection regulations</li>
        </ul>
      </div>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Confirm Export</h2>
            <p>You are about to export <strong>{pendingType === 'full' ? 'full system' : pendingType}</strong> data.</p>

            <div className="confirm-summary">
              <strong>Filters applied:</strong>
              <ul>
                {getFilterSummary().map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
              <p className="confirm-filename">
                <strong>Filename:</strong> gps_export_{pendingType}_{new Date().toISOString().split('T')[0]}.csv
              </p>
            </div>

            {/* CSV Column Preview */}
            <div className="csv-preview-box">
              <p className="csv-preview-label">
                CSV Preview — column headers
              </p>
              <div className="csv-preview-scroll">
                <div className="csv-preview-chips">
                  {(pendingType === 'users'
                    ? ['ID', 'Email', 'First Name', 'Last Name', 'Status', 'Organization', 'Role', 'Created At']
                    : pendingType === 'assessments'
                    ? ['Assessment ID', 'User Email', 'Church', 'Instrument', 'Completed At', 'Gift 1', 'Score 1', 'Gift 2', 'Score 2']
                    : ['Users', 'Churches', 'Assessments', 'Audit Log']
                  ).map((col) => (
                    <span key={col} className="csv-preview-chip">
                      {col}
                    </span>
                  ))}
                </div>
                {pendingType === 'full' && (
                  <p className="csv-preview-note">Full export includes all four data sections in a single CSV file.</p>
                )}
              </div>
            </div>

            <div className="confirm-actions">
              <button className="btn-cancel" onClick={() => setShowConfirm(false)}>
                Cancel
              </button>
              <button className="btn-confirm" onClick={handleConfirmExport}>
                Download CSV
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
