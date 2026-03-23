import { useEffect, useState, useRef } from 'react';
import { useAdmin } from '../context/AdminContext';
import './InvitesManagement.css';

export function InvitesManagement() {
  const {
    invites,
    isLoading,
    error,
    fetchInvites,
    createInvite,
    bulkInvite,
    uploadCSV,
    resendInvite,
    cancelInvite,
    clearError
  } = useAdmin();

  const [email, setEmail] = useState('');
  const [bulkEmails, setBulkEmails] = useState('');
  const [showBulk, setShowBulk] = useState(false);
  const [showCSV, setShowCSV] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchInvites();
  }, [fetchInvites]);

  const handleSingleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    
    try {
      await createInvite(email);
      setEmail('');
      fetchInvites();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create invite');
    }
  };

  const handleBulkInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bulkEmails.trim()) return;
    
    const emails = bulkEmails.split('\n').map(e => e.trim()).filter(e => e);
    
    try {
      const result = await bulkInvite(emails);
      setUploadResult(result);
      setBulkEmails('');
      fetchInvites();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to send invites');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      const result = await uploadCSV(file);
      setUploadResult(result);
      fetchInvites();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload CSV');
    }
  };

  const handleResend = async (id: string) => {
    await resendInvite(id);
    fetchInvites();
  };

  const handleCancel = async (id: string) => {
    if (!confirm('Cancel this invitation?')) return;
    await cancelInvite(id);
    fetchInvites();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted': return 'success';
      case 'sent': return 'pending';
      case 'revoked': return 'error';
      default: return '';
    }
  };

  return (
    <div className="invites-management">
      <header className="page-header">
        <h1>Invite Management</h1>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}

      {uploadResult && (
        <div className="result-banner">
          <p>Created: {uploadResult.created_count} invites</p>
          {uploadResult.failed.length > 0 && (
            <p>Failed: {uploadResult.failed.length}</p>
          )}
          <button onClick={() => setUploadResult(null)}>×</button>
        </div>
      )}

      {/* Single Invite */}
      <section className="invite-section">
        <h2>Send Single Invite</h2>
        <form onSubmit={handleSingleInvite} className="invite-form">
          <input
            type="email"
            placeholder="Enter email address..."
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit" className="btn-primary">
            Send Invite
          </button>
        </form>
      </section>

      {/* Bulk Invite Toggle */}
      <section className="invite-section">
        <button
          className="btn-toggle"
          onClick={() => setShowBulk(!showBulk)}
        >
          {showBulk ? 'Hide' : 'Show'} Bulk Invite
        </button>
        
        {showBulk && (
          <form onSubmit={handleBulkInvite} className="bulk-form">
            <textarea
              placeholder="Enter email addresses (one per line)..."
              value={bulkEmails}
              onChange={(e) => setBulkEmails(e.target.value)}
              rows={5}
              required
            />
            <button type="submit" className="btn-primary">
              Send Bulk Invites
            </button>
          </form>
        )}
      </section>

      {/* CSV Upload Toggle */}
      <section className="invite-section">
        <button
          className="btn-toggle"
          onClick={() => setShowCSV(!showCSV)}
        >
          {showCSV ? 'Hide' : 'Show'} CSV Upload
        </button>
        
        {showCSV && (
          <div className="csv-upload">
            <p>Upload a CSV file with email addresses in the first column</p>
            <input
              type="file"
              accept=".csv"
              ref={fileInputRef}
              onChange={handleFileUpload}
            />
          </div>
        )}
      </section>

      {/* Invites List */}
      <section className="invites-list-section">
        <h2>Sent Invitations</h2>
        
        {isLoading ? (
          <p>Loading...</p>
        ) : invites.length === 0 ? (
          <p className="no-data">No invitations sent yet</p>
        ) : (
          <div className="invites-table">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Sent</th>
                  <th>Expires</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => (
                  <tr key={invite.id}>
                    <td>{invite.email}</td>
                    <td>
                      <span className={`status-badge ${getStatusColor(invite.status)}`}>
                        {invite.status}
                      </span>
                    </td>
                    <td>{new Date(invite.created_at).toLocaleDateString()}</td>
                    <td>
                      {invite.expires_at
                        ? new Date(invite.expires_at).toLocaleDateString()
                        : 'N/A'}
                    </td>
                    <td>
                      {invite.status === 'sent' && (
                        <>
                          <button
                            className="btn-resend"
                            onClick={() => handleResend(invite.id)}
                          >
                            Resend
                          </button>
                          <button
                            className="btn-cancel"
                            onClick={() => handleCancel(invite.id)}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
