import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import { api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

interface CharacterScores {
  loving: number;
  joyful: number;
  peaceful: number;
  patient: number;
  kind: number;
  good: number;
  faithful: number;
  gentle: number;
  self_controlled: number;
  average: number;
}

interface CallingScores {
  know_gifts: number;
  know_people: number;
  using_gifts: number;
  see_impact: number;
  experience_joy: number;
  pray_regularly: number;
  see_movement: number;
  receive_support: number;
  average: number;
}

interface MyImpactResultsData {
  character: CharacterScores;
  calling: CallingScores;
  myimpact_score: number;
}

export function MyImpactResults() {
  const { myimpactResults: contextResults, questions, answeredCount, assessmentStartDate } = useAssessment();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const assessmentId = searchParams.get('id');

  // Local state for fetched results (avoids context render loops)
  const [localResults, setLocalResults] = useState<MyImpactResultsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const fetchedRef = useRef<string | null>(null);

  // Use context results if available (e.g. after submit), otherwise use locally fetched
  const myimpactResults = contextResults || localResults;

  useEffect(() => {
    if (assessmentId && !myimpactResults && !loading && fetchedRef.current !== assessmentId) {
      fetchedRef.current = assessmentId;
      setLoading(true);
      setFetchError(null);
      api.get(`/assessments/${assessmentId}/grade`)
        .then((res) => {
          // If the API returned GPS data, redirect to the correct page
          if (res.data.gifts && !res.data.character) {
            navigate(`/assessment-results?id=${assessmentId}`, { replace: true });
            return;
          }
          setLocalResults(res.data);
        })
        .catch((err) => {
          setFetchError(err.response?.data?.detail || 'Failed to load results');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [assessmentId, myimpactResults, loading]);

  useEffect(() => {
    if (!assessmentId && !myimpactResults) {
      navigate('/dashboard');
    }
  }, [assessmentId, myimpactResults, navigate]);

  if (fetchError) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="font-body text-lg text-red-600 mb-4">{fetchError}</p>
            <button
              onClick={() => navigate(-1)}
              className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
            >
              Go Back
            </button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (!myimpactResults) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">Loading results...</p>
        </main>
        <Footer />
      </div>
    );
  }

  const { character, calling, myimpact_score } = myimpactResults;

  const totalQuestions = questions.length;
  const completedCount = answeredCount || totalQuestions;
  const progressPct = totalQuestions > 0 ? Math.round((completedCount / totalQuestions) * 100) : 100;

  const getScoreInterpretation = (score: number) => {
    if (score >= 70) return { label: 'Mature', bg: 'bg-green-100 text-green-800' };
    if (score >= 50) return { label: 'Growing', bg: 'bg-yellow-100 text-yellow-800' };
    if (score >= 30) return { label: 'Developing', bg: 'bg-orange-100 text-orange-800' };
    return { label: 'Beginning', bg: 'bg-red-100 text-red-800' };
  };

  const interpretation = getScoreInterpretation(myimpact_score);

  const getBarColor = (score: number) => {
    if (score >= 8) return 'bg-brand-teal';
    if (score >= 5) return 'bg-brand-gold';
    return 'bg-brand-pink';
  };

  const characterDimensions = [
    { key: 'loving', label: 'Loving', score: character.loving },
    { key: 'joyful', label: 'Joyful', score: character.joyful },
    { key: 'peaceful', label: 'Peaceful', score: character.peaceful },
    { key: 'patient', label: 'Patient', score: character.patient },
    { key: 'kind', label: 'Kind', score: character.kind },
    { key: 'good', label: 'Good', score: character.good },
    { key: 'faithful', label: 'Faithful', score: character.faithful },
    { key: 'gentle', label: 'Gentle', score: character.gentle },
    { key: 'self_controlled', label: 'Self-Controlled', score: character.self_controlled },
  ];

  const callingDimensions = [
    { key: 'know_gifts', label: 'I can name my top 3 Spiritual Gifts', score: calling.know_gifts },
    { key: 'know_people', label: 'I know the people/causes God wants me to serve', score: calling.know_people },
    { key: 'using_gifts', label: 'I am using my gifts to serve others', score: calling.using_gifts },
    { key: 'see_impact', label: 'I see God making a difference through me', score: calling.see_impact },
    { key: 'experience_joy', label: 'I experience joy in serving others', score: calling.experience_joy },
    { key: 'pray_regularly', label: 'I regularly pray for people around me', score: calling.pray_regularly },
    { key: 'see_movement', label: 'I see people move toward faith', score: calling.see_movement },
    { key: 'receive_support', label: 'I receive support in my calling', score: calling.receive_support },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        <div className="max-w-[1230px] mx-auto px-6 pt-12 pb-16">

          {/* Header */}
          <h1 className="font-heading font-black text-[32px] md:text-[48px] md:leading-[55px] text-brand-charcoal">
            MyImpact Assessment
          </h1>
          {assessmentStartDate && (
            <p className="font-body font-semibold italic text-lg text-brand-charcoal mt-1">
              Assessment started on {assessmentStartDate}
            </p>
          )}

          {/* Progress bar — only show if questions are loaded */}
          {totalQuestions > 0 && (
            <div className="mt-8">
              <div className="w-full h-[42px] bg-brand-gray-lightest rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-gold rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="font-body font-semibold italic text-lg text-brand-charcoal text-center mt-3">
                Completed {completedCount} of {totalQuestions} questions
              </p>
            </div>
          )}

          {/* MyImpact Score Hero */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
              Your MyImpact Score
            </h2>

            <div className="bg-brand-gray-lightest rounded-xl p-8 md:p-12 text-center">
              <p className="font-body font-bold text-xl text-brand-charcoal mb-2">
                Character &times; Calling = MyImpact Score
              </p>

              {/* Formula display */}
              <div className="flex items-center justify-center gap-4 md:gap-8 my-8">
                <div className="text-center">
                  <div className="font-heading font-black text-[40px] md:text-[56px] text-brand-teal leading-none">
                    {character.average.toFixed(1)}
                  </div>
                  <div className="font-body font-bold text-lg text-brand-gray-med mt-1">Character</div>
                </div>
                <span className="font-heading font-black text-[32px] text-brand-charcoal">&times;</span>
                <div className="text-center">
                  <div className="font-heading font-black text-[40px] md:text-[56px] text-brand-teal leading-none">
                    {calling.average.toFixed(1)}
                  </div>
                  <div className="font-body font-bold text-lg text-brand-gray-med mt-1">Calling</div>
                </div>
                <span className="font-heading font-black text-[32px] text-brand-charcoal">=</span>
                <div className="text-center">
                  <div className="font-heading font-black text-[48px] md:text-[64px] text-brand-gold leading-none">
                    {myimpact_score.toFixed(1)}
                  </div>
                  <div className="font-body font-bold text-lg text-brand-gray-med mt-1">MyImpact</div>
                </div>
              </div>

              <span className={`inline-flex items-center px-4 py-1 rounded-full font-body font-bold text-lg ${interpretation.bg}`}>
                {interpretation.label}
              </span>
              <p className="font-body text-base text-brand-gray-med mt-4 max-w-lg mx-auto">
                Most first-time takers score between 4-25. The goal is steady growth, not perfection.
              </p>
            </div>
          </section>

          {/* Character Section */}
          <section className="mt-16">
            <div className="flex items-baseline justify-between mb-2">
              <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal">
                Character
              </h2>
              <span className="font-body font-black text-xl text-brand-teal">
                Average: {character.average.toFixed(1)}/10
              </span>
            </div>
            <p className="font-body font-bold text-xl text-brand-charcoal leading-[30px] mb-6">
              Fruit of the Spirit &mdash; Rate yourself as those who know you best would rate you.
            </p>

            <div className="space-y-0">
              {characterDimensions.map((dim) => (
                <div key={dim.key}>
                  <div className="border-t border-brand-gray-light" />
                  <div className="flex items-center gap-6 py-5">
                    <span className="shrink-0 inline-flex items-center justify-center h-[50px] w-[195px] rounded-full bg-brand-teal-light font-body font-bold text-xl text-brand-charcoal">
                      {dim.label}
                    </span>

                    <div className="flex-1 h-3 bg-brand-gray-lightest rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${getBarColor(dim.score)}`}
                        style={{ width: `${(dim.score / 10) * 100}%` }}
                      />
                    </div>

                    <span className="shrink-0 font-body font-black text-xl text-brand-teal w-16 text-right">
                      {dim.score}/10
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>
          </section>

          {/* Calling Section */}
          <section className="mt-16">
            <div className="flex items-baseline justify-between mb-2">
              <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal">
                Calling
              </h2>
              <span className="font-body font-black text-xl text-brand-teal">
                Average: {calling.average.toFixed(1)}/10
              </span>
            </div>
            <p className="font-body font-bold text-xl text-brand-charcoal leading-[30px] mb-6">
              Your Unique Design &mdash; Your Calling is the unique way God has designed you to partner with Him.
            </p>

            <div className="space-y-0">
              {callingDimensions.map((dim) => (
                <div key={dim.key}>
                  <div className="border-t border-brand-gray-light" />
                  <div className="flex items-center gap-6 py-5">
                    <span className="shrink-0 inline-flex items-center justify-center h-[50px] px-6 min-w-[195px] rounded-full bg-brand-gold font-body font-bold text-base text-brand-charcoal text-center leading-tight">
                      {dim.label}
                    </span>

                    <div className="flex-1 h-3 bg-brand-gray-lightest rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${getBarColor(dim.score)}`}
                        style={{ width: `${(dim.score / 10) * 100}%` }}
                      />
                    </div>

                    <span className="shrink-0 font-body font-black text-xl text-brand-teal w-16 text-right">
                      {dim.score}/10
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>
          </section>

          {/* Growth Tips */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
              Growth Opportunities
            </h2>
            <p className="font-body font-bold text-xl text-brand-charcoal leading-[30px] mb-6">
              The goal is steady growth, not perfection. Consider focusing on your lowest-scoring areas to increase your overall impact.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-brand-gray-lightest rounded-xl p-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-2">Retake Regularly</h3>
                <p className="font-body text-base text-brand-charcoal">Take this assessment every 6-12 months to track your growth over time.</p>
              </div>
              <div className="bg-brand-gray-lightest rounded-xl p-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-2">Get Feedback</h3>
                <p className="font-body text-base text-brand-charcoal">Ask those closest to you how they would rate your character and calling.</p>
              </div>
              <div className="bg-brand-gray-lightest rounded-xl p-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-2">Set Goals</h3>
                <p className="font-body text-base text-brand-charcoal">Focus on 1-2 dimensions at a time for sustainable growth.</p>
              </div>
            </div>
          </section>

          {/* Navigation footer */}
          <div className="flex justify-between items-center mt-16 no-print">
            <button
              onClick={() => navigate(-1)}
              className="h-[50px] px-8 bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors flex items-center gap-2"
            >
              <span className="text-xl">&larr;</span> Back
            </button>

            <button
              onClick={() => window.print()}
              className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors flex items-center gap-2"
            >
              Print <span className="text-xl">&rarr;</span>
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
