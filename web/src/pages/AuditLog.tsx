import { useEffect, useState } from 'react';
import { useMaster } from '../context/MasterContext';
import './AuditLog.css';

export function AuditLog() {
  const { auditLog, fetchAuditLog, error, clearError, totalAuditPages } = useMaster();
  const [filters, setFilters] = useState({ action: '', target_type: '' });
  const [selectedEntry, setSelectedEntry] = useState<any>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    fetchAuditLog();
  }, [fetchAuditLog]);

  const handleFilter = () => {
    const activeFilters: any = {};
    if (filters.action) activeFilters.action = filters.action;
    if (filters.target_type) activeFilters.target_type = filters.target_type;
    fetchAuditLog(1, activeFilters);
  };

  const viewDetail = (entry: any) => {
    setSelectedEntry(entry);
    setShowDetail(true);
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'impersonate': return 'warning';
      case 'role_change': return 'info';
      case 'export': return 'success';
      default: return '';
    }
  };

  return (
    <div className="audit-log">
      <header className="page-header">
        <h1>Audit Log</h1>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}

      {/* Filters */}
      <div className="filters-bar">
        <select
          value={filters.action}
          onChange={(e) => setFilters({ ...filters, action: e.target.value })}
        >
          <option value="">All Actions</option>
          <option value="impersonate">Impersonate</option>
          <option value="role_change">Role Change</option>
          <option value="export">Export</option>
        </select>

        <select
          value={filters.target_type}
          onChange={(e) => setFilters({ ...filters, target_type: e.target.value })}
        >
          <option value="">All Targets</option>
          <option value="user">User</option>
          <option value="organization">Organization</option>
        </select>

        <button className="btn-primary" onClick={handleFilter}>
          Apply Filters
        </button>
      </div>

      {/* Log Table */}
      <div className="log-table">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Action</th>
              <th>Target</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {auditLog.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.created_at).toLocaleString()}</td>
                <td>{entry.user_name}</td>
                <td>
                  <span className={`action-badge ${getActionColor(entry.action)}`}>
                    {entry.action}
                  </span>
                </td>
                <td>
                  {entry.target_type} {entry.target_id ? `(${entry.target_id.slice(0, 8)}...)` : ''}
                </td>
                <td>
                  <button
                    className="btn-view"
                    onClick={() => viewDetail(entry)}
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalAuditPages > 1 && (
        <div className="pagination">
          {Array.from({ length: totalAuditPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              className="page-btn"
              onClick={() => fetchAuditLog(page, filters)}
            >
              {page}
            </button>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {showDetail && selectedEntry && (
        <div className="modal-overlay" onClick={() => setShowDetail(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Audit Entry Details</h2>
            <div className="detail-content">
              <p><strong>ID:</strong> {selectedEntry.id}</p>
              <p><strong>Time:</strong> {new Date(selectedEntry.created_at).toLocaleString()}</p>
              <p><strong>User:</strong> {selectedEntry.user_name} ({selectedEntry.user_email})</p>
              <p><strong>Action:</strong> {selectedEntry.action}</p>
              <p><strong>Target Type:</strong> {selectedEntry.target_type}</p>
              <p><strong>Target ID:</strong> {selectedEntry.target_id}</p>
              
              {selectedEntry.details && (
                <div className="details-section">
                  <h3>Details</h3>
                  <pre>{JSON.stringify(selectedEntry.details, null, 2)}</pre>
                </div>
              )}
            </div>
            <button className="btn-close" onClick={() => setShowDetail(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
