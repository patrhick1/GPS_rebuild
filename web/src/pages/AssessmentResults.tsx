import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import { api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

const GIFT_COLORS = [
  'bg-brand-teal-light',
  'bg-brand-gold',
  'bg-brand-purple',
  'bg-brand-pink',
];

const PASSION_COLORS = [
  'bg-brand-teal-light',
  'bg-brand-gold',
  'bg-brand-purple',
  'bg-brand-pink',
];

interface GiftResult {
  id: string;
  name: string;
  short_code: string;
  description: string;
  points: number;
}

interface StoryResult {
  question: string;
  answer: string;
  question_es?: string;
}

interface GradedResults {
  gifts: GiftResult[];
  top_gifts: GiftResult[];
  passions: GiftResult[];
  top_passions: GiftResult[];
  abilities: string[];
  people: string[];
  causes: string[];
  stories: StoryResult[];
}

export function AssessmentResults() {
  const { results: contextResults, questions, answeredCount, assessmentStartDate } = useAssessment();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const assessmentId = searchParams.get('id');

  // Local state for fetched results (avoids context render loops)
  const [localResults, setLocalResults] = useState<GradedResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const fetchedRef = useRef<string | null>(null);

  // Use context results if available (e.g. after submit), otherwise use locally fetched
  const results = contextResults || localResults;

  useEffect(() => {
    if (assessmentId && !results && !loading && fetchedRef.current !== assessmentId) {
      fetchedRef.current = assessmentId;
      setLoading(true);
      setFetchError(null);
      api.get(`/assessments/${assessmentId}/grade`)
        .then((res) => {
          // If the API returned MyImpact data, redirect to the correct page
          if (res.data.character && res.data.calling && !res.data.gifts) {
            navigate(`/myimpact-results?id=${assessmentId}`, { replace: true });
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
  }, [assessmentId, results, loading]);

  useEffect(() => {
    if (!assessmentId && !results) {
      navigate('/dashboard');
    }
  }, [assessmentId, results, navigate]);

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

  if (!results) {
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

  const totalQuestions = questions.length;
  const completedCount = answeredCount || totalQuestions;
  const progressPct = totalQuestions > 0 ? Math.round((completedCount / totalQuestions) * 100) : 100;

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        <div className="max-w-[1230px] mx-auto px-6 pt-12 pb-16">

          {/* Header */}
          <h1 className="font-heading font-black text-[32px] md:text-[48px] md:leading-[55px] text-brand-charcoal">
            GPS Assessment
          </h1>
          {assessmentStartDate && (
            <p className="font-body font-semibold italic text-lg text-brand-charcoal mt-1">
              Assessment started on {assessmentStartDate}
            </p>
          )}

          {/* Progress bar — only show if questions are loaded (i.e. user just submitted) */}
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

          {/* Story Section */}
          {results.stories.length > 0 && (
            <section className="mt-16">
              <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                Story
              </h2>

              <div className="font-body font-bold text-xl text-brand-charcoal leading-[30px] space-y-4">
                <p>
                  <span className="font-black">Take delight in the LORD, and he will give you the desires of your heart.</span>
                  {' '}Psalm 37:4
                </p>
                <p>
                  <span className="font-black">We are God's masterpiece. He has created us anew in Christ Jesus, so we can do the good things he planned for us long ago.</span>
                  {' '}Ephesians 2:10
                </p>
                <p className="font-bold">
                  As we abide with Jesus, He grows in us a passion for the good works He wants us to do. We will assess three areas of passion: the People, the Causes, and the primary Influencing Style you use to serve those people and causes. Follow the directions in each category to discern your passion.
                </p>
              </div>

              {/* Story responses */}
              {results.stories.map((story, idx) => (
                <div key={idx} className="mt-6">
                  <h3 className="font-body font-black text-lg text-brand-charcoal">{story.question}</h3>
                  <p className="font-body text-lg text-brand-charcoal mt-1 whitespace-pre-wrap">{story.answer}</p>
                </div>
              ))}
            </section>
          )}

          {/* Your Spiritual Gifts */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
              Your Spiritual Gifts
            </h2>

            <div className="space-y-0">
              {results.gifts.map((gift, index) => (
                <div key={gift.id}>
                  {/* Separator */}
                  <div className="border-t border-brand-gray-light" />

                  <div className="flex items-start gap-6 py-6">
                    {/* Gift pill */}
                    <span
                      className={`shrink-0 inline-flex items-center justify-center h-[50px] px-6 rounded-full font-body font-bold text-xl text-brand-charcoal ${GIFT_COLORS[index % GIFT_COLORS.length]}`}
                    >
                      {gift.name}
                    </span>

                    {/* Description */}
                    <p className="flex-1 font-body font-bold text-xl text-brand-charcoal leading-[30px]">
                      {gift.description}
                    </p>

                    {/* Score */}
                    <span className="shrink-0 font-body font-black text-xl text-brand-teal whitespace-nowrap">
                      Score: {gift.points}
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>
          </section>

          {/* Passions / Influencing Styles */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-2">
              Passions
            </h2>
            <p className="font-body font-bold text-xl text-brand-charcoal leading-[30px] mb-6">
              Your Spiritual Influencing Styles (highest score is primary &amp; lower is secondary)
            </p>

            <div className="space-y-0">
              {results.passions.map((passion, index) => (
                <div key={passion.id}>
                  <div className="border-t border-brand-gray-light" />

                  <div className="flex items-start gap-6 py-6">
                    {/* Passion pill */}
                    <span
                      className={`shrink-0 inline-flex items-center justify-center h-[50px] px-6 rounded-full font-body font-bold text-xl text-brand-charcoal ${PASSION_COLORS[index % PASSION_COLORS.length]}`}
                    >
                      {passion.name}
                    </span>

                    {/* Description */}
                    <p className="flex-1 font-body font-bold text-xl text-brand-charcoal leading-[30px]">
                      {passion.description}
                    </p>

                    {/* Score */}
                    <span className="shrink-0 font-body font-black text-xl text-brand-teal whitespace-nowrap">
                      Score: {passion.points}
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>
          </section>

          {/* Selections */}
          {(results.abilities.length > 0 || results.people.length > 0 || results.causes.length > 0) && (
            <section className="mt-16">
              <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                Your Selections
              </h2>

              {results.abilities.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">Key Abilities</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.abilities.map((ability, idx) => (
                      <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-purple/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                        {ability}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {results.people.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">People You're Passionate About</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.people.map((person, idx) => (
                      <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-pink/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                        {person}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {results.causes.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">Causes You Care About</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.causes.map((cause, idx) => (
                      <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-teal-light/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                        {cause}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

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
