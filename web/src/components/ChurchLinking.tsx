import { useState } from 'react';
import { useDashboard } from '../context/DashboardContext';
import './ChurchLinking.css';

export function ChurchLinking() {
  const { summary, searchChurches, requestChurchLink, leaveOrganization, isLoading } = useDashboard();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setIsSearching(true);
    try {
      const results = await searchChurches(searchQuery);
      setSearchResults(results);
    } catch (err) {
      setMessage('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleLink = async (orgId: string) => {
    try {
      await requestChurchLink(orgId);
      setMessage('Request sent! The church admin will review your request.');
      setSearchResults([]);
      setSearchQuery('');
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Failed to send request');
    }
  };

  const handleLeave = async () => {
    if (!window.confirm('Are you sure you want to leave your current organization?')) {
      return;
    }
    
    try {
      await leaveOrganization();
      setMessage('You have left the organization.');
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Failed to leave organization');
    }
  };

  const hasOrganization = summary?.stats.has_organization;
  const currentOrg = summary?.organization;

  return (
    <div className="church-linking">
      <h2>Church Affiliation</h2>

      {message && (
        <div className="message-banner">
          {message}
          <button onClick={() => setMessage(null)}>×</button>
        </div>
      )}

      {/* Current Status */}
      <div className="current-status">
        <h3>Current Status</h3>
        {hasOrganization && currentOrg ? (
          <div className="org-card">
            <div className="org-info">
              <h4>{currentOrg.name}</h4>
              <span className="role-badge">{currentOrg.role}</span>
            </div>
            <button className="btn-leave" onClick={handleLeave}>
              Leave Organization
            </button>
          </div>
        ) : (
          <div className="no-org">
            <p>You are currently an independent user (not affiliated with any church).</p>
          </div>
        )}
      </div>

      {/* Search for Churches */}
      {!hasOrganization && (
        <div className="search-section">
          <h3>Find Your Church</h3>
          <p>Search for your church to request affiliation.</p>
          
          <div className="search-box">
            <input
              type="text"
              placeholder="Search by church name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              className="btn-primary"
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
            >
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="search-results">
              <h4>Search Results</h4>
              {searchResults.map((church) => (
                <div key={church.id} className="church-result">
                  <div className="church-info">
                    <h5>{church.name}</h5>
                    <p>
                      {church.city}{church.state && `, ${church.state}`}
                      {' • '}
                      {church.member_count} members
                    </p>
                  </div>
                  <button
                    className="btn-link"
                    onClick={() => handleLink(church.id)}
                    disabled={isLoading}
                  >
                    Request to Join
                  </button>
                </div>
              ))}
            </div>
          )}

          {searchResults.length === 0 && !isSearching && searchQuery && (
            <div className="no-results">
              <p>No churches found matching "{searchQuery}"</p>
              <p>Try a different search term or contact your church admin.</p>
            </div>
          )}
        </div>
      )}

      {/* Upgrade to Admin Section */}
      <div className="upgrade-section">
        <h3>Want to Register Your Church?</h3>
        <p>
          If you're a church administrator and want to register your organization
          for GPS assessments, you can upgrade your account.
        </p>
        <button className="btn-secondary" disabled>
          Upgrade to Church Admin (Coming Soon)
        </button>
      </div>
    </div>
  );
}
