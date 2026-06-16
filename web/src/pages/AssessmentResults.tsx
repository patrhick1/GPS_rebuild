import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import { api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { useTranslation } from '../hooks/useTranslation';
import { optionLabel } from '../data/assessmentOptions';

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
  name_es?: string | null;
  short_code: string;
  description: string;
  description_es?: string | null;
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
  const { t, isEs } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const assessmentId = searchParams.get('id');

  // Local state for fetched results (avoids context render loops)
  const [localResults, setLocalResults] = useState<GradedResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const fetchedRef = useRef<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const handleDownloadPdf = async () => {
    if (!assessmentId) return;
    setPdfLoading(true);
    try {
      const res = await api.get(`/assessments/${assessmentId}/pdf`, {
        responseType: 'blob',
        params: { locale: isEs ? 'es' : 'en' },
      });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'gps-results.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently ignore — user can use Print as fallback
    } finally {
      setPdfLoading(false);
    }
  };

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
              {t('Go Back')}
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
          <p className="font-body text-lg text-brand-gray-med">{t('Loading results...')}</p>
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
            {t('GPS Assessment')}
          </h1>
          {assessmentStartDate && (
            <p className="font-body font-semibold italic text-lg text-brand-charcoal mt-1">
              {t('Assessment started on')} {assessmentStartDate}
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
                {t('Completed')} {completedCount} {t('of')} {totalQuestions} {t('questions')}
              </p>
            </div>
          )}

          {/* Section order matches the legacy GPS results page (Sherri 2026-05-05):
             Gifts → Passions → Story. The previous layout led with Story which
             felt backwards to the operations team since spiritual gifts are
             the headline output of the assessment. */}

          {/* === GIFTS === */}
          {/* Show only the top 3-4 gifts (top_gifts already includes ties up to
             a hard cap of 4). Displaying all 19 was overwhelming and not how
             the legacy platform presented results. */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-2">
              {t('Your Spiritual Gifts')}
            </h2>

            <div className="space-y-0">
              {results.top_gifts.map((gift, index) => (
                <div key={gift.id}>
                  <div className="border-t border-brand-gray-light" />

                  <div className="flex items-start gap-6 py-6">
                    <span
                      className={`shrink-0 inline-flex items-center justify-center h-[50px] px-6 rounded-full font-body font-bold text-xl text-brand-charcoal ${GIFT_COLORS[index % GIFT_COLORS.length]}`}
                    >
                      {(isEs && gift.name_es) || gift.name}
                    </span>

                    <p className="flex-1 font-body font-bold text-xl text-brand-charcoal leading-[30px]">
                      {(isEs && gift.description_es) || gift.description}
                    </p>

                    <span className="shrink-0 font-body font-black text-xl text-brand-teal whitespace-nowrap">
                      {t('Score:')} {gift.points}
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>

            {/* Key Abilities — folded under the gifts section because, per the
               legacy layout, abilities are the practical companion to gifts. */}
            {results.abilities.length > 0 && (
              <div className="mt-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">{t('Key Abilities')}</h3>
                <div className="flex flex-wrap gap-2">
                  {results.abilities.map((ability, idx) => (
                    <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-purple/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                      {optionLabel(ability, isEs)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* === PASSIONS === */}
          {/* Top TWO influencing styles only (not the legacy storage cap of 3
             and not all 5). Sherri 2026-05-05: "we only display top TWO ...
             this helps users focus in." */}
          <section className="mt-16">
            <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-2">
              {t('Influencing Styles')}
            </h2>
            <p className="font-body font-bold text-xl text-brand-charcoal leading-[30px] mb-6">
              {t('Your Spiritual Influencing Styles (highest score is primary & lower is secondary)')}
            </p>

            <div className="space-y-0">
              {results.top_passions.slice(0, 2).map((passion, index) => (
                <div key={passion.id}>
                  <div className="border-t border-brand-gray-light" />

                  <div className="flex items-start gap-6 py-6">
                    <span
                      className={`shrink-0 inline-flex items-center justify-center h-[50px] px-6 rounded-full font-body font-bold text-xl text-brand-charcoal ${PASSION_COLORS[index % PASSION_COLORS.length]}`}
                    >
                      {(isEs && passion.name_es) || passion.name}
                    </span>

                    <p className="flex-1 font-body font-bold text-xl text-brand-charcoal leading-[30px]">
                      {(isEs && passion.description_es) || passion.description}
                    </p>

                    <span className="shrink-0 font-body font-black text-xl text-brand-teal whitespace-nowrap">
                      {t('Score:')} {passion.points}
                    </span>
                  </div>
                </div>
              ))}
              <div className="border-t border-brand-gray-light" />
            </div>

            {/* People + Causes — folded under the passions section. Per the
               legacy layout these belong with passions, not in a separate
               "Selections" block, because the GPS framing is "passions for
               people, passions for causes". */}
            {results.people.length > 0 && (
              <div className="mt-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">{t("People You're Passionate About")}</h3>
                <div className="flex flex-wrap gap-2">
                  {results.people.map((person, idx) => (
                    <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-pink/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                      {optionLabel(person, isEs)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {results.causes.length > 0 && (
              <div className="mt-6">
                <h3 className="font-body font-black text-xl text-brand-charcoal mb-3">{t('Causes You Care About')}</h3>
                <div className="flex flex-wrap gap-2">
                  {results.causes.map((cause, idx) => (
                    <span key={idx} className="inline-flex items-center justify-center px-4 h-8 bg-brand-teal-light/50 rounded-full font-body font-bold text-lg text-brand-charcoal">
                      {optionLabel(cause, isEs)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* === STORY === */}
          {/* Last section in the legacy layout. Question shown in teal, answer
             in charcoal so the eye separates prompt from response. */}
          {results.stories.length > 0 && (
            <section className="mt-16">
              <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mb-6">
                {t('Story')}
              </h2>

              <div className="font-body font-bold text-xl text-brand-charcoal leading-[30px] space-y-4">
                {isEs ? (
                  <>
                    <p>
                      <span className="font-black">Deléitate en el SEÑOR, y él te concederá los deseos de tu corazón.</span>
                      {' '}Salmo 37:4
                    </p>
                    <p>
                      <span className="font-black">Porque somos hechura de Dios, creados en Cristo Jesús para buenas obras, las cuales Dios dispuso de antemano a fin de que las pongamos en práctica.</span>
                      {' '}Efesios 2:10
                    </p>
                    <p className="font-bold">
                      Al permanecer con Jesús, Él hace crecer en nosotros una pasión por las buenas obras que Él quiere que hagamos. Evaluaremos tres áreas de pasión: las Personas, las Causas y el Estilo de Influencia principal que usas para servir a esas personas y causas. Sigue las instrucciones en cada categoría para discernir tu pasión.
                    </p>
                  </>
                ) : (
                  <>
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
                  </>
                )}
              </div>

              {/* Story responses — Q in teal, A in charcoal per Sherri's
                 reference layout for visual separation. */}
              <div className="mt-8 space-y-6">
                {results.stories.map((story, idx) => (
                  <div key={idx} className="border-t border-brand-gray-light pt-5">
                    <h3 className="font-body font-bold text-lg text-brand-teal">
                      {(isEs && story.question_es) ? story.question_es : story.question}
                    </h3>
                    <p className="font-body text-lg text-brand-charcoal mt-2 whitespace-pre-wrap">
                      {story.answer || <span className="italic text-brand-gray-med">—</span>}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Navigation footer */}
          <div className="flex justify-between items-center mt-16 no-print">
            <button
              onClick={() => navigate(-1)}
              className="h-[50px] px-8 bg-brand-gray-light text-brand-charcoal font-body font-bold text-lg rounded-xl hover:bg-brand-gray-light/80 transition-colors flex items-center gap-2"
            >
              <span className="text-xl">&larr;</span> {t('Back')}
            </button>

            <div className="flex items-center gap-3">
              {assessmentId && (
                <button
                  onClick={handleDownloadPdf}
                  disabled={pdfLoading}
                  className="h-[50px] px-8 bg-white border-2 border-brand-teal text-brand-teal font-body font-bold text-lg rounded-xl hover:bg-brand-teal/10 transition-colors disabled:opacity-50"
                >
                  {pdfLoading ? t('Generating…') : t('Download PDF')}
                </button>
              )}
              <button
                onClick={() => window.print()}
                className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors flex items-center gap-2"
              >
                {t('Print')} <span className="text-xl">&rarr;</span>
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
