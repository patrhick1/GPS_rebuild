import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import './AssessmentWizard.css';

export function AssessmentWizard() {
  const {
    assessmentId,
    questions,
    answers,
    currentQuestionIndex,
    isLoading,
    error,
    startAssessment,
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

  useEffect(() => {
    // Start assessment if not already started
    if (!assessmentId && !isLoading) {
      startAssessment();
    }
  }, [assessmentId, isLoading, startAssessment]);

  const currentQuestion = questions[currentQuestionIndex];
  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : null;

  const handleLikertSelect = (value: number) => {
    if (currentQuestion) {
      saveAnswer(currentQuestion.id, { numeric_value: value });
    }
  };

  const handleTextChange = (value: string) => {
    if (currentQuestion) {
      saveAnswer(currentQuestion.id, { text_value: value });
    }
  };

  const handleSubmit = async () => {
    try {
      await submitAssessment();
      navigate('/assessment-results');
    } catch (err) {
      // Error handled by context
    }
  };

  const handleSaveAndExit = async () => {
    await saveProgress();
    navigate('/dashboard');
  };

  if (isLoading && !assessmentId) {
    return (
      <div className="assessment-loading">
        <div className="spinner">Loading...</div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="assessment-loading">
        <p>No questions available</p>
      </div>
    );
  }

  return (
    <div className="assessment-wizard">
      {/* Progress Bar */}
      <div className="assessment-progress">
        <div className="progress-info">
          <span>Question {progress.current} of {progress.total}</span>
          <span>{progress.percentage}% Complete</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
      </div>

      {/* Question Navigation Dots */}
      <div className="question-nav">
        {questions.map((q, idx) => (
          <button
            key={q.id}
            className={`nav-dot ${idx === currentQuestionIndex ? 'active' : ''} ${answers[q.id] ? 'answered' : ''}`}
            onClick={() => goToQuestion(idx)}
            title={`Question ${idx + 1}`}
          />
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}

      {/* Question Card */}
      <div className="question-card">
        <h2 className="question-text">{currentQuestion.question}</h2>
        
        {currentQuestion.summary && (
          <p className="question-summary">{currentQuestion.summary}</p>
        )}

        {/* Likert Scale (1-5) */}
        {currentQuestion.question_type_id === 'likert' && (
          <div className="likert-scale">
            <div className="likert-labels">
              <span>Strongly Disagree</span>
              <span>Strongly Agree</span>
            </div>
            <div className="likert-options">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  className={`likert-btn ${currentAnswer?.numeric_value === value ? 'selected' : ''}`}
                  onClick={() => handleLikertSelect(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Text Input */}
        {currentQuestion.question_type_id === 'text' && (
          <textarea
            className="text-answer"
            rows={6}
            placeholder={currentQuestion.default_text || 'Enter your answer...'}
            value={currentAnswer?.text_value || ''}
            onChange={(e) => handleTextChange(e.target.value)}
          />
        )}

        {/* Multiple Choice / Checkbox would go here */}
      </div>

      {/* Navigation Buttons */}
      <div className="assessment-nav">
        <button
          className="btn-secondary"
          onClick={goToPrevious}
          disabled={currentQuestionIndex === 0}
        >
          Previous
        </button>

        <div className="nav-center">
          <button
            className="btn-save-exit"
            onClick={handleSaveAndExit}
            disabled={isLoading}
          >
            Save & Exit
          </button>
        </div>

        {currentQuestionIndex < questions.length - 1 ? (
          <button
            className="btn-primary"
            onClick={goToNext}
            disabled={!currentAnswer}
          >
            Next
          </button>
        ) : (
          <button
            className="btn-primary btn-submit"
            onClick={handleSubmit}
            disabled={isLoading || !currentAnswer}
          >
            {isLoading ? 'Submitting...' : 'Submit Assessment'}
          </button>
        )}
      </div>
    </div>
  );
}
