import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useMaster, type ChurchMember } from '../context/MasterContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';
import tealArrowIcon from '../../Graphics for Dev/Icons/Dark Teal Arrow Circle Icon.svg';
import searchIcon from '../../Graphics for Dev/Icons/Charcoal Search Icon.svg';

type Tab = 'dashboard' | 'churches';

export function MasterDashboard() {
  const { user, logout } = useAuth();
  const {
    dashboardStats, fetchDashboardStats,
    churches, fetchChurches, toggleChurchStatus,
    transferPrimaryAdmin, fetchChurchMembers,
    totalChurchPages,
    isLoading, error, clearError,
  } = useMaster();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Churches tab state
  const [churchSearch, setChurchSearch] = useState('');
  const [churchPage, setChurchPage] = useState(1);
  const [expandedChurchId, setExpandedChurchId] = useState<string | null>(null);
  const [churchMembers, setChurchMembers] = useState<ChurchMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);

  useEffect(() => {
    fetchDashboardStats();
    fetchChurches();
  }, [fetchDashboardStats, fetchChurches]);

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

  const handleChurchSearch = () => {
    setChurchPage(1);
    fetchChurches(1, churchSearch);
  };

  const handleChurchPageChange = (page: number) => {
    setChurchPage(page);
    fetchChurches(page, churchSearch);
  };

  const handleToggleStatus = (churchId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'paused' ? 'active' : 'paused';
    toggleChurchStatus(churchId, newStatus);
  };

  const handleExpandChurch = async (churchId: string) => {
    if (expandedChurchId === churchId) {
      setExpandedChurchId(null);
      setChurchMembers([]);
      return;
    }
    setExpandedChurchId(churchId);
    setMembersLoading(true);
    try {
      const members = await fetchChurchMembers(churchId);
      setChurchMembers(members);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load members');
      setExpandedChurchId(null);
    } finally {
      setMembersLoading(false);
    }
  };

  const handleTransferPrimary = async (churchId: string, memberId: string, memberName: string) => {
    if (!window.confirm(`Transfer primary admin to ${memberName}? This will also transfer billing access.`)) return;
    try {
      await transferPrimaryAdmin(churchId, memberId);
      fetchChurches(churchPage, churchSearch);
      // Refresh expanded member list
      const members = await fetchChurchMembers(churchId);
      setChurchMembers(members);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to transfer primary admin');
    }
  };

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  // Chart data
  const gpsData = dashboardStats?.gps_assessments_monthly || [];
  const myimpactData = dashboardStats?.myimpact_assessments_monthly || [];
  const usersData = dashboardStats?.users_monthly || [];
  const orgsData = dashboardStats?.orgs_monthly || [];

  const sidebarItems: { key: Tab; label: string }[] = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'churches', label: 'Churches' },
  ];

  // Pagination
  const renderPagination = () => {
    if (totalChurchPages <= 1) return null;
    const pages = [];
    const maxVisible = 5;
    const start = Math.max(1, churchPage - Math.floor(maxVisible / 2));
    const end = Math.min(totalChurchPages, start + maxVisible - 1);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return (
      <div className="flex items-center justify-center gap-2 mt-6">
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => handleChurchPageChange(p)}
            className={`w-10 h-10 rounded-lg font-body font-bold text-base transition-colors ${
              p === churchPage
                ? 'bg-brand-teal text-white'
                : 'bg-white text-brand-charcoal border border-brand-gray-light hover:bg-brand-gray-lightest'
            }`}
          >
            {p}
          </button>
        ))}
        {churchPage < totalChurchPages && (
          <>
            <button
              onClick={() => handleChurchPageChange(churchPage + 1)}
              className="px-3 h-10 rounded-lg font-body font-bold text-base text-brand-charcoal border border-brand-gray-light hover:bg-brand-gray-lightest transition-colors"
            >
              Next
            </button>
            <button
              onClick={() => handleChurchPageChange(totalChurchPages)}
              className="px-3 h-10 rounded-lg font-body font-bold text-base text-brand-charcoal border border-brand-gray-light hover:bg-brand-gray-lightest transition-colors"
            >
              Last
            </button>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        {/* Header */}
        <section className="max-w-[1230px] mx-auto px-6 pt-12 pb-6">
          <div className="flex justify-between items-start">
            <h1 className="font-heading text-3xl md:text-[48px] md:leading-[55px] text-brand-charcoal">
              <span className="font-medium">Welcome to Your Super Admin Account,</span>
              <br />
              <span className="font-black">{firstName}</span>
            </h1>

            {/* Gold hamburger menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-2 hover:opacity-80 transition-opacity"
                aria-label="Menu"
              >
                <img
                  src={menuOpen ? goldXIcon : goldMenuIcon}
                  alt=""
                  className="w-[50px] h-auto"
                />
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-[307px] bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] z-50">
                  <nav className="py-1">
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/account'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      Account
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/update-password'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      Update Password
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest rounded-b-xl transition-colors"
                    >
                      Logout
                    </button>
                  </nav>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Body: Sidebar + Content */}
        <section className="max-w-[1230px] mx-auto px-6 pb-16 flex flex-col md:flex-row gap-8">
          {/* Left Sidebar Nav */}
          <aside className="w-full md:w-[280px] shrink-0">
            <nav className="space-y-2">
              {sidebarItems.map((item) => (
                <button
                  key={item.key}
                  onClick={() => setActiveTab(item.key)}
                  className={`flex items-center gap-3 w-full text-left py-2 px-1 transition-colors ${
                    activeTab === item.key
                      ? 'font-heading font-black text-brand-teal text-2xl'
                      : 'font-heading font-medium text-brand-charcoal text-2xl hover:text-brand-teal'
                  }`}
                >
                  {activeTab === item.key && (
                    <img src={tealArrowIcon} alt="" className="w-[34px] h-[34px]" />
                  )}
                  {item.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Right Content Area */}
          <div className="flex-1 min-w-0">
            {/* ── Dashboard Tab ── */}
            {activeTab === 'dashboard' && (
              <div className="space-y-8">
                {/* MyImpact Average Score Card */}
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-8">
                  <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal text-center mb-8">
                    MyImpact Average Score
                  </h2>
                  <div className="flex items-center justify-center gap-4 flex-wrap">
                    {/* Character */}
                    <div className="text-center">
                      <div className="bg-brand-gray-lightest border-4 border-brand-teal-light rounded-md h-[54px] w-[156px] flex items-center justify-center">
                        <span className="font-heading font-medium text-2xl text-brand-teal">
                          {dashboardStats?.avg_character_score ?? '—'}
                        </span>
                      </div>
                      <p className="font-heading font-medium text-base text-brand-charcoal uppercase mt-2">Character</p>
                    </div>
                    <span className="font-heading font-medium text-[32px] text-brand-charcoal">&times;</span>
                    {/* Calling */}
                    <div className="text-center">
                      <div className="bg-brand-gray-lightest border-4 border-brand-teal-light rounded-md h-[54px] w-[156px] flex items-center justify-center">
                        <span className="font-heading font-medium text-2xl text-brand-teal">
                          {dashboardStats?.avg_calling_score ?? '—'}
                        </span>
                      </div>
                      <p className="font-heading font-medium text-base text-brand-charcoal uppercase mt-2">Calling</p>
                    </div>
                    <span className="font-heading font-medium text-[32px] text-brand-charcoal">=</span>
                    {/* Impact */}
                    <div className="text-center">
                      <div className="bg-brand-gray-lightest border-4 border-brand-teal-light rounded-md h-[54px] w-[156px] flex items-center justify-center">
                        <span className="font-heading font-medium text-2xl text-brand-teal">
                          {dashboardStats?.avg_myimpact_score ?? '—'}
                        </span>
                      </div>
                      <p className="font-heading font-medium text-base text-brand-charcoal uppercase mt-2">Impact</p>
                    </div>
                  </div>
                </div>

                {/* Charts 2×2 Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* GPS Completed Assessments */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <h3 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-4">
                      GPS Completed Assessments
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={gpsData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e3e3e3" />
                        <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <YAxis tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <Tooltip />
                        <Line
                          type="monotone"
                          dataKey="count"
                          stroke="#f7a824"
                          strokeWidth={2}
                          dot={{ fill: '#f7a824', r: 3.5 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* MyImpact Completed Assessments */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <h3 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-4">
                      MyImpact Completed Assessments
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={myimpactData.length > 0 ? myimpactData : gpsData.map(d => ({ ...d, count: 0 }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e3e3e3" />
                        <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <YAxis tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <Tooltip />
                        <Line
                          type="monotone"
                          dataKey="count"
                          stroke="#88c0c3"
                          strokeWidth={2}
                          dot={{ fill: '#88c0c3', r: 3.5 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Total Users */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <h3 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-4">
                      Total Users
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={usersData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e3e3e3" />
                        <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <YAxis tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#a7b9d3" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Total Organizations */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <h3 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-4">
                      Total Organizations
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={orgsData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e3e3e3" />
                        <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <YAxis tick={{ fontSize: 12, fill: '#3f4644' }} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#e3a2a2" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}

            {/* ── Churches Tab ── */}
            {activeTab === 'churches' && (
              <div>
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-4 flex justify-between items-center">
                    <span className="font-body">{error}</span>
                    <button onClick={clearError} className="text-red-500 hover:text-red-700 font-bold text-xl">&times;</button>
                  </div>
                )}

                {/* Single card wrapping title + search + table + pagination */}
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-8">
                  {/* Title */}
                  <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                    Churches
                  </h2>

                  {/* Search Bar */}
                  <div className="flex gap-3 mb-8">
                    <div className="relative flex-1 max-w-[484px]">
                      <img
                        src={searchIcon}
                        alt=""
                        className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 opacity-60"
                      />
                      <input
                        type="text"
                        placeholder="Search Church"
                        value={churchSearch}
                        onChange={(e) => setChurchSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleChurchSearch()}
                        className="w-full h-[50px] pl-6 pr-12 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-[rgba(63,70,68,0.66)] focus:outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20 transition-colors"
                      />
                    </div>
                    <button
                      onClick={handleChurchSearch}
                      className="h-[50px] w-[119px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                    >
                      Search
                    </button>
                  </div>

                  {/* Table */}
                  {isLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <p className="font-body text-lg text-brand-gray-med">Loading churches...</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[700px]">
                        <thead>
                          <tr className="border-b border-brand-gray-light">
                            <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-0 py-4">
                              Church Name
                            </th>
                            <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                              # of Users
                            </th>
                            <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                              Location
                            </th>
                            <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                              Admin
                            </th>
                            <th className="px-4 py-4" />
                          </tr>
                        </thead>
                        <tbody>
                          {churches.length === 0 ? (
                            <tr>
                              <td colSpan={5} className="px-0 py-12 text-center font-body text-lg text-brand-gray-med">
                                No churches found
                              </td>
                            </tr>
                          ) : (
                            churches.map((church) => {
                              const primaryAdmin = church.admins.find((a) => a.is_primary);
                              const isExpanded = expandedChurchId === church.id;

                              return (
                                <React.Fragment key={church.id}>
                                  {/* Main row */}
                                  <tr className={`border-b border-brand-gray-light last:border-b-0 ${isExpanded ? 'bg-brand-gray-lightest/50' : ''}`}>
                                    <td className="px-0 py-5 font-body font-bold text-lg text-brand-charcoal">
                                      <button
                                        onClick={() => handleExpandChurch(church.id)}
                                        className="flex items-center gap-2 hover:text-brand-teal transition-colors text-left"
                                      >
                                        <span className={`text-sm transition-transform ${isExpanded ? 'rotate-90' : ''}`}>&#9654;</span>
                                        {church.name}
                                      </button>
                                    </td>
                                    <td className="px-4 py-5 font-body font-bold text-lg text-brand-charcoal">
                                      {church.member_count}
                                    </td>
                                    <td className="px-4 py-5 font-body font-bold text-lg text-brand-charcoal">
                                      {[church.city, church.state].filter(Boolean).join(', ') || '—'}
                                    </td>
                                    <td className="px-4 py-5 font-body text-lg text-brand-charcoal">
                                      {primaryAdmin ? (
                                        <span className="inline-flex items-center">
                                          <span className="font-black">{primaryAdmin.name}</span>
                                          <span className="ml-1.5 text-xs font-body font-bold text-brand-teal bg-brand-teal/10 px-1.5 py-0.5 rounded">
                                            Primary
                                          </span>
                                        </span>
                                      ) : (
                                        <span className="text-sm font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded">
                                          No Primary Admin
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-5">
                                      {church.status === 'paused' ? (
                                        <button
                                          onClick={() => handleToggleStatus(church.id, church.status)}
                                          className="w-[129px] h-[50px] bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                                        >
                                          Restore
                                        </button>
                                      ) : (
                                        <button
                                          onClick={() => handleToggleStatus(church.id, church.status)}
                                          className="w-[129px] h-[50px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                                        >
                                          Pause
                                        </button>
                                      )}
                                    </td>
                                  </tr>

                                  {/* Expanded members row */}
                                  {isExpanded && (
                                    <tr>
                                      <td colSpan={5} className="px-0 py-0 bg-brand-gray-lightest/30">
                                        <div className="px-6 py-4">
                                          <h4 className="font-heading font-bold text-base text-brand-teal uppercase mb-3">
                                            Members
                                          </h4>
                                          {membersLoading ? (
                                            <p className="font-body text-sm text-brand-gray-med py-2">Loading members...</p>
                                          ) : churchMembers.length === 0 ? (
                                            <p className="font-body text-sm text-brand-gray-med py-2">No active members</p>
                                          ) : (
                                            <div className="space-y-1">
                                              {churchMembers.map((member) => (
                                                <div
                                                  key={member.id}
                                                  className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white/60 transition-colors"
                                                >
                                                  <div className="flex items-center gap-3">
                                                    <span className="font-body font-bold text-base text-brand-charcoal">
                                                      {member.name}
                                                    </span>
                                                    <span className="font-body text-sm text-brand-gray-med">
                                                      {member.email}
                                                    </span>
                                                  </div>
                                                  <div className="flex items-center gap-3">
                                                    <span className={`text-xs font-body font-bold px-2 py-0.5 rounded ${
                                                      member.role === 'admin'
                                                        ? 'text-brand-teal bg-brand-teal/10'
                                                        : 'text-brand-gray-med bg-brand-gray-light'
                                                    }`}>
                                                      {member.role === 'admin' ? 'Admin' : 'Member'}
                                                    </span>
                                                    {member.is_primary_admin ? (
                                                      <span className="text-xs font-body font-bold text-brand-teal bg-brand-teal/10 px-2 py-0.5 rounded">
                                                        Primary
                                                      </span>
                                                    ) : (
                                                      <button
                                                        onClick={() => handleTransferPrimary(church.id, member.id, member.name)}
                                                        className="text-xs font-body font-bold text-brand-gold hover:text-brand-gold/80 underline transition-colors"
                                                      >
                                                        Make Primary
                                                      </button>
                                                    )}
                                                  </div>
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                        </div>
                                      </td>
                                    </tr>
                                  )}
                                </React.Fragment>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {renderPagination()}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
