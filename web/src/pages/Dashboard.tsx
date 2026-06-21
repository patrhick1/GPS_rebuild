import { useEffect, useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { OnboardingGuide } from '../components/OnboardingGuide';
import { useTranslation } from '../hooks/useTranslation';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';

export function Dashboard() {
  const { user, logout } = useAuth();
  const { summary, history, myimpactHistory, fetchSummary, fetchHistory, fetchMyImpactHistory, isLoading, error, compareAssessments, deleteAssessment } = useDashboard();
  const { t, isEs } = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Onboarding state — show guide for first-time users (no assessments taken yet)
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (
      summary &&
      summary.stats.total_assessments === 0 &&
      history.length === 0 &&
      myimpactHistory.length === 0 &&
      !user?.onboarding_completed
    ) {
      setShowOnboarding(true);
    }
  }, [summary, history, myimpactHistory, user?.onboarding_completed]);

  const dismissOnboarding = async () => {
    setShowOnboarding(false);
    try {
      await api.post('/auth/onboarding-complete');
    } catch {
      // Non-critical — guide won't reappear if assessments exist anyway
    }
  };

  // Re-take confirmation state
  const [retakeModalOpen, setRetakeModalOpen] = useState(false);
  const [retakeType, setRetakeType] = useState<'gps' | 'myimpact'>('gps');
  const [retakeDate, setRetakeDate] = useState('');

  // Comparison state
  const [compareSelected, setCompareSelected] = useState<string[]>([]);
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [compareError, setCompareError] = useState('');
  const [compareLoading, setCompareLoading] = useState(false);

  const toggleCompareSelect = (id: string) => {
    setComparisonResult(null);
    setCompareError('');
    setCompareSelected(prev => {
      if (prev.includes(id)) return prev.filter(i => i !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleCompare = async () => {
    if (compareSelected.length !== 2) return;
    setCompareLoading(true);
    setCompareError('');
    try {
      const result = await compareAssessments(compareSelected[0], compareSelected[1]);
      setComparisonResult(result);
    } catch {
      setCompareError('Failed to load comparison. Please try again.');
    } finally {
      setCompareLoading(false);
    }
  };

  const handleDeleteAssessment = async (id: string) => {
    // Soft delete — the row stays in the DB with deleted_at set, but
    // user-facing GETs filter it out. Confirm before firing to avoid
    // accidental clicks; window.confirm is the lightest UX consistent
    // with the rest of the dashboard (Sherri can ask for a styled modal
    // if she wants more friction later).
    if (!window.confirm(t('Delete this assessment? You can ask an admin to recover it later if needed.'))) {
      return;
    }
    try {
      await deleteAssessment(id);
      // Drop the selection if the deleted row was queued for compare
      setCompareSelected((prev) => prev.filter((sid) => sid !== id));
      setComparisonResult(null);
    } catch {
      // Non-fatal: leave the row in place if the API call failed
    }
  };

  // Build a unified delta table from a GPS comparison result
  const buildDeltaRows = (result: any) => {
    const a1 = result.assessment_1;
    const a2 = result.assessment_2;
    if (!a1 || !a2) return [];
    const map1: Record<string, number> = {};
    const map2: Record<string, number> = {};
    a1.gifts.forEach((g: any) => { map1[g.name] = g.score; });
    a2.gifts.forEach((g: any) => { map2[g.name] = g.score; });
    const names = Array.from(new Set([...Object.keys(map1), ...Object.keys(map2)]));
    return names
      .map(name => ({ name, s1: map1[name] ?? 0, s2: map2[name] ?? 0, delta: (map2[name] ?? 0) - (map1[name] ?? 0) }))
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  };

  // ── MyImpact comparison: parallel state to GPS. Keeping the two
  // pools separate is cleaner UX than one pool that switches type
  // mid-selection, and matches the API's "both must share
  // instrument_type" guard.
  const [miCompareSelected, setMiCompareSelected] = useState<string[]>([]);
  const [miComparisonResult, setMiComparisonResult] = useState<any>(null);
  const [miCompareError, setMiCompareError] = useState('');
  const [miCompareLoading, setMiCompareLoading] = useState(false);

  const toggleMiCompareSelect = (id: string) => {
    setMiComparisonResult(null);
    setMiCompareError('');
    setMiCompareSelected(prev => {
      if (prev.includes(id)) return prev.filter(i => i !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleMiCompare = async () => {
    if (miCompareSelected.length !== 2) return;
    setMiCompareLoading(true);
    setMiCompareError('');
    try {
      const result = await compareAssessments(miCompareSelected[0], miCompareSelected[1]);
      setMiComparisonResult(result);
    } catch {
      setMiCompareError('Failed to load comparison. Please try again.');
    } finally {
      setMiCompareLoading(false);
    }
  };

  // MyImpact dimension labels — same source used on the wizard / results
  // page. Wrapping in t() so Spanish picks up existing keys.
  const buildMiDimensionRows = (result: any) => {
    const m1 = result?.myimpact_1;
    const m2 = result?.myimpact_2;
    if (!m1 || !m2) return { character: [], calling: [] };
    const characterLabels: Array<{ key: string; label: string }> = [
      { key: 'loving', label: t('Loving') },
      { key: 'joyful', label: t('Joyful') },
      { key: 'peaceful', label: t('Peaceful') },
      { key: 'patient', label: t('Patient') },
      { key: 'kind', label: t('Kind') },
      { key: 'good', label: t('Good') },
      { key: 'faithful', label: t('Faithful') },
      { key: 'gentle', label: t('Gentle') },
      { key: 'self_controlled', label: t('Self-Controlled') },
    ];
    const callingLabels: Array<{ key: string; label: string }> = [
      { key: 'know_gifts', label: t('I can name my top 3 Spiritual Gifts') },
      { key: 'know_people', label: t('I know the people/causes God wants me to serve') },
      { key: 'using_gifts', label: t('I am using my gifts to serve others') },
      { key: 'see_impact', label: t('I see God making a difference through me') },
      { key: 'experience_joy', label: t('I experience joy in serving others') },
      { key: 'pray_regularly', label: t('I regularly pray for people around me') },
      { key: 'see_movement', label: t('I see people move toward faith') },
      { key: 'receive_support', label: t('I receive support in my calling') },
    ];
    const rowFor = (dims: Array<{ key: string; label: string }>, src1: any, src2: any) =>
      dims.map(({ key, label }) => {
        const s1 = src1?.[key] ?? 0;
        const s2 = src2?.[key] ?? 0;
        return { name: label, s1, s2, delta: s2 - s1 };
      });
    return {
      character: rowFor(characterLabels, m1.character, m2.character),
      calling: rowFor(callingLabels, m1.calling, m2.calling),
    };
  };

  useEffect(() => {
    fetchSummary();
    fetchHistory();
    fetchMyImpactHistory();
  }, [fetchSummary, fetchHistory, fetchMyImpactHistory]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const firstName = summary?.user.first_name || user?.first_name || 'User';

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
  };

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  const handleStartAssessment = (type: 'gps' | 'myimpact') => {
    const items = type === 'gps' ? history : myimpactHistory;
    const lastCompleted = items.find(a => a.status === 'completed');
    if (lastCompleted?.completed_at) {
      setRetakeType(type);
      setRetakeDate(formatDate(lastCompleted.completed_at));
      setRetakeModalOpen(true);
    } else {
      navigate(type === 'gps' ? '/assessment' : '/myimpact');
    }
  };

  if (isLoading && !summary) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">{t('Loading dashboard...')}</p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {showOnboarding && (
        <OnboardingGuide firstName={firstName} onDismiss={dismissOnboarding} />
      )}

      <main className="flex-1 bg-white">
        {error && (
          <div className="max-w-[1230px] mx-auto px-6 pt-6">
            <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-3 rounded-xl font-body text-base">
              {error}
            </div>
          </div>
        )}

        {/* ── Welcome + Actions Section ── */}
        <section className="max-w-[1230px] mx-auto px-6 pt-12 pb-8">
          <div className="flex justify-between items-start">
            {/* Greeting */}
            <h1 className="font-heading text-3xl md:text-[48px] md:leading-[55px] text-brand-charcoal">
              <span className="font-medium">{t('Welcome to Your Dashboard,')}</span>
              <br />
              <span className="font-black">{firstName}</span>
            </h1>

            {/* Gold hamburger / X menu toggle */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-2 hover:opacity-80 transition-opacity"
                aria-label="Dashboard menu"
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
                      onClick={() => { setMenuOpen(false); document.getElementById('gps-section')?.scrollIntoView({ behavior: 'smooth' }); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {t('GPS Assessments')}
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); document.getElementById('myimpact-section')?.scrollIntoView({ behavior: 'smooth' }); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {t('MyImpact Assessments')}
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/account'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {t('Account')}
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/update-password'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {t('Update Password')}
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    {/* Locale toggle — Chelsie 2026-06-17: needs to live in
                       the page hamburger on both mobile and desktop, not
                       just the footer. */}
                    <button
                      onClick={() => { setMenuOpen(false); navigate(isEs ? '/update-locale?locale=en' : '/update-locale?locale=es'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-teal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {isEs ? 'In English?' : '¿En español?'}
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest rounded-b-xl transition-colors"
                    >
                      {t('Logout')}
                    </button>
                  </nav>
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mt-6 max-w-[732px]">
            {t(
              'Welcome {firstName}! Below are the results of your GPS and MyImpact assessments with their current level of completion. Click to continue with or to review the results of that particular assessment. You can take as many assessments as you wish.',
              { firstName },
            )}
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 mt-8">
            <button
              onClick={() => handleStartAssessment('gps')}
              className="h-[50px] px-10 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
            >
              {t('Take New GPS Assessment')}
            </button>
            <button
              onClick={() => handleStartAssessment('myimpact')}
              className="h-[50px] px-10 bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
            >
              {t('Take New MyImpact Assessment')}
            </button>
          </div>

          {/* Church Linking Prompt */}
          {!summary?.organization && user?.role !== 'admin' && user?.role !== 'master' && (
            summary?.pending_organization?.status === 'pending' ? (
              <div className="mt-8 bg-brand-gray-lightest border border-brand-gray-light rounded-xl p-6 flex items-center gap-3">
                <span className="inline-block w-3 h-3 rounded-full bg-yellow-400 shrink-0" />
                <p className="font-body font-bold text-base text-brand-charcoal">
                  {(() => {
                    const tpl = t('Your request to join {orgName} is awaiting approval.');
                    const [before, after] = tpl.split('{orgName}');
                    return (
                      <>
                        {before}
                        <span className="text-brand-teal">{summary.pending_organization.name}</span>
                        {after}
                      </>
                    );
                  })()}
                </p>
              </div>
            ) : (
              <div className="mt-8 bg-brand-gray-lightest border border-brand-gray-light rounded-xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <p className="font-heading font-bold text-lg text-brand-charcoal">
                    {t('Link My Assessment Results to a Church')}
                  </p>
                  <p className="font-body text-sm text-brand-gray-med mt-1">
                    {t('Search for your church, submit a request, and get connected once approved.')}
                  </p>
                </div>
                <button
                  onClick={() => navigate('/account#church-linking')}
                  className="shrink-0 h-[44px] px-6 bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 transition-colors"
                >
                  {t('Find My Church')}
                </button>
              </div>
            )
          )}

          {/* Upgrade / Admin link */}
          {user?.role === 'admin' || user?.role === 'master' ? (
            <p className="font-body font-bold text-base md:text-xl text-brand-charcoal mt-8">
              <Link
                to={user?.role === 'master' ? '/master' : '/admin'}
                className="font-black text-brand-teal underline hover:text-brand-teal/80 transition-colors"
              >
                {t('Go to Admin Dashboard')}
              </Link>
            </p>
          ) : (
            <p className="font-body font-bold text-base md:text-xl text-brand-charcoal mt-8">
              {t("Want to access toolkit resources and manage your church's assessment results?")}{' '}
              {t('Get the Calling Development Toolkit, which includes Church Admin access to the Disciples Made Impact Dashboard.')}{' '}
              <Link
                to="/upgrade"
                className="font-black text-brand-teal underline hover:text-brand-teal/80 transition-colors"
              >
                {t('Get Toolkit Access')}
              </Link>
            </p>
          )}
        </section>

        {/* ── GPS Assessments Section ── */}
        <section id="gps-section" className="max-w-[1230px] mx-auto px-6 py-8">
          <h2 className="font-heading font-medium text-2xl md:text-[32px] md:leading-[41px] text-brand-teal mb-4">
            {t('GPS Assessments')}
          </h2>

          <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] overflow-hidden">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6">
                <p className="font-body text-lg text-brand-gray-med mb-4">
                  {t('No GPS assessments yet. Take your first one!')}
                </p>
                <button
                  onClick={() => navigate('/assessment')}
                  className="h-[50px] px-10 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                >
                  {t('Start GPS Assessment')}
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto relative">
                {/* Narrow-viewport scroll hint — Sherri 2026-06-16: users
                   couldn't tell the assessment table was horizontally
                   scrollable on mobile. */}
                <p className="md:hidden text-right text-xs italic text-brand-gray-med px-3 py-1">
                  → {t('scroll for more')}
                </p>
                <table className="w-full min-w-[800px]">
                  <thead>
                    <tr className="border-b border-brand-gray-light">
                      <th className="px-6 py-4 w-10" />
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-6 py-4">
                        {t('Started')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Completed')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Progress')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Gifts')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Passion')}
                      </th>
                      <th className="px-4 py-4" />
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr key={item.id} className="border-b border-brand-gray-light last:border-b-0">
                        {/* Compare checkbox */}
                        <td className="px-6 py-5">
                          {item.status === 'completed' && (
                            <input
                              type="checkbox"
                              checked={compareSelected.includes(item.id)}
                              onChange={() => toggleCompareSelect(item.id)}
                              className="w-4 h-4 accent-brand-teal cursor-pointer"
                              aria-label="Select for comparison"
                            />
                          )}
                        </td>
                        {/* Started */}
                        <td className="px-6 py-5 font-body font-bold text-lg text-brand-charcoal">
                          {formatDate(item.created_at)}
                        </td>

                        {/* Completed */}
                        <td className="px-4 py-5 font-body font-bold text-lg text-brand-charcoal">
                          {item.status === 'completed' ? formatDate(item.completed_at) : ''}
                        </td>

                        {/* Progress */}
                        <td className="px-4 py-5">
                          <div className="flex items-center gap-2">
                            <span className="font-body font-bold text-lg text-brand-charcoal">
                              {item.progress_percentage}%
                            </span>
                            <div className="w-[156px] h-4 bg-brand-gray-lightest rounded-full overflow-hidden">
                              <div
                                className="h-full bg-brand-gold rounded-full transition-all duration-300"
                                style={{ width: `${item.progress_percentage}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Gifts */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' && item.top_gifts.length > 0 ? (
                            <div className="flex gap-2">
                              {item.top_gifts.map((gift, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center justify-center px-3 h-8 bg-brand-purple/50 rounded-full font-body font-bold text-base text-brand-charcoal whitespace-nowrap"
                                >
                                  {(isEs && gift.name_es) || gift.name}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              {t('incomplete')}
                            </span>
                          )}
                        </td>

                        {/* Passion */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' && item.top_passions.length > 0 ? (
                            <div className="flex gap-2">
                              {item.top_passions.map((passion, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center justify-center px-4 h-8 bg-brand-pink/50 rounded-full font-body font-bold text-lg text-brand-charcoal"
                                >
                                  {(isEs && passion.name_es) || passion.name}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              {t('incomplete')}
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="px-4 py-5">
                          <div className="flex items-center gap-2">
                            {item.status === 'completed' ? (
                              <button
                                onClick={() => navigate(`/assessment-results?id=${item.id}`)}
                                className="w-[175px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                              >
                                {t('View Results')}
                              </button>
                            ) : (
                              <button
                                onClick={() => navigate(`/assessment?continue=${item.id}`)}
                                className="w-[175px] h-[50px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                              >
                                {t('Continue')}
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteAssessment(item.id)}
                              title={t('Delete assessment')}
                              aria-label={t('Delete assessment')}
                              className="w-10 h-10 flex items-center justify-center text-brand-gray-med hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                <path d="M10 11v6M14 11v6" />
                                <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Compare controls */}
          {compareSelected.length > 0 && (
            <div className="mt-4 flex items-center gap-4">
              <span className="font-body text-base text-brand-gray-med">
                {compareSelected.length === 1 ? 'Select one more to compare' : '2 assessments selected'}
              </span>
              <button
                onClick={handleCompare}
                disabled={compareSelected.length !== 2 || compareLoading}
                className="h-10 px-6 bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {compareLoading ? 'Loading…' : 'Compare'}
              </button>
              <button
                onClick={() => { setCompareSelected([]); setComparisonResult(null); setCompareError(''); }}
                className="h-10 px-6 border border-brand-gray-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-brand-gray-lightest transition-colors"
              >
                Clear
              </button>
            </div>
          )}

          {compareError && (
            <p className="mt-3 font-body text-sm text-red-600">{compareError}</p>
          )}

          {/* Delta comparison panel */}
          {comparisonResult && (
            <div className="mt-6 border border-brand-gray-light rounded-xl overflow-hidden">
              <div className="bg-brand-teal/10 px-6 py-3 flex items-center justify-between">
                <h3 className="font-heading font-bold text-lg text-brand-charcoal">
                  Score Comparison&ensp;
                  <span className="font-body font-normal text-sm text-brand-gray-med">
                    {new Date(comparisonResult.assessment_1.completed_at).toLocaleDateString()}
                    {' → '}
                    {new Date(comparisonResult.assessment_2.completed_at).toLocaleDateString()}
                  </span>
                </h3>
                <button
                  onClick={() => setComparisonResult(null)}
                  className="text-brand-gray-med hover:text-brand-charcoal text-xl font-bold leading-none"
                  aria-label="Close comparison"
                >
                  &times;
                </button>
              </div>

              <div className="px-6 py-4">
                <h4 className="font-body font-bold text-base text-brand-gray-med uppercase mb-3">Spiritual Gifts</h4>
                <div className="space-y-2">
                  {buildDeltaRows(comparisonResult).map(({ name, s1, s2, delta }) => (
                    <div key={name} className="flex items-center gap-3">
                      <span className="w-40 font-body font-bold text-base text-brand-charcoal truncate">{name}</span>
                      <span className="font-body text-base text-brand-gray-med">{s1} → {s2}</span>
                      {delta !== 0 && (
                        <span className={`font-body font-bold text-base ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {delta > 0 ? `+${delta}` : delta}
                        </span>
                      )}
                      {delta === 0 && (
                        <span className="font-body text-base text-brand-gray-med">—</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>

        {/* ── MyImpact Assessments Section ── */}
        <section id="myimpact-section" className="max-w-[1230px] mx-auto px-6 pt-4 pb-16">
          <h2 className="font-heading font-medium text-2xl md:text-[32px] md:leading-[41px] text-brand-teal mb-4">
            {t('MyImpact Assessments')}
          </h2>

          <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] overflow-hidden">
            {myimpactHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6">
                <p className="font-body text-lg text-brand-gray-med mb-4">
                  {t('No MyImpact assessments yet. Take your first one!')}
                </p>
                <button
                  onClick={() => navigate('/myimpact')}
                  className="h-[50px] px-10 bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                >
                  {t('Start MyImpact Assessment')}
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto relative">
                {/* Narrow-viewport scroll hint — Sherri 2026-06-16: users
                   couldn't tell the assessment table was horizontally
                   scrollable on mobile. */}
                <p className="md:hidden text-right text-xs italic text-brand-gray-med px-3 py-1">
                  → {t('scroll for more')}
                </p>
                <table className="w-full min-w-[800px]">
                  <thead>
                    <tr className="border-b border-brand-gray-light">
                      <th className="px-6 py-4 w-10" />
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-6 py-4">
                        {t('Started')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Completed')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('MyImpact Score')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Character')}
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        {t('Calling')}
                      </th>
                      <th className="px-4 py-4" />
                    </tr>
                  </thead>
                  <tbody>
                    {myimpactHistory.map((item) => (
                      <tr key={item.id} className="border-b border-brand-gray-light last:border-b-0">
                        {/* Compare checkbox */}
                        <td className="px-6 py-5">
                          {item.status === 'completed' && (
                            <input
                              type="checkbox"
                              checked={miCompareSelected.includes(item.id)}
                              onChange={() => toggleMiCompareSelect(item.id)}
                              className="w-4 h-4 accent-brand-teal cursor-pointer"
                              aria-label="Select for comparison"
                            />
                          )}
                        </td>
                        {/* Started */}
                        <td className="px-6 py-5 font-body font-bold text-lg text-brand-charcoal">
                          {formatDate(item.created_at)}
                        </td>

                        {/* Completed */}
                        <td className="px-4 py-5 font-body font-bold text-lg text-brand-charcoal">
                          {item.status === 'completed' ? formatDate(item.completed_at) : ''}
                        </td>

                        {/* MyImpact Score */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' && item.myimpact_score ? (
                            <span className="font-body font-bold text-2xl text-brand-teal">
                              {item.myimpact_score.toFixed(1)}
                            </span>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              {t('incomplete')}
                            </span>
                          )}
                        </td>

                        {/* Character Score */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' && item.character_score ? (
                            <div className="flex items-center gap-2">
                              <span className="font-body font-bold text-lg text-brand-charcoal">
                                {item.character_score.toFixed(1)}
                              </span>
                              <span className="text-brand-gray-med">/10</span>
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              {t('incomplete')}
                            </span>
                          )}
                        </td>

                        {/* Calling Score */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' && item.calling_score ? (
                            <div className="flex items-center gap-2">
                              <span className="font-body font-bold text-lg text-brand-charcoal">
                                {item.calling_score.toFixed(1)}
                              </span>
                              <span className="text-brand-gray-med">/10</span>
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              {t('incomplete')}
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="px-4 py-5">
                          <div className="flex items-center gap-2">
                            {item.status === 'completed' ? (
                              <button
                                onClick={() => navigate(`/myimpact-results?id=${item.id}`)}
                                className="w-[175px] h-[50px] bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                              >
                                {t('View Results')}
                              </button>
                            ) : (
                              <button
                                onClick={() => navigate(`/myimpact?continue=${item.id}`)}
                                className="w-[175px] h-[50px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                              >
                                {t('Continue')}
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteAssessment(item.id)}
                              title={t('Delete assessment')}
                              aria-label={t('Delete assessment')}
                              className="w-10 h-10 flex items-center justify-center text-brand-gray-med hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                <path d="M10 11v6M14 11v6" />
                                <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* MyImpact compare controls (mirrors the GPS compare UX above) */}
          {miCompareSelected.length > 0 && (
            <div className="mt-4 flex items-center gap-4">
              <span className="font-body text-base text-brand-gray-med">
                {miCompareSelected.length === 1 ? 'Select one more to compare' : '2 assessments selected'}
              </span>
              <button
                onClick={handleMiCompare}
                disabled={miCompareSelected.length !== 2 || miCompareLoading}
                className="h-10 px-6 bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {miCompareLoading ? 'Loading…' : 'Compare'}
              </button>
              <button
                onClick={() => { setMiCompareSelected([]); setMiComparisonResult(null); setMiCompareError(''); }}
                className="h-10 px-6 border border-brand-gray-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-brand-gray-lightest transition-colors"
              >
                Clear
              </button>
            </div>
          )}

          {miCompareError && (
            <p className="mt-3 font-body text-sm text-red-600">{miCompareError}</p>
          )}

          {/* MyImpact delta panel — character + calling + MyImpact-score change */}
          {miComparisonResult && miComparisonResult.myimpact_1 && miComparisonResult.myimpact_2 && (
            <div className="mt-6 border border-brand-gray-light rounded-xl overflow-hidden">
              <div className="bg-brand-teal/10 px-6 py-3 flex items-center justify-between">
                <h3 className="font-heading font-bold text-lg text-brand-charcoal">
                  {t('MyImpact Score')}&ensp;
                  <span className="font-body font-normal text-sm text-brand-gray-med">
                    {miComparisonResult.myimpact_1.completed_at && new Date(miComparisonResult.myimpact_1.completed_at).toLocaleDateString()}
                    {' → '}
                    {miComparisonResult.myimpact_2.completed_at && new Date(miComparisonResult.myimpact_2.completed_at).toLocaleDateString()}
                  </span>
                </h3>
                <button
                  onClick={() => setMiComparisonResult(null)}
                  className="text-brand-gray-med hover:text-brand-charcoal text-xl font-bold leading-none"
                  aria-label="Close comparison"
                >
                  &times;
                </button>
              </div>

              <div className="px-6 py-4 space-y-6">
                {/* Headline score delta */}
                <div className="flex items-center gap-4 pb-3 border-b border-brand-gray-light">
                  <span className="font-body font-bold text-base text-brand-charcoal w-40">{t('MyImpact Score')}</span>
                  <span className="font-body text-base text-brand-gray-med">
                    {(miComparisonResult.myimpact_1.myimpact_score ?? 0).toFixed(1)} → {(miComparisonResult.myimpact_2.myimpact_score ?? 0).toFixed(1)}
                  </span>
                  {(() => {
                    const d = (miComparisonResult.myimpact_2.myimpact_score ?? 0) - (miComparisonResult.myimpact_1.myimpact_score ?? 0);
                    if (Math.abs(d) < 0.05) return <span className="font-body text-base text-brand-gray-med">—</span>;
                    return (
                      <span className={`font-body font-bold text-base ${d > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {d > 0 ? `+${d.toFixed(1)}` : d.toFixed(1)}
                      </span>
                    );
                  })()}
                </div>

                {/* Character dimensions */}
                <div>
                  <h4 className="font-body font-bold text-base text-brand-gray-med uppercase mb-3">{t('Character')}</h4>
                  <div className="space-y-2">
                    {buildMiDimensionRows(miComparisonResult).character.map(({ name, s1, s2, delta }) => (
                      <div key={name} className="flex items-center gap-3">
                        <span className="w-56 font-body font-bold text-base text-brand-charcoal truncate">{name}</span>
                        <span className="font-body text-base text-brand-gray-med">{s1} → {s2}</span>
                        {delta !== 0 ? (
                          <span className={`font-body font-bold text-base ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {delta > 0 ? `+${delta}` : delta}
                          </span>
                        ) : (
                          <span className="font-body text-base text-brand-gray-med">—</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Calling dimensions */}
                <div>
                  <h4 className="font-body font-bold text-base text-brand-gray-med uppercase mb-3">{t('Calling')}</h4>
                  <div className="space-y-2">
                    {buildMiDimensionRows(miComparisonResult).calling.map(({ name, s1, s2, delta }) => (
                      <div key={name} className="flex items-start gap-3">
                        <span className="w-56 font-body font-bold text-base text-brand-charcoal">{name}</span>
                        <span className="font-body text-base text-brand-gray-med">{s1} → {s2}</span>
                        {delta !== 0 ? (
                          <span className={`font-body font-bold text-base ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {delta > 0 ? `+${delta}` : delta}
                          </span>
                        ) : (
                          <span className="font-body text-base text-brand-gray-med">—</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
        {/* Re-take Confirmation Modal */}
        {retakeModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-8">
              <h3 className="font-heading font-black text-xl text-brand-charcoal mb-4">
                Start a New {retakeType === 'gps' ? 'GPS' : 'MyImpact'} Assessment?
              </h3>
              <p className="font-body text-base text-brand-charcoal mb-6">
                You completed a {retakeType === 'gps' ? 'GPS' : 'MyImpact'} assessment on{' '}
                <span className="font-bold">{retakeDate}</span>. Are you sure you want to start
                a new one?
              </p>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setRetakeModalOpen(false)}
                  className="h-[50px] px-8 bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setRetakeModalOpen(false);
                    navigate(retakeType === 'gps' ? '/assessment' : '/myimpact');
                  }}
                  className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                >
                  Start New Assessment
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
