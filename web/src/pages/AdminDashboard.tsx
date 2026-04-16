import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { useAdmin } from '../context/AdminContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';
import tealArrowIcon from '../../Graphics for Dev/Icons/Dark Teal Arrow Circle Icon.svg';
import searchIcon from '../../Graphics for Dev/Icons/Charcoal Search Icon.svg';
import trashIcon from '../../Graphics for Dev/Icons/Dark Teal Trash Can Icon.svg';
import nextIcon from '../../Graphics for Dev/Icons/Charcoal Next Icon.svg';
import lastIcon from '../../Graphics for Dev/Icons/Charcoal Last Icon.svg';

type AdminTab = 'gps' | 'myimpact' | 'settings';

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
  'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
  'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
  'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
];

function MyImpactScoreBadge({ score }: { score?: number | null }) {
  if (score == null) return <span className="font-body font-bold text-lg text-brand-charcoal">—</span>;
  return (
    <span className="inline-flex items-center h-8 px-3 rounded-full font-body font-bold text-base bg-brand-teal-light/30 text-brand-charcoal">
      {score.toFixed(0)}
    </span>
  );
}

export function AdminDashboard() {
  const { user, logout } = useAuth();
  const {
    members,
    pending,
    churchSettings,
    stats,
    isLoading,
    isSaving,
    error,
    totalPages,
    currentPage,
    fetchMembers,
    fetchPending,
    fetchSettings,
    fetchStats,
    updateSettings,
    approvePending,
    declinePending,
    toggleAdmin,
    transferPrimaryAdmin,
    removeMember,
    clearError,
  } = useAdmin();

  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<AdminTab>('gps');
  const [menuOpen, setMenuOpen] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [noSubscription, setNoSubscription] = useState(false);
  const [primaryAdminInfo, setPrimaryAdminInfo] = useState<{ name: string; email: string } | null>(null);
  const [transferTarget, setTransferTarget] = useState<typeof members[0] | null>(null);
  const [isTransferring, setIsTransferring] = useState(false);
  const [search, setSearch] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportInstrument, setExportInstrument] = useState('');
  const [exportDateFrom, setExportDateFrom] = useState('');
  const [exportDateTo, setExportDateTo] = useState('');
  const [exportFormat, setExportFormat] = useState('');
  const [sortField, setSortField] = useState<string>('');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [selectedMember, setSelectedMember] = useState<typeof members[0] | null>(null);
  const [isMemberExporting, setIsMemberExporting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Church settings form state
  const [churchName, setChurchName] = useState('');
  const [churchCity, setChurchCity] = useState('');
  const [churchState, setChurchState] = useState('');
  const [settingsMsg, setSettingsMsg] = useState('');

  useEffect(() => {
    fetchMembers();
    fetchPending();
    fetchSettings();
    fetchStats();
  }, [fetchMembers, fetchPending, fetchSettings, fetchStats]);

  useEffect(() => {
    api.get('/billing/subscription/status').then((res) => {
      const subStatus = res.data?.status;
      if (res.data?.primary_admin_name) {
        setPrimaryAdminInfo({ name: res.data.primary_admin_name, email: res.data.primary_admin_email });
      }
      if (subStatus === 'no_subscription') {
        // Primary admins will be redirected by the global interceptor when member fetches fail.
        // Secondary admins see a dedicated banner and all write actions are disabled.
        if (!user?.is_primary_admin) {
          setNoSubscription(true);
          setIsReadOnly(true);
        }
      } else if (subStatus && !['active', 'trialing', 'past_due'].includes(subStatus)) {
        setIsReadOnly(true);
      }
    }).catch(() => {
      // Ignore — member fetch 402s are handled by the global interceptor
    });
  }, [user?.is_primary_admin]);

  // Sync church settings form
  useEffect(() => {
    if (churchSettings) {
      setChurchName(churchSettings.name || '');
      setChurchCity(churchSettings.city || '');
      setChurchState(churchSettings.state || '');
    }
  }, [churchSettings]);

  // Close menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const firstName = user?.first_name || 'Admin';

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
    });
  };

  const handleSearch = () => {
    fetchMembers(1, search);
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handlePageChange = (page: number) => {
    fetchMembers(page, search);
  };

  const handleSaveSettings = async () => {
    clearError();
    setSettingsMsg('');
    try {
      await updateSettings({ ...churchSettings, name: churchName, city: churchCity, state: churchState });
      setSettingsMsg('Settings saved successfully.');
      setTimeout(() => setSettingsMsg(''), 3000);
    } catch {
      // error set in context
    }
  };

  const handleCopyLink = () => {
    if (churchSettings?.key) {
      const link = `${window.location.origin}/register?org=${churchSettings.key}`;
      navigator.clipboard.writeText(link);
      alert('Assessment link copied to clipboard!');
    }
  };

  const handleExportCSV = () => {
    setShowExportModal(true);
  };

  const handleConfirmExport = async () => {
    setIsExporting(true);
    setExportMsg('');
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (exportInstrument) params.set('instrument', exportInstrument);
      if (exportDateFrom) params.set('date_from', exportDateFrom);
      if (exportDateTo) params.set('date_to', exportDateTo);
      if (exportFormat) params.set('format', exportFormat);
      const qs = params.toString();
      const response = await fetch(`/api/admin/export/csv${qs ? `?${qs}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const disposition = response.headers.get('Content-Disposition');
      const filename = disposition?.split('filename=')[1]?.replace(/"/g, '') || 'church-data.csv';
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setExportMsg('Export downloaded successfully.');
      setTimeout(() => setExportMsg(''), 3000);
      setShowExportModal(false);
    } catch {
      setExportMsg('Failed to export data. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const sortIndicator = (field: string) =>
    sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  const sortedMembers = [...members].sort((a, b) => {
    if (!sortField) return 0;
    const dir = sortDir === 'asc' ? 1 : -1;
    switch (sortField) {
      case 'name': {
        const aName = `${a.first_name} ${a.last_name}`.toLowerCase();
        const bName = `${b.first_name} ${b.last_name}`.toLowerCase();
        return aName.localeCompare(bName) * dir;
      }
      case 'date': {
        const aDate = a.last_assessment_date || '';
        const bDate = b.last_assessment_date || '';
        return aDate.localeCompare(bDate) * dir;
      }
      case 'character': {
        const aScore = a.myimpact_character_score ?? -1;
        const bScore = b.myimpact_character_score ?? -1;
        return (aScore - bScore) * dir;
      }
      case 'calling': {
        const aScore = a.myimpact_calling_score ?? -1;
        const bScore = b.myimpact_calling_score ?? -1;
        return (aScore - bScore) * dir;
      }
      case 'myimpact': {
        const aScore = a.myimpact_score ?? -1;
        const bScore = b.myimpact_score ?? -1;
        return (aScore - bScore) * dir;
      }
      default:
        return 0;
    }
  });

  const handleExportMemberCSV = async (member: typeof members[0]) => {
    setIsMemberExporting(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/admin/export/csv/${member.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${member.first_name}-${member.last_name}-data.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Failed to export member data.');
    } finally {
      setIsMemberExporting(false);
    }
  };

  const handlePrintMember = (member: typeof members[0]) => {
    const w = window.open('', '_blank', 'width=800,height=600');
    if (!w) return;
    const gifts = (member.top_gifts || []).map(g => g.short_code || g.name).join(', ');
    const passions = (member.top_passions || []).map(p => p.name).join(', ');
    w.document.write(`
      <html><head><title>${member.first_name} ${member.last_name} — Member Report</title>
      <style>body{font-family:sans-serif;padding:40px;color:#333}h1{font-size:24px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #ddd}th{background:#f5f5f5;font-size:13px;text-transform:uppercase;color:#666}</style></head>
      <body>
        <h1>${member.first_name} ${member.last_name}</h1>
        <p><strong>Email:</strong> ${member.email || '—'}</p>
        <p><strong>Status:</strong> ${member.status || '—'}</p>
        <p><strong>Last Assessment:</strong> ${formatDate(member.last_assessment_date)}</p>
        <table>
          <tr><th>Gifts</th><td>${gifts || '—'}</td></tr>
          <tr><th>Influencing Style</th><td>${passions || '—'}</td></tr>
          ${member.myimpact_score != null ? `
          <tr><th>MyImpact Score</th><td>${member.myimpact_score}</td></tr>
          <tr><th>Character</th><td>${member.myimpact_character_score ?? '—'}</td></tr>
          <tr><th>Calling</th><td>${member.myimpact_calling_score ?? '—'}</td></tr>
          ` : ''}
        </table>
        <p style="margin-top:20px;font-size:12px;color:#999">Printed from GPS Admin Dashboard — ${churchSettings?.name || ''}</p>
      </body></html>
    `);
    w.document.close();
    w.print();
  };

  const adminMembers = members.filter((m) => m.role === 'admin' || m.role === 'master');

  // Shared member row action handler
  const handleViewResults = (member: typeof members[0]) => {
    if (activeTab === 'myimpact') {
      if (member.latest_myimpact_assessment_id) {
        navigate(`/myimpact-results?id=${member.latest_myimpact_assessment_id}`);
      }
    } else {
      if (member.latest_gps_assessment_id) {
        navigate(`/assessment-results?id=${member.latest_gps_assessment_id}`);
      }
    }
  };

  const handleRemoveMember = async (member: typeof members[0]) => {
    if (confirm(`Remove ${member.first_name} ${member.last_name} from the organization?`)) {
      await removeMember(member.id);
      fetchMembers();
    }
  };

  const hasResults = (member: typeof members[0]) =>
    activeTab === 'myimpact'
      ? !!member.latest_myimpact_assessment_id
      : !!member.latest_gps_assessment_id;

  const handleConfirmTransfer = async () => {
    if (!transferTarget) return;
    setIsTransferring(true);
    try {
      await transferPrimaryAdmin(transferTarget.id.toString());
      setTransferTarget(null);
    } catch {
      // error surfaced via AdminContext
    } finally {
      setIsTransferring(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        {noSubscription && (
          <div className="max-w-[1400px] mx-auto px-6 md:px-10 pt-6">
            <div className="bg-amber-50 border border-amber-300 text-amber-800 px-5 py-4 rounded-xl font-body text-base">
              <span className="font-bold">No active subscription.</span>
              {' '}Your church hasn't set up a subscription yet.
              {primaryAdminInfo
                ? <> Contact <span className="font-bold">{primaryAdminInfo.name}</span> ({primaryAdminInfo.email}), the primary administrator, to get started.</>
                : ' Contact the primary administrator to get started.'}
            </div>
          </div>
        )}

        {isReadOnly && (
          <div className="max-w-[1400px] mx-auto px-6 md:px-10 pt-6">
            <div className="bg-amber-50 border border-amber-300 text-amber-800 px-5 py-4 rounded-xl font-body text-base flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <span className="font-bold">Your subscription has expired.</span>
                {' '}You can view existing member data, but inviting, approving, and editing are disabled.
                {!user?.is_primary_admin && (
                  primaryAdminInfo
                    ? <span> Contact <span className="font-bold">{primaryAdminInfo.name}</span> ({primaryAdminInfo.email}), the primary administrator, to renew.</span>
                    : <span> Contact your organization's primary admin to renew.</span>
                )}
              </div>
              {user?.is_primary_admin && (
                <button
                  onClick={() => navigate('/admin/billing')}
                  className="shrink-0 h-[40px] px-5 bg-amber-600 text-white font-body font-bold text-base rounded-xl hover:bg-amber-700 transition-colors whitespace-nowrap"
                >
                  Renew Now →
                </button>
              )}
            </div>
          </div>
        )}

        {error && error !== 'no_subscription' && (
          <div className="max-w-[1400px] mx-auto px-6 md:px-10 pt-6">
            <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-3 rounded-xl font-body text-base flex items-center justify-between">
              <span>{error}</span>
              <button onClick={clearError} className="ml-4 text-red-500 hover:text-red-700 font-bold text-lg leading-none" aria-label="Dismiss error">&times;</button>
            </div>
          </div>
        )}

        {/* ── Header ── */}
        <section className="max-w-[1400px] mx-auto px-6 md:px-10 pt-10 pb-6">
          <div className="flex items-start justify-between">
            {/* Title */}
            <div>
              <h1 className="font-heading text-[36px] md:text-[48px] leading-[40px] md:leading-[55px] text-brand-charcoal">
                <span className="font-medium">Welcome to Your Admin Account,</span>{' '}
                <span className="font-black">{firstName}</span>
              </h1>
              {churchSettings && (
                <p className="font-body font-semibold text-lg text-brand-teal mt-2">
                  {churchSettings.name}
                </p>
              )}
            </div>

            {/* Gold hamburger menu */}
            <div className="relative" ref={menuRef}>
              <button onClick={() => setMenuOpen(!menuOpen)} className="p-2" aria-label="Toggle menu">
                <img src={menuOpen ? goldXIcon : goldMenuIcon} alt="" className="w-[50px] h-auto" />
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-full mt-2 w-[260px] bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] z-50 py-2">
                  {[
                    ...(user?.role === 'master' ? [{ label: '← Back to Master Dashboard', action: () => navigate('/master') }] : []),
                    { label: 'GPS Assessments', action: () => navigate('/dashboard') },
                    { label: 'MyImpact Assessments', action: () => navigate('/dashboard') },
                    { label: 'Account', action: () => navigate('/account') },
                    { label: 'Update Password', action: () => navigate('/update-password') },
                    { label: 'Logout', action: () => { setMenuOpen(false); logout(); } },
                  ].map((item) => (
                    <button
                      key={item.label}
                      onClick={() => { setMenuOpen(false); item.action(); }}
                      className="w-full text-left px-6 py-3 font-body font-bold text-base text-brand-charcoal hover:bg-brand-gray-light/30 transition-colors"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── Content: Sidebar + Main ── */}
        <section className="max-w-[1400px] mx-auto px-6 md:px-10 pb-10">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Left sidebar nav */}
            <aside className="lg:w-[280px] shrink-0">
              {user?.role === 'master' && (
                <button
                  onClick={() => navigate('/master')}
                  className="flex items-center gap-2 mb-4 font-body font-bold text-base text-brand-teal hover:text-brand-teal/80 transition-colors"
                >
                  <span className="text-lg">←</span> Back to Master Dashboard
                </button>
              )}
              {user?.role !== 'master' && (
                <button
                  onClick={() => navigate('/dashboard')}
                  className="flex items-center gap-2 mb-4 font-body font-bold text-base text-brand-teal hover:text-brand-teal/80 transition-colors"
                >
                  <span className="text-lg">←</span> Back to Member Dashboard
                </button>
              )}

              <button
                onClick={() => navigate('/dashboard')}
                className="font-heading font-medium text-[20px] md:text-[22px] leading-[32px] md:leading-[40px] text-brand-charcoal hover:text-brand-teal transition-colors mb-1"
              >
                My Assessments
              </button>

              {(['gps', 'myimpact', 'settings'] as AdminTab[]).map((tab) => {
                const labels: Record<AdminTab, string> = {
                  gps: 'GPS Member Assessments',
                  myimpact: 'MyImpact Member Assessments',
                  settings: 'Church Profile & Settings',
                };
                const isActive = activeTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex items-center gap-2 w-full text-left py-1.5 font-heading font-medium text-[16px] md:text-[18px] leading-[24px] md:leading-[28px] transition-colors ${
                      isActive
                        ? 'text-brand-teal'
                        : 'text-brand-charcoal hover:text-brand-teal'
                    }`}
                  >
                    {isActive && (
                      <img src={tealArrowIcon} alt="" className="w-[20px] h-[20px] md:w-[26px] md:h-[26px] shrink-0" />
                    )}
                    <span>{labels[tab]}</span>
                  </button>
                );
              })}
            </aside>

            {/* Right content */}
            <div className="flex-1 min-w-0">
              {/* Church Stats Overview */}
              {stats && (activeTab === 'gps' || activeTab === 'myimpact') && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white border border-brand-gray-light rounded-xl p-4 text-center shadow-sm">
                    <p className="font-heading font-black text-[28px] text-brand-teal">{stats.active_members}</p>
                    <p className="font-body text-sm text-brand-gray-med">Active Members</p>
                  </div>
                  <div className="bg-white border border-brand-gray-light rounded-xl p-4 text-center shadow-sm">
                    <p className="font-heading font-black text-[28px] text-brand-teal">{stats.gps_assessments}</p>
                    <p className="font-body text-sm text-brand-gray-med">GPS Assessments</p>
                  </div>
                  <div className="bg-white border border-brand-gray-light rounded-xl p-4 text-center shadow-sm">
                    <p className="font-heading font-black text-[28px] text-brand-teal">{stats.myimpact_assessments}</p>
                    <p className="font-body text-sm text-brand-gray-med">MyImpact Assessments</p>
                  </div>
                  {stats.avg_myimpact_score != null && (
                    <div className="bg-white border border-brand-gray-light rounded-xl p-4 text-center shadow-sm">
                      <p className="font-heading font-black text-[28px] text-brand-gold">{stats.avg_myimpact_score}</p>
                      <p className="font-body text-xs text-brand-gray-med mt-1">
                        Character {stats.avg_character_score} x Calling {stats.avg_calling_score}
                      </p>
                      <p className="font-body text-sm text-brand-gray-med">Avg MyImpact Score</p>
                    </div>
                  )}
                </div>
              )}

              {/* Pending Member Requests — shown on all tabs */}
              <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6 mb-8">
                  <h3 className="font-heading font-medium text-[24px] text-brand-charcoal mb-1">
                    Pending Member Requests
                  </h3>
                  <hr className="border-brand-gray-light mb-3" />
                  <p className="font-body font-semibold italic text-base text-brand-charcoal mb-4 leading-relaxed">
                    These users have asked to connect their Assessment results to your church.
                    Approve to add their data to your dashboard. Decline to keep their results private.
                  </p>

                  {pending.length === 0 ? (
                    <p className="font-body text-base text-brand-gray-med">No pending requests.</p>
                  ) : (
                    <div className="divide-y divide-brand-gray-light">
                      {pending.map((req) => (
                        <div key={req.membership_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                          <span className="font-body font-bold text-lg text-brand-charcoal">
                            {req.first_name} {req.last_name}
                          </span>
                          {!isReadOnly ? (
                            <div className="flex gap-3">
                              <button
                                onClick={async () => { await approvePending(req.membership_id); fetchPending(); fetchMembers(); }}
                                className="h-[50px] w-[133px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                              >
                                Accept
                              </button>
                              <button
                                onClick={async () => { await declinePending(req.membership_id); fetchPending(); }}
                                className="h-[50px] w-[133px] bg-[#E3E3E3] text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-[#d5d5d5] transition-colors"
                              >
                                Decline
                              </button>
                            </div>
                          ) : (
                            <span className="font-body text-sm text-amber-700 italic">Subscription required</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

            </div>
          </div>

          {/* ── Tab content — full width below sidebar row ── */}

              {/* ── GPS Members Tab ── */}
              {activeTab === 'gps' && (
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                  <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                    Gift Passion Story — Users &nbsp;|&nbsp; Admin Dashboard
                  </h2>

                  {/* Search bar + Gold link button + Export — responsive 3-tier layout */}
                  <div className="flex flex-col gap-3 mb-8">
                    <div className="flex gap-3">
                      {/* Input */}
                      <div className="relative flex-1 lg:max-w-[484px]">
                        <input
                          type="text"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          onKeyDown={handleSearchKeyDown}
                          placeholder="Search Member"
                          className="w-full h-[50px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 pr-10 font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60"
                        />
                        <img src={searchIcon} alt="" className="absolute right-3 top-1/2 -translate-y-1/2 w-[22px] h-[22px]" />
                      </div>
                      {/* Search button — inline on md+, hidden on mobile */}
                      <button
                        onClick={handleSearch}
                        className="hidden md:flex items-center justify-center h-[50px] w-[119px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors shrink-0"
                      >
                        Search
                      </button>
                      {/* Gold button — inline on desktop only */}
                      <button
                        onClick={handleCopyLink}
                        className="hidden lg:flex items-center h-[50px] px-6 bg-brand-gold text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gold/90 transition-colors whitespace-nowrap"
                      >
                        Access Unique Assessment Link
                      </button>
                      {/* Export CSV — inline on desktop only */}
                      <button
                        onClick={handleExportCSV}
                        disabled={isExporting}
                        className="hidden lg:flex items-center h-[50px] px-6 bg-brand-charcoal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-charcoal/90 transition-colors whitespace-nowrap disabled:opacity-50"
                      >
                        {isExporting ? 'Exporting...' : 'Export CSV'}
                      </button>
                    </div>
                    {/* Search button — mobile only, own row */}
                    <button
                      onClick={handleSearch}
                      className="md:hidden h-[50px] w-[119px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                    >
                      Search
                    </button>
                    {/* Gold button — tablet + mobile, own row */}
                    <button
                      onClick={handleCopyLink}
                      className="lg:hidden h-[50px] w-full bg-brand-gold text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gold/90 transition-colors"
                    >
                      Access Unique Assessment Link
                    </button>
                    {/* Export CSV — tablet + mobile, own row */}
                    <button
                      onClick={handleExportCSV}
                      disabled={isExporting}
                      className="lg:hidden h-[50px] w-full bg-brand-charcoal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-charcoal/90 transition-colors disabled:opacity-50"
                    >
                      {isExporting ? 'Exporting...' : 'Export CSV'}
                    </button>
                    {exportMsg && (
                      <p className={`font-body text-sm ${exportMsg.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                        {exportMsg}
                      </p>
                    )}
                  </div>

                  {/* ── Table (desktop lg+) ── */}
                  <div className="hidden lg:block overflow-x-auto">
                    <div className="grid grid-cols-[180px_130px_120px_120px_1fr] gap-2 mb-2">
                      <button onClick={() => handleSort('name')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Name{sortIndicator('name')}</button>
                      <button onClick={() => handleSort('date')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Last Assessment{sortIndicator('date')}</button>
                      <span className="font-body font-bold text-[16px] text-brand-gray-med uppercase">Gifts</span>
                      <span className="font-body font-bold text-[16px] text-brand-gray-med uppercase">Influencing Style</span>
                      <span />
                    </div>
                    <hr className="border-brand-gray-light mb-2" />

                    {isLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="w-8 h-8 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : sortedMembers.length === 0 ? (
                      <p className="font-body text-base text-brand-gray-med py-8 text-center">No members found.</p>
                    ) : (
                      sortedMembers.map((member) => (
                        <div key={member.id}>
                          <div className="grid grid-cols-[180px_130px_120px_120px_1fr] gap-2 items-center py-3">
                            <button onClick={() => setSelectedMember(member)} className="font-body font-bold text-lg text-brand-teal truncate text-left hover:underline cursor-pointer">
                              {member.first_name} {member.last_name}
                            </button>
                            <span className="font-body font-bold text-lg text-brand-charcoal">
                              {formatDate(member.last_assessment_date)}
                            </span>
                            <div className="flex gap-1 flex-wrap">
                              {(member.top_gifts || []).map((g, i) => (
                                <span key={i} className="inline-flex items-center justify-center h-8 px-3 bg-[rgba(167,185,211,0.5)] rounded-full font-body font-bold text-lg text-brand-charcoal">
                                  {g.short_code}
                                </span>
                              ))}
                            </div>
                            <div className="flex gap-1 flex-wrap">
                              {(member.top_passions || []).map((p, i) => (
                                <span key={i} className="inline-flex items-center justify-center h-8 px-4 bg-[rgba(227,162,162,0.5)] rounded-full font-body font-bold text-lg text-brand-charcoal">
                                  {p.name}
                                </span>
                              ))}
                            </div>
                            <div className="flex items-center gap-2 justify-end flex-wrap">
                              <button
                                onClick={() => handleViewResults(member)}
                                disabled={!hasResults(member)}
                                className={`h-[50px] w-[133px] font-body font-bold text-lg rounded-xl transition-colors ${
                                  hasResults(member)
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                  className={`h-[50px] w-[175px] font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                    member.is_admin
                                      ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                      : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                  }`}
                                >
                                  {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                </button>
                              )}
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => handleRemoveMember(member)}
                                  className="p-2 hover:opacity-70 transition-opacity"
                                  title="Remove member"
                                >
                                  <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                </button>
                              )}
                            </div>
                          </div>
                          <hr className="border-brand-gray-light" />
                        </div>
                      ))
                    )}
                  </div>

                  {/* ── Card layout (tablet + mobile, <lg) ── */}
                  <div className="lg:hidden">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="w-8 h-8 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : sortedMembers.length === 0 ? (
                      <p className="font-body text-base text-brand-gray-med py-8 text-center">No members found.</p>
                    ) : (
                      sortedMembers.map((member) => (
                        <div key={member.id}>
                          <div className="py-4">
                            {/* Name + Last Assessment */}
                            <div className="flex justify-between items-start mb-3">
                              <div>
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Name</p>
                                <button onClick={() => setSelectedMember(member)} className="font-body font-bold text-lg text-brand-teal text-left hover:underline cursor-pointer">
                                  {member.first_name} {member.last_name}
                                </button>
                              </div>
                              <div className="text-right">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Last Assessment</p>
                                <p className="font-body font-bold text-lg text-brand-charcoal">
                                  {formatDate(member.last_assessment_date)}
                                </p>
                              </div>
                            </div>

                            {/* Gifts + Influencing Style */}
                            <div className="flex gap-4 mb-4">
                              <div className="flex-1 min-w-0">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Gifts</p>
                                <div className="flex gap-1 flex-wrap">
                                  {(member.top_gifts || []).map((g, i) => (
                                    <span key={i} className="inline-flex items-center justify-center h-8 px-3 bg-[rgba(167,185,211,0.5)] rounded-full font-body font-bold text-lg text-brand-charcoal">
                                      {g.short_code}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Influencing Style</p>
                                <div className="flex gap-1 flex-wrap">
                                  {(member.top_passions || []).map((p, i) => (
                                    <span key={i} className="inline-flex items-center justify-center h-8 px-4 bg-[rgba(227,162,162,0.5)] rounded-full font-body font-bold text-lg text-brand-charcoal">
                                      {p.name}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>

                            {/* Tablet buttons (md+): View Results + Make Admin side by side + trash */}
                            <div className="hidden md:flex items-center gap-3">
                              <button
                                onClick={() => handleViewResults(member)}
                                disabled={!hasResults(member)}
                                className={`h-[50px] flex-1 font-body font-bold text-lg rounded-xl transition-colors ${
                                  hasResults(member)
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                View Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                  className={`h-[50px] flex-1 font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                    member.is_admin
                                      ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                      : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                  }`}
                                >
                                  {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                </button>
                              )}
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => handleRemoveMember(member)}
                                  className="p-2 hover:opacity-70 transition-opacity shrink-0"
                                  title="Remove member"
                                >
                                  <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                </button>
                              )}
                            </div>

                            {/* Mobile buttons (<md): Results full-width, then Make Admin + trash right-aligned */}
                            <div className="md:hidden flex flex-col gap-2">
                              <button
                                onClick={() => handleViewResults(member)}
                                disabled={!hasResults(member)}
                                className={`h-[50px] w-full font-body font-bold text-lg rounded-xl transition-colors ${
                                  hasResults(member)
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <div className="flex items-center justify-end gap-2">
                                  <button
                                    onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                    className={`h-[50px] px-4 font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                      member.is_admin
                                        ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                        : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                    }`}
                                  >
                                    {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                  </button>
                                  <button
                                    onClick={() => handleRemoveMember(member)}
                                    className="p-2 hover:opacity-70 transition-opacity"
                                    title="Remove member"
                                  >
                                    <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                          <hr className="border-brand-gray-light" />
                        </div>
                      ))
                    )}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-3 mt-6">
                      {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => handlePageChange(page)}
                          className={`font-body font-bold text-lg transition-colors ${
                            page === currentPage ? 'text-brand-teal' : 'text-brand-charcoal hover:text-brand-teal'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                      {currentPage < totalPages && (
                        <>
                          <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            className="flex items-center gap-1 font-body font-bold text-lg text-brand-charcoal hover:text-brand-teal transition-colors"
                          >
                            Next
                            <img src={nextIcon} alt="" className="w-[7px] h-[12px]" />
                          </button>
                          <button
                            onClick={() => handlePageChange(totalPages)}
                            className="flex items-center gap-1 font-body font-bold text-lg text-brand-charcoal hover:text-brand-teal transition-colors"
                          >
                            Last
                            <img src={lastIcon} alt="" className="w-[14px] h-[12px]" />
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── MyImpact Members Tab ── */}
              {activeTab === 'myimpact' && (
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                  <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                    MyImpact — Users &nbsp;|&nbsp; Admin Dashboard
                  </h2>

                  {/* Search bar + Gold link button + Export — responsive */}
                  <div className="flex flex-col gap-3 mb-8">
                    <div className="flex gap-3">
                      <div className="relative flex-1 lg:max-w-[484px]">
                        <input
                          type="text"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          onKeyDown={handleSearchKeyDown}
                          placeholder="Search Member"
                          className="w-full h-[50px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 pr-10 font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60"
                        />
                        <img src={searchIcon} alt="" className="absolute right-3 top-1/2 -translate-y-1/2 w-[22px] h-[22px]" />
                      </div>
                      <button
                        onClick={handleSearch}
                        className="hidden md:flex items-center justify-center h-[50px] w-[119px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors shrink-0"
                      >
                        Search
                      </button>
                      <button
                        onClick={handleCopyLink}
                        className="hidden lg:flex items-center h-[50px] px-6 bg-brand-gold text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gold/90 transition-colors whitespace-nowrap"
                      >
                        Access Unique Assessment Link
                      </button>
                      <button
                        onClick={handleExportCSV}
                        disabled={isExporting}
                        className="hidden lg:flex items-center h-[50px] px-6 bg-brand-charcoal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-charcoal/90 transition-colors whitespace-nowrap disabled:opacity-50"
                      >
                        {isExporting ? 'Exporting...' : 'Export CSV'}
                      </button>
                    </div>
                    <button
                      onClick={handleSearch}
                      className="md:hidden h-[50px] w-[119px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                    >
                      Search
                    </button>
                    <button
                      onClick={handleCopyLink}
                      className="lg:hidden h-[50px] w-full bg-brand-gold text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gold/90 transition-colors"
                    >
                      Access Unique Assessment Link
                    </button>
                    <button
                      onClick={handleExportCSV}
                      disabled={isExporting}
                      className="lg:hidden h-[50px] w-full bg-brand-charcoal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-charcoal/90 transition-colors disabled:opacity-50"
                    >
                      {isExporting ? 'Exporting...' : 'Export CSV'}
                    </button>
                    {exportMsg && (
                      <p className={`font-body text-sm ${exportMsg.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                        {exportMsg}
                      </p>
                    )}
                  </div>

                  {/* ── Desktop table (lg+) ── */}
                  <div className="hidden lg:block overflow-x-auto">
                    <div className="grid grid-cols-[180px_130px_110px_110px_120px_1fr] gap-2 mb-2">
                      <button onClick={() => handleSort('name')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Name{sortIndicator('name')}</button>
                      <button onClick={() => handleSort('date')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Last Assessment{sortIndicator('date')}</button>
                      <button onClick={() => handleSort('character')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Character{sortIndicator('character')}</button>
                      <button onClick={() => handleSort('calling')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">Calling{sortIndicator('calling')}</button>
                      <button onClick={() => handleSort('myimpact')} className="font-body font-bold text-[16px] text-brand-gray-med uppercase text-left hover:text-brand-teal transition-colors cursor-pointer">MyImpact{sortIndicator('myimpact')}</button>
                      <span />
                    </div>
                    <hr className="border-brand-gray-light mb-2" />

                    {isLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="w-8 h-8 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : sortedMembers.length === 0 ? (
                      <p className="font-body text-base text-brand-gray-med py-8 text-center">No members found.</p>
                    ) : (
                      sortedMembers.map((member) => (
                        <div key={member.id}>
                          <div className="grid grid-cols-[180px_130px_110px_110px_120px_1fr] gap-2 items-center py-3">
                            <button onClick={() => setSelectedMember(member)} className="font-body font-bold text-lg text-brand-teal truncate text-left hover:underline cursor-pointer">
                              {member.first_name} {member.last_name}
                            </button>
                            <span className="font-body font-bold text-lg text-brand-charcoal">
                              {formatDate(member.last_assessment_date)}
                            </span>
                            <span className="font-body font-bold text-lg text-brand-charcoal">
                              {member.myimpact_character_score != null ? member.myimpact_character_score.toFixed(1) : '—'}
                            </span>
                            <span className="font-body font-bold text-lg text-brand-charcoal">
                              {member.myimpact_calling_score != null ? member.myimpact_calling_score.toFixed(1) : '—'}
                            </span>
                            <MyImpactScoreBadge score={member.myimpact_score} />
                            <div className="flex items-center gap-2 justify-end flex-wrap">
                              <button
                                onClick={() => {
                                  if (member.latest_myimpact_assessment_id) {
                                    navigate(`/myimpact-results?id=${member.latest_myimpact_assessment_id}`);
                                  }
                                }}
                                disabled={!member.latest_myimpact_assessment_id}
                                className={`h-[50px] w-[133px] font-body font-bold text-lg rounded-xl transition-colors ${
                                  member.latest_myimpact_assessment_id
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                  className={`h-[50px] w-[175px] font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                    member.is_admin
                                      ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                      : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                  }`}
                                >
                                  {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                </button>
                              )}
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => handleRemoveMember(member)}
                                  className="p-2 hover:opacity-70 transition-opacity"
                                  title="Remove member"
                                >
                                  <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                </button>
                              )}
                            </div>
                          </div>
                          <hr className="border-brand-gray-light" />
                        </div>
                      ))
                    )}
                  </div>

                  {/* ── Card layout (tablet + mobile, <lg) ── */}
                  <div className="lg:hidden">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="w-8 h-8 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : sortedMembers.length === 0 ? (
                      <p className="font-body text-base text-brand-gray-med py-8 text-center">No members found.</p>
                    ) : (
                      sortedMembers.map((member) => (
                        <div key={member.id}>
                          <div className="py-4">
                            {/* Name + Last Assessment */}
                            <div className="flex justify-between items-start mb-3">
                              <div>
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Name</p>
                                <button onClick={() => setSelectedMember(member)} className="font-body font-bold text-lg text-brand-teal text-left hover:underline cursor-pointer">
                                  {member.first_name} {member.last_name}
                                </button>
                              </div>
                              <div className="text-right">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Last Assessment</p>
                                <p className="font-body font-bold text-lg text-brand-charcoal">
                                  {formatDate(member.last_assessment_date)}
                                </p>
                              </div>
                            </div>

                            {/* Character + Calling + MyImpact scores */}
                            <div className="flex gap-4 mb-4">
                              <div className="flex-1">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Character</p>
                                <p className="font-body font-bold text-lg text-brand-charcoal">
                                  {member.myimpact_character_score != null ? member.myimpact_character_score.toFixed(1) : '—'}
                                </p>
                              </div>
                              <div className="flex-1">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">Calling</p>
                                <p className="font-body font-bold text-lg text-brand-charcoal">
                                  {member.myimpact_calling_score != null ? member.myimpact_calling_score.toFixed(1) : '—'}
                                </p>
                              </div>
                              <div className="flex-1">
                                <p className="font-body font-bold text-[16px] text-brand-gray-med uppercase mb-1">MyImpact</p>
                                <MyImpactScoreBadge score={member.myimpact_score} />
                              </div>
                            </div>

                            {/* Tablet buttons (md+) */}
                            <div className="hidden md:flex items-center gap-3">
                              <button
                                onClick={() => {
                                  if (member.latest_myimpact_assessment_id) {
                                    navigate(`/myimpact-results?id=${member.latest_myimpact_assessment_id}`);
                                  }
                                }}
                                disabled={!member.latest_myimpact_assessment_id}
                                className={`h-[50px] flex-1 font-body font-bold text-lg rounded-xl transition-colors ${
                                  member.latest_myimpact_assessment_id
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                View Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                  className={`h-[50px] flex-1 font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                    member.is_admin
                                      ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                      : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                  }`}
                                >
                                  {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                </button>
                              )}
                              {!member.is_primary_admin && !isReadOnly && (
                                <button
                                  onClick={() => handleRemoveMember(member)}
                                  className="p-2 hover:opacity-70 transition-opacity shrink-0"
                                  title="Remove member"
                                >
                                  <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                </button>
                              )}
                            </div>

                            {/* Mobile buttons (<md) */}
                            <div className="md:hidden flex flex-col gap-2">
                              <button
                                onClick={() => {
                                  if (member.latest_myimpact_assessment_id) {
                                    navigate(`/myimpact-results?id=${member.latest_myimpact_assessment_id}`);
                                  }
                                }}
                                disabled={!member.latest_myimpact_assessment_id}
                                className={`h-[50px] w-full font-body font-bold text-lg rounded-xl transition-colors ${
                                  member.latest_myimpact_assessment_id
                                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90 cursor-pointer'
                                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                                }`}
                              >
                                Results
                              </button>
                              {!member.is_primary_admin && !isReadOnly && (
                                <div className="flex items-center justify-end gap-2">
                                  <button
                                    onClick={() => toggleAdmin(member.id, member.role || 'member')}
                                    className={`h-[50px] px-4 font-body font-bold text-lg text-brand-charcoal rounded-xl transition-colors ${
                                      member.is_admin
                                        ? 'bg-brand-teal-light hover:bg-brand-teal-light/80'
                                        : 'bg-[#E3E3E3] hover:bg-[#d5d5d5]'
                                    }`}
                                  >
                                    {member.is_admin ? 'Remove Admin' : 'Make Admin'}
                                  </button>
                                  <button
                                    onClick={() => handleRemoveMember(member)}
                                    className="p-2 hover:opacity-70 transition-opacity"
                                    title="Remove member"
                                  >
                                    <img src={trashIcon} alt="Delete" className="w-[21px] h-[26px]" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                          <hr className="border-brand-gray-light" />
                        </div>
                      ))
                    )}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-3 mt-6">
                      {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => handlePageChange(page)}
                          className={`font-body font-bold text-lg transition-colors ${
                            page === currentPage ? 'text-brand-teal' : 'text-brand-charcoal hover:text-brand-teal'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                      {currentPage < totalPages && (
                        <>
                          <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            className="flex items-center gap-1 font-body font-bold text-lg text-brand-charcoal hover:text-brand-teal transition-colors"
                          >
                            Next
                            <img src={nextIcon} alt="" className="w-[7px] h-[12px]" />
                          </button>
                          <button
                            onClick={() => handlePageChange(totalPages)}
                            className="flex items-center gap-1 font-body font-bold text-lg text-brand-charcoal hover:text-brand-teal transition-colors"
                          >
                            Last
                            <img src={lastIcon} alt="" className="w-[14px] h-[12px]" />
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── Church Profile & Settings Tab ── */}
              {activeTab === 'settings' && (
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                  <h2 className="font-heading font-black text-[32px] text-brand-charcoal mb-6">
                    Church Profile &amp; Settings
                  </h2>

                  {settingsMsg && (
                    <div className="bg-green-50 border border-green-200 text-green-700 px-5 py-3 rounded-xl font-body text-base mb-4">
                      {settingsMsg}
                    </div>
                  )}
                  {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-3 rounded-xl font-body text-base mb-4">
                      {error}
                    </div>
                  )}

                  {/* Church Name */}
                  <label className="block font-body font-bold text-lg text-brand-charcoal mb-2">Church Name</label>
                  <input
                    type="text"
                    value={churchName}
                    onChange={(e) => setChurchName(e.target.value)}
                    placeholder="Church Name"
                    className="w-full h-[50px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body font-bold text-lg text-brand-charcoal mb-6"
                  />

                  {/* City + State */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <label className="block font-body font-bold text-lg text-brand-charcoal mb-2">City</label>
                      <input
                        type="text"
                        value={churchCity}
                        onChange={(e) => setChurchCity(e.target.value)}
                        placeholder="City"
                        className="w-full h-[50px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body font-bold text-lg text-brand-charcoal"
                      />
                    </div>
                    <div>
                      <label className="block font-body font-bold text-lg text-brand-charcoal mb-2">State</label>
                      <select
                        value={churchState}
                        onChange={(e) => setChurchState(e.target.value)}
                        className="w-full h-[50px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body font-bold text-lg text-brand-charcoal"
                      >
                        <option value="">Select State</option>
                        {US_STATES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <hr className="border-brand-gray-light my-6" />

                  {/* Administrators */}
                  <h3 className="font-body font-bold text-lg text-brand-charcoal mb-3">Administrators</h3>
                  {adminMembers.length > 0 ? (
                    <div className="space-y-2 mb-6">
                      {adminMembers.map((admin) => (
                        <div key={admin.id} className="flex items-center justify-between py-2">
                          <span className="font-body font-bold text-base text-brand-charcoal">
                            {admin.first_name} {admin.last_name}
                            {admin.is_primary_admin && (
                              <span className="ml-2 text-sm text-brand-gray-med">(Primary)</span>
                            )}
                          </span>
                          {!admin.is_primary_admin && !isReadOnly && (
                            <div className="flex items-center gap-3">
                              {user?.is_primary_admin && (
                                <button
                                  onClick={() => setTransferTarget(admin)}
                                  className="font-body text-sm font-bold text-brand-teal hover:underline"
                                  title="Transfer primary admin status"
                                >
                                  Make Primary
                                </button>
                              )}
                              <button
                                onClick={() => toggleAdmin(admin.id.toString(), admin.role || 'admin')}
                                className="p-1 hover:opacity-70 transition-opacity"
                                title="Remove admin"
                              >
                                <img src={trashIcon} alt="Remove" className="w-[18px] h-[22px]" />
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="font-body text-sm text-brand-gray-med mb-6">No other administrators</p>
                  )}

                  <hr className="border-brand-gray-light my-6" />

                  {/* Links */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <h3 className="font-body font-bold text-lg text-brand-charcoal mb-2">
                        Connect to Your Church Database
                      </h3>
                      <button className="h-[44px] px-5 bg-brand-teal-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-brand-teal-light/80 transition-colors">
                        Manage Connections
                      </button>
                    </div>
                    {user?.is_primary_admin && (
                      <div>
                        <h3 className="font-body font-bold text-lg text-brand-charcoal mb-2">
                          Subscription &amp; Billing
                        </h3>
                        <button
                          onClick={() => navigate('/admin/billing')}
                          className="h-[44px] px-5 bg-brand-teal-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                        >
                          Manage Payment Method
                        </button>
                      </div>
                    )}
                  </div>

                  <hr className="border-brand-gray-light my-6" />

                  {/* Save */}
                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveSettings}
                      disabled={isSaving || isReadOnly}
                      className="h-[50px] w-[219px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors disabled:opacity-50"
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}
        </section>
      </main>

      <Footer />

      {/* Transfer Primary Admin confirmation modal */}
      {transferTarget && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
            <h2 className="font-heading font-bold text-2xl text-brand-charcoal mb-2">
              Transfer Primary Admin
            </h2>
            <p className="font-body text-brand-gray-med text-sm mb-6">
              You are about to make <strong>{transferTarget.first_name} {transferTarget.last_name}</strong> the
              primary administrator of <strong>{churchSettings?.name}</strong>.
            </p>

            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-6 font-body text-sm text-amber-800 space-y-3">
              <div>
                <p className="font-bold mb-1">What changes for you:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>You become a secondary administrator</li>
                  <li>You lose access to billing and subscription management</li>
                  <li>You can no longer transfer primary status without their cooperation</li>
                </ul>
              </div>
              <div>
                <p className="font-bold mb-1">What changes for {transferTarget.first_name}:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>They gain full billing and subscription access</li>
                  <li>They can transfer primary status or cancel the subscription</li>
                </ul>
              </div>
            </div>

            <p className="font-body text-sm text-brand-gray-med mb-6">
              This requires <strong>{transferTarget.first_name}'s</strong> cooperation to reverse.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setTransferTarget(null)}
                className="flex-1 h-[48px] border border-brand-gray-light rounded-xl font-body font-bold text-brand-charcoal hover:bg-gray-50 transition-colors"
                disabled={isTransferring}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmTransfer}
                disabled={isTransferring}
                className="flex-1 h-[48px] bg-brand-teal text-white rounded-xl font-body font-bold hover:bg-brand-teal/90 disabled:opacity-50 transition-colors"
              >
                {isTransferring ? 'Transferring...' : 'Confirm Transfer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Member Detail Slide-in Panel ── */}
      {selectedMember && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setSelectedMember(null)}
          />
          <div className="fixed top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl z-50 flex flex-col overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-brand-gray-light">
              <h2 className="font-heading font-bold text-xl text-brand-charcoal">
                Member Details
              </h2>
              <button
                onClick={() => setSelectedMember(null)}
                className="text-brand-gray-med hover:text-brand-charcoal text-2xl font-bold leading-none"
                aria-label="Close panel"
              >
                &times;
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 px-6 py-6 space-y-5">
              <div>
                <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Name</p>
                <p className="font-body font-bold text-xl text-brand-charcoal">
                  {selectedMember.first_name} {selectedMember.last_name}
                </p>
              </div>

              <div>
                <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Email</p>
                <p className="font-body font-bold text-base text-brand-charcoal">
                  {selectedMember.email || '—'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Status</p>
                  <p className="font-body font-bold text-base text-brand-charcoal capitalize">
                    {selectedMember.status || '—'}
                  </p>
                </div>
                <div>
                  <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Role</p>
                  <p className="font-body font-bold text-base text-brand-charcoal capitalize">
                    {selectedMember.is_primary_admin ? 'Primary Admin' : selectedMember.is_admin ? 'Admin' : 'Member'}
                  </p>
                </div>
              </div>

              <div>
                <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Last Assessment</p>
                <p className="font-body font-bold text-base text-brand-charcoal">
                  {formatDate(selectedMember.last_assessment_date)}
                </p>
              </div>

              <hr className="border-brand-gray-light" />

              {/* GPS Data */}
              {(selectedMember.top_gifts?.length > 0 || selectedMember.top_passions?.length > 0) && (
                <div>
                  <p className="font-heading font-bold text-lg text-brand-teal mb-3">GPS Assessment</p>
                  <div className="space-y-3">
                    <div>
                      <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Gifts</p>
                      <div className="flex gap-1 flex-wrap">
                        {(selectedMember.top_gifts || []).map((g, i) => (
                          <span key={i} className="inline-flex items-center h-8 px-3 bg-[rgba(167,185,211,0.5)] rounded-full font-body font-bold text-base text-brand-charcoal">
                            {g.short_code || g.name}
                          </span>
                        ))}
                        {(!selectedMember.top_gifts || selectedMember.top_gifts.length === 0) && (
                          <span className="font-body text-brand-gray-med">—</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="font-body text-sm text-brand-gray-med uppercase mb-1">Influencing Style</p>
                      <div className="flex gap-1 flex-wrap">
                        {(selectedMember.top_passions || []).map((p, i) => (
                          <span key={i} className="inline-flex items-center h-8 px-4 bg-[rgba(227,162,162,0.5)] rounded-full font-body font-bold text-base text-brand-charcoal">
                            {p.name}
                          </span>
                        ))}
                        {(!selectedMember.top_passions || selectedMember.top_passions.length === 0) && (
                          <span className="font-body text-brand-gray-med">—</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* MyImpact Data */}
              {selectedMember.myimpact_score != null && (
                <div>
                  <p className="font-heading font-bold text-lg text-brand-teal mb-3">MyImpact Assessment</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center bg-brand-gray-lightest rounded-xl p-3">
                      <p className="font-heading font-black text-2xl text-brand-charcoal">
                        {selectedMember.myimpact_character_score?.toFixed(1) ?? '—'}
                      </p>
                      <p className="font-body text-xs text-brand-gray-med">Character</p>
                    </div>
                    <div className="text-center bg-brand-gray-lightest rounded-xl p-3">
                      <p className="font-heading font-black text-2xl text-brand-charcoal">
                        {selectedMember.myimpact_calling_score?.toFixed(1) ?? '—'}
                      </p>
                      <p className="font-body text-xs text-brand-gray-med">Calling</p>
                    </div>
                    <div className="text-center bg-brand-teal-light/30 rounded-xl p-3">
                      <p className="font-heading font-black text-2xl text-brand-teal">
                        {selectedMember.myimpact_score?.toFixed(0) ?? '—'}
                      </p>
                      <p className="font-body text-xs text-brand-gray-med">MyImpact</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-brand-gray-light space-y-3">
              <div className="flex gap-3">
                <button
                  onClick={() => handleExportMemberCSV(selectedMember)}
                  disabled={isMemberExporting}
                  className="flex-1 h-[44px] bg-brand-charcoal text-white font-body font-bold text-base rounded-xl hover:bg-brand-charcoal/90 transition-colors disabled:opacity-50"
                >
                  {isMemberExporting ? 'Exporting...' : 'Export CSV'}
                </button>
                <button
                  onClick={() => handlePrintMember(selectedMember)}
                  className="flex-1 h-[44px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                >
                  Print
                </button>
              </div>
              <button
                onClick={() => {
                  handleViewResults(selectedMember);
                  setSelectedMember(null);
                }}
                disabled={!hasResults(selectedMember)}
                className={`w-full h-[44px] font-body font-bold text-base rounded-xl transition-colors ${
                  hasResults(selectedMember)
                    ? 'bg-brand-teal text-white hover:bg-brand-teal/90'
                    : 'bg-brand-gray-light text-brand-gray-med cursor-not-allowed'
                }`}
              >
                View Full Results
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Export CSV Modal with Filters ── */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 max-h-[90vh] overflow-y-auto">
            <h2 className="font-heading font-bold text-2xl text-brand-charcoal mb-2">
              Export Member Data
            </h2>
            <p className="font-body text-sm text-brand-gray-med mb-6">
              Choose filters for your CSV export. Leave blank to export all data.
            </p>

            {/* Instrument filter */}
            <label className="block font-body font-bold text-base text-brand-charcoal mb-2">Assessment Type</label>
            <select
              value={exportInstrument}
              onChange={(e) => setExportInstrument(e.target.value)}
              className="w-full h-[44px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body font-bold text-base text-brand-charcoal mb-4"
            >
              <option value="">All Assessments</option>
              <option value="gps">GPS Only</option>
              <option value="myimpact">MyImpact Only</option>
            </select>

            {/* Date range */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block font-body font-bold text-base text-brand-charcoal mb-2">From Date</label>
                <input
                  type="date"
                  value={exportDateFrom}
                  onChange={(e) => setExportDateFrom(e.target.value)}
                  className="w-full h-[44px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body text-base text-brand-charcoal"
                />
              </div>
              <div>
                <label className="block font-body font-bold text-base text-brand-charcoal mb-2">To Date</label>
                <input
                  type="date"
                  value={exportDateTo}
                  onChange={(e) => setExportDateTo(e.target.value)}
                  className="w-full h-[44px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body text-base text-brand-charcoal"
                />
              </div>
            </div>

            {/* Export format (ChMS compatibility) */}
            <label className="block font-body font-bold text-base text-brand-charcoal mb-2">Export Format</label>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              className="w-full h-[44px] bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl px-4 font-body font-bold text-base text-brand-charcoal mb-6"
            >
              <option value="">Standard</option>
              <option value="planning_center">Planning Center Compatible</option>
              <option value="rock_rms">ROCK RMS Compatible</option>
            </select>

            {/* Filter summary */}
            <div className="bg-brand-gray-lightest rounded-xl px-4 py-3 mb-4 font-body text-sm text-brand-charcoal">
              <p className="font-bold mb-1">Export will include:</p>
              <ul className="list-disc list-inside space-y-0.5 text-brand-gray-med">
                <li>{exportInstrument ? (exportInstrument === 'gps' ? 'GPS' : 'MyImpact') + ' assessments only' : 'All assessment types'}</li>
                <li>{exportDateFrom || exportDateTo ? `Date range: ${exportDateFrom || 'beginning'} — ${exportDateTo || 'present'}` : 'All dates'}</li>
                <li>Format: {exportFormat === 'planning_center' ? 'Planning Center' : exportFormat === 'rock_rms' ? 'ROCK RMS' : 'Standard'}</li>
                <li>File: {churchSettings?.name?.replace(/\s+/g, '_') || 'Church'}_{exportInstrument ? exportInstrument.toUpperCase() : 'All'}_{new Date().toISOString().split('T')[0].replace(/-/g, '')}.csv</li>
              </ul>
            </div>

            {/* CSV Preview */}
            <div className="mb-6 border border-brand-gray-light rounded-xl overflow-hidden">
              <p className="font-body font-bold text-xs text-brand-charcoal px-3 py-2 bg-brand-gray-lightest border-b border-brand-gray-light">
                CSV Preview (sample row)
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-body">
                  <thead>
                    <tr className="bg-brand-gray-lightest/50">
                      {(exportFormat === 'planning_center'
                        ? ['first_name', 'last_name', 'email', 'campus', 'assessment_instrument', 'assessment_date', 'score_categories']
                        : exportFormat === 'rock_rms'
                        ? ['FirstName', 'LastName', 'Email', 'Campus', 'AssessmentInstrument', 'AssessmentDate', 'ScoreCategories']
                        : ['First Name', 'Last Name', 'Email', 'Church Name', 'Assessment Instrument', 'Assessment Date', 'Score Categories']
                      ).map((col) => (
                        <th key={col} className="px-2 py-1.5 text-left text-brand-charcoal whitespace-nowrap border-b border-brand-gray-light">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedMembers.length > 0 ? (
                      <tr className="text-brand-gray-med">
                        <td className="px-2 py-1.5 whitespace-nowrap">{sortedMembers[0].first_name || '—'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{sortedMembers[0].last_name || '—'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{sortedMembers[0].email || '—'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{churchSettings?.name || '—'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{exportInstrument === 'myimpact' ? 'MyImpact' : 'GPS'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{sortedMembers[0].last_assessment_date || '—'}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{sortedMembers[0].top_gifts?.[0]?.name || (sortedMembers[0].myimpact_score != null ? String(sortedMembers[0].myimpact_score) : '—')}</td>
                      </tr>
                    ) : (
                      <tr><td colSpan={7} className="px-2 py-1.5 text-brand-gray-med italic">No members to preview</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {exportMsg && (
              <p className={`font-body text-sm mb-4 ${exportMsg.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                {exportMsg}
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => { setShowExportModal(false); setExportMsg(''); }}
                className="flex-1 h-[48px] border border-brand-gray-light rounded-xl font-body font-bold text-brand-charcoal hover:bg-gray-50 transition-colors"
                disabled={isExporting}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmExport}
                disabled={isExporting}
                className="flex-1 h-[48px] bg-brand-teal text-white rounded-xl font-body font-bold hover:bg-brand-teal/90 disabled:opacity-50 transition-colors"
              >
                {isExporting ? 'Exporting...' : 'Download CSV'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
