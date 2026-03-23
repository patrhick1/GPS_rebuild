import { useEffect, useState } from 'react';
import { useAdmin } from '../context/AdminContext';
import './MembersManagement.css';

export function MembersManagement() {
  const {
    members,
    pending,
    isLoading,
    error,
    totalPages,
    currentPage,
    fetchMembers,
    fetchPending,
    approvePending,
    declinePending,
    removeMember,
    clearError
  } = useAdmin();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [activeTab, setActiveTab] = useState<'members' | 'pending'>('members');

  useEffect(() => {
    if (activeTab === 'members') {
      fetchMembers(1, search, statusFilter);
    } else {
      fetchPending();
    }
  }, [activeTab, fetchMembers, fetchPending]);

  const handleSearch = () => {
    fetchMembers(1, search, statusFilter);
  };

  const handleApprove = async (id: string) => {
    await approvePending(id);
    fetchPending();
  };

  const handleDecline = async (id: string) => {
    await declinePending(id);
    fetchPending();
  };

  const handleRemove = async (id: string) => {
    if (!confirm('Are you sure you want to remove this member?')) return;
    await removeMember(id);
    fetchMembers(currentPage, search, statusFilter);
  };

  const viewDetail = (member: any) => {
    setSelectedMember(member);
    setShowDetail(true);
  };

  return (
    <div className="members-management">
      <header className="page-header">
        <h1>Member Management</h1>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        <button
          className={activeTab === 'members' ? 'active' : ''}
          onClick={() => setActiveTab('members')}
        >
          Members ({members.length})
        </button>
        <button
          className={activeTab === 'pending' ? 'active' : ''}
          onClick={() => setActiveTab('pending')}
        >
          Pending ({pending.length})
        </button>
      </div>

      {/* Members Tab */}
      {activeTab === 'members' && (
        <>
          {/* Search & Filter */}
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="pending">Pending</option>
            </select>
            <button className="btn-primary" onClick={handleSearch}>
              Search
            </button>
          </div>

          {/* Members Table */}
          <div className="members-table">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Assessments</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id}>
                    <td>
                      {member.first_name} {member.last_name}
                    </td>
                    <td>{member.email}</td>
                    <td>{member.role}</td>
                    <td>
                      <span className={`status-badge ${member.status}`}>
                        {member.status}
                      </span>
                    </td>
                    <td>{member.assessment_count}</td>
                    <td>
                      <button
                        className="btn-view"
                        onClick={() => viewDetail(member)}
                      >
                        View
                      </button>
                      <button
                        className="btn-remove"
                        onClick={() => handleRemove(member.id)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  className={page === currentPage ? 'active' : ''}
                  onClick={() => fetchMembers(page, search, statusFilter)}
                >
                  {page}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {/* Pending Tab */}
      {activeTab === 'pending' && (
        <div className="pending-list">
          {pending.length === 0 ? (
            <p className="no-data">No pending membership requests</p>
          ) : (
            pending.map((request) => (
              <div key={request.membership_id} className="pending-card">
                <div className="pending-info">
                  <h3>{request.first_name} {request.last_name}</h3>
                  <p>{request.email}</p>
                  <span>
                    Requested {new Date(request.requested_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="pending-actions">
                  <button
                    className="btn-approve"
                    onClick={() => handleApprove(request.membership_id)}
                  >
                    Approve
                  </button>
                  <button
                    className="btn-decline"
                    onClick={() => handleDecline(request.membership_id)}
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Member Detail Modal */}
      {showDetail && selectedMember && (
        <div className="modal-overlay" onClick={() => setShowDetail(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Member Details</h2>
            <div className="detail-content">
              <p><strong>Name:</strong> {selectedMember.first_name} {selectedMember.last_name}</p>
              <p><strong>Email:</strong> {selectedMember.email}</p>
              <p><strong>Phone:</strong> {selectedMember.phone_number || 'N/A'}</p>
              <p><strong>Role:</strong> {selectedMember.role}</p>
              <p><strong>Status:</strong> {selectedMember.status}</p>
              <p><strong>Joined:</strong> {new Date(selectedMember.joined_at).toLocaleDateString()}</p>
              <p><strong>Assessments:</strong> {selectedMember.assessment_count}</p>
              {selectedMember.last_assessment_date && (
                <p><strong>Last Assessment:</strong> {new Date(selectedMember.last_assessment_date).toLocaleDateString()}</p>
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
