import { useEffect, useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';

export function Dashboard() {
  const { user, logout } = useAuth();
  const { summary, history, myimpactHistory, fetchSummary, fetchHistory, fetchMyImpactHistory, isLoading, error, compareAssessments } = useDashboard();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  // Build a unified delta table from comparison result
  const buildDeltaRows = (result: any) => {
    const map1: Record<string, number> = {};
    const map2: Record<string, number> = {};
    result.assessment_1.gifts.forEach((g: any) => { map1[g.name] = g.score; });
    result.assessment_2.gifts.forEach((g: any) => { map2[g.name] = g.score; });
    const names = Array.from(new Set([...Object.keys(map1), ...Object.keys(map2)]));
    return names
      .map(name => ({ name, s1: map1[name] ?? 0, s2: map2[name] ?? 0, delta: (map2[name] ?? 0) - (map1[name] ?? 0) }))
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
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

  if (isLoading && !summary) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">Loading dashboard...</p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

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
              <span className="font-medium">Welcome to Your Dashboard,</span>
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
                      GPS Assessments
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); document.getElementById('myimpact-section')?.scrollIntoView({ behavior: 'smooth' }); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      MyImpact Assessments
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
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

          {/* Description */}
          <p className="font-body font-bold text-lg leading-[26px] text-brand-charcoal mt-6 max-w-[732px]">
            Welcome {firstName}! Below are the results of your GPS and MyImpact assessments
            with their current level of completion. Click to continue with or to review the
            results of that particular assessment. You can take as many assessments as you wish.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 mt-8">
            <button
              onClick={() => navigate('/assessment')}
              className="h-[50px] px-10 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
            >
              Take New GPS Assessment
            </button>
            <button
              onClick={() => navigate('/myimpact')}
              className="h-[50px] px-10 bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
            >
              Take New MyImpact Assessment
            </button>
          </div>

          {/* Upgrade / Admin link */}
          {user?.role === 'admin' || user?.role === 'master' ? (
            <p className="font-body font-bold text-base md:text-xl text-brand-charcoal mt-8">
              <Link
                to="/admin"
                className="font-black text-brand-teal underline hover:text-brand-teal/80 transition-colors"
              >
                Go to Admin Dashboard
              </Link>
            </p>
          ) : (
            <p className="font-body font-bold text-base md:text-xl text-brand-charcoal mt-8">
              Want to track and manage your church's assessment results?{' '}
              <Link
                to="/upgrade"
                className="font-black text-brand-teal underline hover:text-brand-teal/80 transition-colors"
              >
                Upgrade to a Church Administrator account
              </Link>
            </p>
          )}
        </section>

        {/* ── GPS Assessments Section ── */}
        <section id="gps-section" className="max-w-[1230px] mx-auto px-6 py-8">
          <h2 className="font-heading font-medium text-2xl md:text-[32px] md:leading-[41px] text-brand-teal mb-4">
            GPS Assessments
          </h2>

          <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] overflow-hidden">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6">
                <p className="font-body text-lg text-brand-gray-med mb-4">
                  No GPS assessments yet. Take your first one!
                </p>
                <button
                  onClick={() => navigate('/assessment')}
                  className="h-[50px] px-10 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                >
                  Start GPS Assessment
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px]">
                  <thead>
                    <tr className="border-b border-brand-gray-light">
                      <th className="px-6 py-4 w-10" />
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-6 py-4">
                        Started
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Completed
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Progress
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Gifts
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Passion
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
                                  className="inline-flex items-center justify-center px-3 h-8 bg-brand-purple/50 rounded-full font-body font-bold text-lg text-brand-charcoal"
                                >
                                  {gift.short_code}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              incomplete
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
                                  {passion.name}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="uppercase font-body font-bold text-base text-brand-gray-med">
                              incomplete
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' ? (
                            <button
                              onClick={() => navigate(`/assessment-results?id=${item.id}`)}
                              className="w-[175px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                            >
                              View Results
                            </button>
                          ) : (
                            <button
                              onClick={() => navigate(`/assessment?continue=${item.id}`)}
                              className="w-[175px] h-[50px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                            >
                              Continue
                            </button>
                          )}
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
            MyImpact Assessments
          </h2>

          <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] overflow-hidden">
            {myimpactHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6">
                <p className="font-body text-lg text-brand-gray-med mb-4">
                  No MyImpact assessments yet. Take your first one!
                </p>
                <button
                  onClick={() => navigate('/myimpact')}
                  className="h-[50px] px-10 bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                >
                  Start MyImpact Assessment
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px]">
                  <thead>
                    <tr className="border-b border-brand-gray-light">
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-6 py-4">
                        Started
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Completed
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        MyImpact Score
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Character
                      </th>
                      <th className="text-left uppercase font-body font-bold text-base text-brand-gray-med px-4 py-4">
                        Calling
                      </th>
                      <th className="px-4 py-4" />
                    </tr>
                  </thead>
                  <tbody>
                    {myimpactHistory.map((item) => (
                      <tr key={item.id} className="border-b border-brand-gray-light last:border-b-0">
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
                              incomplete
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
                              incomplete
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
                              incomplete
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="px-4 py-5">
                          {item.status === 'completed' ? (
                            <button
                              onClick={() => navigate(`/myimpact-results?id=${item.id}`)}
                              className="w-[175px] h-[50px] bg-brand-teal-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-teal-light/80 transition-colors"
                            >
                              View Results
                            </button>
                          ) : (
                            <button
                              onClick={() => navigate(`/myimpact?continue=${item.id}`)}
                              className="w-[175px] h-[50px] bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                            >
                              Continue
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
