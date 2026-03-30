import { useEffect, useState, useRef, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire',
  'New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio',
  'Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota',
  'Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia',
  'Wisconsin','Wyoming',
];

export function Account() {
  const { user, logout } = useAuth();
  const {
    summary,
    fetchSummary,
    searchChurches,
    requestChurchLink,
    leaveOrganization,
  } = useDashboard();
  const navigate = useNavigate();

  // Menu state
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Profile form state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [country, setCountry] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  // Church linking state
  const [churchQuery, setChurchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<
    { id: string; name: string; city?: string; state?: string; member_count: number }[]
  >([]);
  const [selectedChurch, setSelectedChurch] = useState<string | null>(null);
  const [linkMessage, setLinkMessage] = useState('');
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Populate form when summary loads
  useEffect(() => {
    if (summary) {
      setFirstName(summary.user.first_name || '');
      setLastName(summary.user.last_name || '');
      setEmail(summary.user.email || '');
    }
  }, [summary]);

  // Populate extended fields from user profile
  useEffect(() => {
    if (user) {
      setPhone((user as any).phone_number || '');
      setCountry((user as any).country || '');
      setCity((user as any).city || '');
      setState((user as any).state || '');
    }
  }, [user]);

  // Fetch full profile for extended fields
  useEffect(() => {
    async function loadProfile() {
      try {
        const res = await api.get('/auth/me');
        const data = res.data;
        setPhone(data.phone_number || '');
        setCountry(data.country || '');
        setCity(data.city || '');
        setState(data.state || '');
      } catch {
        // ignore — fields stay empty
      }
    }
    loadProfile();
  }, []);

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

  // Profile save
  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveMessage('');
    try {
      await api.put('/auth/profile', {
        first_name: firstName,
        last_name: lastName,
        phone_number: phone || null,
        city: city || null,
        state: state || null,
        country: country || null,
      });
      setSaveMessage('Profile updated successfully');
      fetchSummary();
    } catch {
      setSaveMessage('Failed to save changes');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMessage(''), 3000);
    }
  };

  // Church search
  const handleChurchSearch = async (query: string) => {
    setChurchQuery(query);
    setSelectedChurch(null);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const results = await searchChurches(query);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  // Church link submit
  const handleChurchLink = async () => {
    if (!selectedChurch) return;
    setLinkMessage('');
    try {
      await requestChurchLink(selectedChurch);
      setLinkMessage('Request submitted! You will be connected once your church approves.');
      setChurchQuery('');
      setSearchResults([]);
      setSelectedChurch(null);
    } catch {
      setLinkMessage('Failed to submit request');
    }
  };

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        {/* ── Header Section ── */}
        <section className="max-w-[1230px] mx-auto px-6 pt-12 pb-4">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="font-heading font-black text-3xl md:text-[48px] md:leading-[55px] text-brand-charcoal">
                Your Account
              </h1>
              <p className="font-body font-semibold italic text-lg leading-[26px] text-brand-charcoal mt-2">
                Your Personal Account Information
              </p>
            </div>

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
                      onClick={() => { setMenuOpen(false); navigate('/dashboard'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      GPS Assessments
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/dashboard'); }}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      MyImpact Assessments
                    </button>
                    <hr className="border-brand-gray-light mx-4" />
                    <button
                      onClick={() => setMenuOpen(false)}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-teal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
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

        {/* ── Profile Form Card ── */}
        <section className="max-w-[1230px] mx-auto px-6 pb-8">
          <form onSubmit={handleSaveProfile}>
            <div className="max-w-[1057px] bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-10 lg:p-12">
              {/* Row 1: First Name | Email */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="First Name"
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                />
                <input
                  type="email"
                  value={email}
                  disabled
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal opacity-70 cursor-not-allowed"
                />
              </div>

              {/* Row 2: Last Name | Phone */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Last Name"
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Phone Number"
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                />
              </div>

              {/* Divider */}
              <hr className="border-brand-gray-light mb-6" />

              {/* Location label */}
              <p className="font-body font-bold text-lg text-brand-charcoal mb-3">Location</p>

              {/* Row 3: Country | City | State */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <select
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                >
                  <option value="">Country</option>
                  <option value="United States">United States</option>
                  <option value="Canada">Canada</option>
                  <option value="Mexico">Mexico</option>
                  <option value="United Kingdom">United Kingdom</option>
                  <option value="Other">Other</option>
                </select>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="City"
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                />
                <select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                >
                  <option value="">State</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Change Password link + Save button */}
              <div className="flex flex-col sm:flex-row items-end justify-end gap-3">
                <Link
                  to="/update-password"
                  className="font-body font-bold text-base text-brand-teal hover:underline"
                >
                  Change Password
                </Link>
                <button
                  type="submit"
                  disabled={saving}
                  className="w-[219px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 disabled:opacity-50 transition-colors"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>

              {saveMessage && (
                <p className={`mt-3 text-right font-body text-sm ${saveMessage.includes('success') ? 'text-green-600' : 'text-red-600'}`}>
                  {saveMessage}
                </p>
              )}
            </div>
          </form>
        </section>

        {/* ── Church Linking Section ── */}
        <section className="max-w-[1230px] mx-auto px-6 pb-16">
          <h2 className="font-heading font-black text-2xl md:text-[40px] md:leading-[41px] text-brand-charcoal mb-2">
            Link My Assessment Results to a Church
          </h2>
          <p className="font-body font-semibold italic text-lg leading-[26px] text-brand-charcoal mb-4">
            You'll be connected once your church approves the request
          </p>

          <div className="max-w-[1057px] bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-10 lg:p-12">
            {summary?.organization ? (
              /* Already linked to a church */
              <div>
                <p className="font-body font-bold text-lg text-brand-charcoal mb-4">
                  You are currently linked to <span className="text-brand-teal">{summary.organization.name}</span>
                </p>
                <button
                  onClick={async () => {
                    await leaveOrganization();
                    setLinkMessage('You have left the organization.');
                  }}
                  className="h-[50px] px-8 bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors"
                >
                  Leave Organization
                </button>
              </div>
            ) : (
              /* Church search */
              <div>
                <p className="font-body font-bold text-lg text-brand-charcoal mb-3">
                  Type to search for your church
                </p>

                {/* Search input */}
                <div className="relative mb-4">
                  <input
                    type="text"
                    value={churchQuery}
                    onChange={(e) => handleChurchSearch(e.target.value)}
                    placeholder="Name of Church"
                    className="w-full max-w-[934px] h-[50px] px-5 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body font-bold text-lg text-brand-charcoal placeholder:text-brand-charcoal/60 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                  />

                  {/* Search results dropdown */}
                  {searchResults.length > 0 && (
                    <div className="absolute left-0 top-[54px] w-full max-w-[934px] bg-white border border-brand-gray-light rounded-xl shadow-lg z-40 max-h-[200px] overflow-y-auto">
                      {searchResults.map((church) => (
                        <button
                          key={church.id}
                          type="button"
                          onClick={() => {
                            setSelectedChurch(church.id);
                            setChurchQuery(church.name);
                            setSearchResults([]);
                          }}
                          className={`w-full text-left px-5 py-3 font-body text-base text-brand-charcoal hover:bg-brand-gray-lightest transition-colors ${
                            selectedChurch === church.id ? 'bg-brand-gray-lightest' : ''
                          }`}
                        >
                          {church.name}
                          {church.city && <span className="text-brand-gray-med"> — {church.city}{church.state ? `, ${church.state}` : ''}</span>}
                        </button>
                      ))}
                    </div>
                  )}

                  {searching && (
                    <p className="mt-2 font-body text-sm text-brand-gray-med">Searching...</p>
                  )}
                </div>

                {/* Submit button */}
                <button
                  type="button"
                  onClick={handleChurchLink}
                  disabled={!selectedChurch}
                  className="w-[167px] h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mb-6"
                >
                  Submit
                </button>

                {linkMessage && (
                  <p className={`font-body text-sm mb-4 ${linkMessage.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                    {linkMessage}
                  </p>
                )}

                {/* Upgrade link */}
                <p className="font-body font-bold text-lg text-brand-charcoal">
                  Can't find your church?{' '}
                  <Link
                    to="/upgrade"
                    className="text-brand-teal underline hover:text-brand-teal/80 transition-colors"
                  >
                    Upgrade to a Church Administrator Account
                  </Link>
                </p>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
