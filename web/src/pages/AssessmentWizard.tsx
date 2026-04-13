import { useEffect, useState, useRef, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAssessment } from '../context/AssessmentContext';

/** Simple translation map for GPS assessment UI strings */
const ES_STRINGS: Record<string, string> = {
  'GPS Assessment': 'Evaluación GPS',
  'Assessment started on': 'Evaluación iniciada el',
  'Completed': 'Completadas',
  'of': 'de',
  'questions': 'preguntas',
  'Statements': 'Declaraciones',
  'Answers': 'Respuestas',
  'Almost Never': 'Casi Nunca',
  'Almost Always': 'Casi Siempre',
  'Previous': 'Anterior',
  'Next': 'Siguiente',
  'Submit': 'Enviar',
  'Submitting...': 'Enviando...',
  'Save & Exit': 'Guardar y Salir',
  'Account': 'Cuenta',
  'Logout': 'Cerrar Sesión',
  'Loading assessment...': 'Cargando evaluación...',
  'No questions available': 'No hay preguntas disponibles',
  'Enter your answer...': 'Ingrese su respuesta...',
  'Assessment menu': 'Menú de evaluación',
};
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { MultiSelectPage } from '../components/MultiSelectPage';
import { PEOPLE_OPTIONS, CAUSES_OPTIONS, ABILITIES_OPTIONS } from '../data/assessmentOptions';
import goldMenuIcon from '../../Graphics for Dev/Icons/Gold Menu Icon.svg';
import goldXIcon from '../../Graphics for Dev/Icons/Gold X Icon.svg';
import leftArrowIcon from '../../Graphics for Dev/Icons/Charcoal Left Arrow Icon.svg';
import rightArrowIcon from '../../Graphics for Dev/Icons/White Right Arrow Icon.svg';

const SECTION_LABELS: Record<string, Record<string, string>> = {
  gifts: { en: 'Gifts', es: 'Dones' },
  passion: { en: 'Passion', es: 'Pasión' },
  story: { en: 'Story', es: 'Historia' },
};

