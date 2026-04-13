import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export function MyImpactWizard() {
  const {
    assessmentId,
    instrumentType,
    questions,
    answers,
    currentQuestionIndex,
    isLoading,
    error,
    startAssessment,
    continueAssessment,
    saveAnswer,
    goToNext,
    goToPrevious,
    goToQuestion,
    submitAssessment,
    saveProgress,
    clearError,
    progress
  } = useAssessment();

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const continueId = searchParams.get('continue');

  useEffect(() => {
    if (continueId) {
      if (!assessmentId && !isLoading) {
        continueAssessment(continueId);
      }
    } else if (!assessmentId && !isLoading) {
      startAssessment('myimpact');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [continueId, assessmentId, isLoading]);

  useEffect(() => {
    if (instrumentType && instrumentType !== 'myimpact') {
      navigate('/assessment');
    }
  }, [instrumentType, navigate]);

  const currentQuestion = questions[currentQuestionIndex];
  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : null;

  const getSectionHeader = () => {
    if (!currentQuestion) return null;
    const order = currentQuestion.order;
    if (order <= 9) {
      return {
        title: 'Character',
        subtitle: 'Fruit of the Spirit',
        description: 'But the Holy Spirit produces this kind of fruit in our lives: love, joy, peace, patience, kindness, goodness, faithfulness, gentleness, and self-control. Galatians 5:22-23',
      };
    } else {
      return {
        title: 'Calling',
        subtitle: 'Your Unique Design',
        description: "We are God's handiwork, created in Christ Jesus to do good works, which God prepared in advance for us to do. Ephesians 2:10",
      };
    }
  };

  const handleLikertSelect = (value: number) => {
    if (currentQuestion) {
      saveAnswer(currentQuestion.id, { numeric_value: value });
    }
  };

  const handleSubmit = async () => {
    try {
      await submitAssessment();
      navigate('/myimpact-results');
    } catch {
      // Error handled by context
    }
  };

  const handleSaveAndExit = async () => {
    await saveProgress();
    navigate('/dashboard');
  };

  if (isLoading && !assessmentId) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">Loading MyImpact Assessment...</p>
        </main>
        <Footer />
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="font-body text-lg text-brand-gray-med">No questions available</p>
        </main>
        <Footer />
      </div>
    );
  }

  const sectionHeader = getSectionHeader();

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 bg-white">
        <section className="max-w-[800px] mx-auto px-6 py-12">
          <button
            onClick={handleSaveAndExit}
            className="inline-flex items-center gap-1 font-body font-bold text-sm text-brand-teal hover:text-brand-teal/80 transition-colors mb-4"
          >
            <span className="text-base">←</span> Back to Dashboard
          </button>
          {/* Section Header */}
          {sectionHeader && (
            <div className="text-center mb-8">
              <h1 className="font-heading font-black text-[40px] text-brand-charcoal">
                {sectionHeader.title}
              </h1>
              <h2 className="font-heading font-medium text-2xl text-brand-teal mt-1">
                {sectionHeader.subtitle}
              </h2>
              <p className="font-body italic text-base text-brand-gray-med mt-3 max-w-[600px] mx-auto">
                {sectionHeader.description}
              </p>
            </div>
          )}

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between mb-1">
              <span className="font-body text-sm text-brand-gray-med">
                Question {progress.current} of {progress.total}
              </span>
              <span className="font-body text-sm text-brand-gray-med">
                {progress.percentage}% Complete
              </span>
            </div>
            <div className="h-3 bg-brand-gray-lightest rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-teal rounded-full transition-all duration-300"
                style={{ width: `${progress.percentage}%` }}
              />
            </div>
          </div>

          {/* Question Navigation Dots */}
          <div className="flex flex-wrap gap-1.5 justify-center mb-8">
            {questions.map((q, idx) => (
              <button
                key={q.id}
                className={`w-3 h-3 rounded-full transition-colors ${
                  idx === currentQuestionIndex
                    ? 'bg-brand-teal scale-125'
                    : answers[q.id]
                      ? 'bg-brand-teal/40'
                      : 'bg-brand-gray-light'
                }`}
                onClick={() => goToQuestion(idx)}
                title={`Question ${idx + 1}`}
              />
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex justify-between items-center">
              <span className="font-body text-red-700">{error}</span>
              <button onClick={clearError} className="text-red-700 font-bold text-lg ml-4">×</button>
            </div>
          )}

          {/* Question Card */}
          <div className="bg-brand-gray-lightest rounded-xl p-8 mb-8">
            <p className="font-body text-sm uppercase text-brand-gray-med tracking-wide mb-2">
              Question {currentQuestion.order}
            </p>
            <h2 className="font-body font-bold text-xl text-brand-charcoal mb-4">
              {currentQuestion.question}
            </h2>

            {currentQuestion.default_text && (
              <p className="font-body text-sm italic text-brand-gray-med mb-6">
                {currentQuestion.default_text}
              </p>
            )}

            {/* 1-10 Likert Scale */}
            <div>
              <div className="flex justify-between mb-3">
                <span className="font-body text-sm text-brand-gray-med">1 = Not true of me</span>
                <span className="font-body text-sm text-brand-gray-med">10 = Consistently true of me</span>
              </div>
              <div className="flex gap-2 justify-center flex-wrap">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
                  <button
                    key={value}
                    className={`w-[48px] h-[48px] rounded-full flex items-center justify-center font-body font-bold text-lg transition-colors ${
                      currentAnswer?.numeric_value === value
                        ? 'bg-brand-teal text-white border-2 border-brand-teal'
                        : 'bg-white border-2 border-brand-gray-light text-brand-charcoal hover:border-brand-teal/50'
                    }`}
                    onClick={() => handleLikertSelect(value)}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center">
            <button
              onClick={goToPrevious}
              disabled={currentQuestionIndex === 0}
              className="px-6 py-2.5 bg-brand-gray-light rounded-xl font-body font-bold text-base text-brand-charcoal disabled:opacity-50 disabled:cursor-not-allowed hover:bg-brand-gray-light/80 transition-colors"
            >
              Previous
            </button>

            <button
              onClick={handleSaveAndExit}
              disabled={isLoading}
              className="px-6 py-2.5 border border-brand-gray-light rounded-xl font-body font-bold text-base text-brand-charcoal hover:bg-brand-gray-lightest disabled:opacity-50 transition-colors"
            >
              Save & Exit
            </button>

            {currentQuestionIndex < questions.length - 1 ? (
              <button
                onClick={goToNext}
                disabled={!currentAnswer}
                className="px-6 py-2.5 bg-brand-teal rounded-xl font-body font-bold text-base text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-brand-teal/90 transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isLoading || !currentAnswer}
                className="px-6 py-2.5 bg-brand-teal rounded-xl font-body font-bold text-base text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-brand-teal/90 transition-colors"
              >
                {isLoading ? 'Submitting...' : 'Submit'}
              </button>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
