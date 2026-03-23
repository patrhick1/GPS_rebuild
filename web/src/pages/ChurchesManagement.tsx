import { useEffect, useState } from 'react';
import { useMaster } from '../context/MasterContext';
import './ChurchesManagement.css';

export function ChurchesManagement() {
  const { churches, fetchChurches, isLoading, error, clearError, totalChurchPages } = useMaster();
  const [search, setSearch] = useState('');
  const [selectedChurch, setSelectedChurch] = useState<any>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    fetchChurches();
  }, [fetchChurches]);

  const handleSearch = () => {
    fetchChurches(1, search);
  };

  const viewDetail = (church: any) => {
    setSelectedChurch(church);
    setShowDetail(true);
  };

  return (
    <div className="churches-management">
      <header className="page-header">
        <h1>Church Management</h1>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}

      {/* Search */}
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search churches by name or city..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn-primary" onClick={handleSearch}>
          Search
        </button>
      </div>

      {/* Churches Table */}
      <div className="churches-table">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Location</th>
              <th>Members</th>
              <th>Assessments</th>
              <th>Admins</th>
              <th>Last Activity</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {churches.map((church) => (
              <tr key={church.id}>
                <td>{church.name}</td>
                <td>
                  {church.city}{church.state && `, ${church.state}`}
                </td>
                <td>{church.member_count}</td>
                <td>{church.assessment_count}</td>
                <td>
                  {church.admins.map(a => a.name).join(', ') || 'None'}
                </td>
                <td>
                  {church.last_activity
                    ? new Date(church.last_activity).toLocaleDateString()
                    : 'Never'}
                </td>
                <td>
                  <button
                    className="btn-view"
                    onClick={() => viewDetail(church)}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalChurchPages > 1 && (
        <div className="pagination">
          {Array.from({ length: totalChurchPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              className="page-btn"
              onClick={() => fetchChurches(page, search)}
            >
              {page}
            </button>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {showDetail && selectedChurch && (
        <div className="modal-overlay" onClick={() => setShowDetail(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{selectedChurch.name}</h2>
            <div className="detail-content">
              <p><strong>Key:</strong> {selectedChurch.key}</p>
              <p><strong>Location:</strong> {selectedChurch.city}, {selectedChurch.state}</p>
              <p><strong>Members:</strong> {selectedChurch.member_count}</p>
              <p><strong>Assessments:</strong> {selectedChurch.assessment_count}</p>
              <p><strong>Created:</strong> {new Date(selectedChurch.created_at).toLocaleDateString()}</p>
              
              <h3>Admins</h3>
              <ul>
                {selectedChurch.admins.map((admin: any) => (
                  <li key={admin.id}>
                    {admin.name} ({admin.email})
                  </li>
                ))}
              </ul>
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