export function AssessmentWizard() {
  const {
    assessmentId,
    questions,
    answers,
    pages,
    currentPageIndex,
    isLoading,
    error,
    startAssessment,
    continueAssessment,
    saveAnswer,
    goToNextPage,
    goToPreviousPage,
    submitAssessment,
    saveProgress,
    clearError,
    answeredCount,
    assessmentStartDate,
  } = useAssessment();

  const { logout, locale } = useAuth();
  const isEs = locale === 'es';
  const t = useMemo(() => (key: string) => isEs ? (ES_STRINGS[key] || key) : key, [isEs]);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const continueId = searchParams.get('continue');

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (continueId) {
      if (!assessmentId && !isLoading) {
        continueAssessment(continueId);
      }
    } else if (!assessmentId && !isLoading) {
      startAssessment('gps');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [continueId, assessmentId, isLoading]);

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

  const currentPage = pages[currentPageIndex];
  const totalQuestions = questions.length;
  const percentage = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const handleLikertSelect = (questionId: string, value: number) => {
    saveAnswer(questionId, { numeric_value: value });
  };

  const handleTextChange = (questionId: string, value: string) => {
    saveAnswer(questionId, { text_value: value });
  };

  const handleSubmit = async () => {
    try {
      await submitAssessment();
      navigate('/assessment-results');
    } catch {
      // Error handled by context
    }
  };

  const handleSaveAndExit = async () => {
    setMenuOpen(false);
    await saveProgress();
    navigate('/dashboard');
  };

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  // Check if all questions on current page are answered
  const isCurrentPageComplete = (): boolean => {
    if (!currentPage) return false;

    if (currentPage.pageType === 'likert') {
      return currentPage.questions.every(q => answers[q.id]?.numeric_value != null);
    }
    if (currentPage.pageType === 'abilities') {
      const q = currentPage.questions[0];
      return !!answers[q.id]?.multiple_choice_answer;
    }
    if (currentPage.pageType === 'people') {
      const q = currentPage.questions[0];
      return !!answers[q.id]?.multiple_choice_answer;
    }
    if (currentPage.pageType === 'causes') {
      const q = currentPage.questions[0];
      return !!answers[q.id]?.multiple_choice_answer;
    }
    if (currentPage.pageType === 'text') {
      const q = currentPage.questions[0];
      return !!answers[q.id]?.text_value;
    }
    return true;
  };

  const isLastPage = currentPageIndex === pages.length - 1;

  if (isLoading && !assessmentId) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">{t('Loading assessment...')}</p>
        </main>
        <Footer />
      </div>
    );
  }

  if (!currentPage || pages.length === 0) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">{t('No questions available')}</p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        <section className="max-w-[1230px] mx-auto px-6 pt-12 pb-8">
          <button
            onClick={handleSaveAndExit}
            className="inline-flex items-center gap-1 font-body font-bold text-sm text-brand-teal hover:text-brand-teal/80 transition-colors mb-4"
          >
            <span className="text-base">←</span> Back to Dashboard
          </button>
          {/* ── Title Row ── */}
          <div className="flex justify-between items-start">
            <div>
              <h1 className="font-heading font-black text-[48px] leading-[55px] text-brand-charcoal">
                {t('GPS Assessment')}
              </h1>
              {assessmentStartDate && (
                <p className="font-body font-semibold italic text-lg text-brand-charcoal mt-1">
                  {t('Assessment started on')} {assessmentStartDate}
                </p>
              )}
            </div>

            {/* Gold hamburger menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-2 hover:opacity-80 transition-opacity"
                aria-label={t('Assessment menu')}
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
                      onClick={handleSaveAndExit}
                      className="w-full text-left px-6 font-body font-bold text-lg text-brand-charcoal leading-[50px] hover:bg-brand-gray-lightest transition-colors"
                    >
                      {t('Save & Exit')}
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

          {/* ── Progress Bar ── */}
          <div className="mt-10">
            <div className="h-[42px] w-full bg-brand-gray-lightest rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-gold rounded-full transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <p className="font-body font-semibold italic text-lg text-brand-charcoal text-center mt-3">
              {t('Completed')} {answeredCount} {t('of')} {totalQuestions} {t('questions')}
            </p>
          </div>

          {/* ── Error ── */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex justify-between items-center">
              <span className="font-body text-red-700">{error}</span>
              <button onClick={clearError} className="text-red-700 font-bold text-lg ml-4">×</button>
            </div>
          )}

          {/* ── Section Header ── */}
          <h2 className="font-heading font-medium text-[32px] leading-[41px] text-brand-teal mt-10 mb-6">
            {SECTION_LABELS[currentPage.section]?.[isEs ? 'es' : 'en'] || currentPage.section}
          </h2>

          {/* ── Page Content ── */}
          {currentPage.pageType === 'likert' && (
            <LikertPage
              questions={currentPage.questions}
              answers={answers}
              onSelect={handleLikertSelect}
              isEs={isEs}
            />
          )}

          {currentPage.pageType === 'abilities' && (
            <MultiSelectPage
              question={currentPage.questions[0]}
              options={ABILITIES_OPTIONS}
              maxSelections={3}
              customCount={2}
              initialValue={answers[currentPage.questions[0].id]?.multiple_choice_answer}
              onChange={(value) => saveAnswer(currentPage.questions[0].id, { multiple_choice_answer: value })}
            />
          )}

          {currentPage.pageType === 'people' && (
            <MultiSelectPage
              question={currentPage.questions[0]}
              options={PEOPLE_OPTIONS}
              maxSelections={2}
              customCount={2}
              initialValue={answers[currentPage.questions[0].id]?.multiple_choice_answer}
              onChange={(value) => saveAnswer(currentPage.questions[0].id, { multiple_choice_answer: value })}
            />
          )}

          {currentPage.pageType === 'causes' && (
            <MultiSelectPage
              question={currentPage.questions[0]}
              options={CAUSES_OPTIONS}
              maxSelections={2}
              customCount={2}
              initialValue={answers[currentPage.questions[0].id]?.multiple_choice_answer}
              onChange={(value) => saveAnswer(currentPage.questions[0].id, { multiple_choice_answer: value })}
            />
          )}

          {currentPage.pageType === 'text' && (
            <TextPage
              question={currentPage.questions[0]}
              answer={answers[currentPage.questions[0].id]}
              onTextChange={handleTextChange}
              isEs={isEs}
            />
          )}

          {/* ── Navigation ── */}
          <div className="flex justify-between items-center mt-10 mb-8">
            {currentPageIndex > 0 ? (
              <button
                onClick={goToPreviousPage}
                className="w-[175px] h-[50px] bg-brand-gray-light rounded-xl flex items-center justify-center gap-2 font-body font-bold text-lg text-brand-charcoal hover:bg-brand-gray-light/80 transition-colors"
              >
                <img src={leftArrowIcon} alt="" className="w-[11px] h-[15px]" />
                {t('Previous')}
              </button>
            ) : (
              <div className="w-[175px]" />
            )}

            <button
              onClick={handleSaveAndExit}
              disabled={isLoading}
              className="px-6 h-[50px] border border-brand-gray-light rounded-xl font-body font-bold text-lg text-brand-charcoal hover:bg-brand-gray-lightest disabled:opacity-50 transition-colors"
            >
              {t('Save & Exit')}
            </button>

            {isLastPage ? (
              <button
                onClick={handleSubmit}
                disabled={isLoading || !isCurrentPageComplete()}
                className="w-[175px] h-[50px] bg-brand-teal rounded-xl flex items-center justify-center gap-2 font-body font-bold text-lg text-white hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? t('Submitting...') : t('Submit')}
                {!isLoading && <img src={rightArrowIcon} alt="" className="w-[11px] h-[15px]" />}
              </button>
            ) : (
              <button
                onClick={goToNextPage}
                disabled={!isCurrentPageComplete()}
                className="w-[175px] h-[50px] bg-brand-teal rounded-xl flex items-center justify-center gap-2 font-body font-bold text-lg text-white hover:bg-brand-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {t('Next')}
                <img src={rightArrowIcon} alt="" className="w-[11px] h-[15px]" />
              </button>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

/* ────────────── Sub-components ────────────── */

function LikertPage({
  questions,
  answers,
  onSelect,
  isEs = false,
}: {
  questions: { id: string; question: string; question_es?: string }[];
  answers: Record<string, { numeric_value?: number }>;
  onSelect: (questionId: string, value: number) => void;
  isEs?: boolean;
}) {
  return (
    <div>
      {/* Column headers */}
      <div className="flex items-center justify-between mb-0">
        <span className="uppercase font-body font-bold text-base text-brand-gray-med tracking-wide">
          {isEs ? 'Declaraciones' : 'Statements'}
        </span>
        <span className="uppercase font-body font-bold text-base text-brand-gray-med tracking-wide mr-4">
          {isEs ? 'Respuestas' : 'Answers'}
        </span>
      </div>

      <hr className="border-brand-gray-light mb-0" />

      {questions.map((q) => {
        const selected = answers[q.id]?.numeric_value;
        return (
          <div key={q.id}>
            <div className="flex flex-col lg:flex-row lg:items-center py-6 gap-6">
              {/* Statement */}
              <p className="font-body font-bold text-[20px] leading-[30px] text-brand-charcoal lg:w-[393px] shrink-0">
                {(isEs && q.question_es) ? q.question_es : q.question}
              </p>

              {/* Likert scale */}
              <div className="flex items-center gap-3 flex-1 justify-end">
                <span className="font-body font-bold text-base text-brand-charcoal leading-[26px] w-[105px] text-left">
                  {isEs ? 'Casi Nunca' : 'Almost Never'}
                </span>
                <div className="flex gap-[15px]">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      onClick={() => onSelect(q.id, val)}
                      className={`w-[53px] h-[53px] rounded-full flex items-center justify-center font-body font-bold text-[20px] transition-colors cursor-pointer ${
                        selected === val
                          ? 'bg-brand-gold border-2 border-brand-gold text-white'
                          : 'bg-white border-2 border-brand-gray-light text-brand-charcoal hover:border-brand-gold/50'
                      }`}
                    >
                      {val}
                    </button>
                  ))}
                </div>
                <span className="font-body font-bold text-base text-brand-charcoal leading-[26px] w-[117px] text-right">
                  {isEs ? 'Casi Siempre' : 'Almost Always'}
                </span>
              </div>
            </div>
            <hr className="border-brand-gray-light" />
          </div>
        );
      })}
    </div>
  );
}

function TextPage({
  question,
  answer,
  onTextChange,
  isEs = false,
}: {
  question: { id: string; question: string; question_es?: string; default_text?: string; summary?: string };
  answer?: { text_value?: string };
  onTextChange: (questionId: string, value: string) => void;
  isEs?: boolean;
}) {
  return (
    <div>
      <p className="font-body font-bold text-[20px] leading-[30px] text-brand-charcoal mb-4">
        {(isEs && question.question_es) ? question.question_es : question.question}
      </p>

      {question.summary && (
        <p className="font-body text-base text-brand-gray-med italic mb-4">
          {question.summary}
        </p>
      )}

      {question.default_text && (
        <div className="bg-brand-gray-lightest rounded-lg p-4 mb-4">
          <p className="font-body text-sm text-brand-gray-med italic whitespace-pre-line">
            {question.default_text}
          </p>
        </div>
      )}

      <textarea
        className="w-full min-h-[200px] p-4 border border-brand-gray-light rounded-xl font-body text-base text-brand-charcoal resize-y focus:outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20 transition-colors"
        placeholder={isEs ? 'Ingrese su respuesta...' : 'Enter your answer...'}
        value={answer?.text_value || ''}
        onChange={(e) => onTextChange(question.id, e.target.value)}
      />
    </div>
  );
}
