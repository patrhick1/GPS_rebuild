import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from './AuthContext';

interface Question {
  id: string;
  question: string;
  question_es?: string;
  order: number;
  type_id: string;
  question_type_id: string;
  passion_type?: string;
  default_text?: string;
  summary?: string;
}

interface Answer {
  question_id: string;
  multiple_choice_answer?: string;
  numeric_value?: number;
  text_value?: string;
}

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

interface AssessmentContextType {
  assessmentId: string | null;
  questions: Question[];
  answers: Record<string, Answer>;
  currentQuestionIndex: number;
  isLoading: boolean;
  error: string | null;
  results: GradedResults | null;
  startAssessment: () => Promise<void>;
  saveAnswer: (questionId: string, answer: Partial<Answer>) => void;
  goToNext: () => void;
  goToPrevious: () => void;
  goToQuestion: (index: number) => void;
  submitAssessment: () => Promise<void>;
  saveProgress: () => Promise<void>;
  clearError: () => void;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<GradedResults | null>(null);

  const startAssessment = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('/assessments/start');
      setAssessmentId(response.data.assessment_id);
      setQuestions(response.data.questions);
      setAnswers({});
      setCurrentQuestionIndex(0);
      setResults(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start assessment');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const saveAnswer = useCallback((questionId: string, answer: Partial<Answer>) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        question_id: questionId,
        ...answer
      }
    }));
  }, []);

  const goToNext = useCallback(() => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  }, [currentQuestionIndex, questions.length]);

  const goToPrevious = useCallback(() => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  }, [currentQuestionIndex]);

  const goToQuestion = useCallback((index: number) => {
    if (index >= 0 && index < questions.length) {
      setCurrentQuestionIndex(index);
    }
  }, [questions.length]);

  const saveProgress = useCallback(async () => {
    if (!assessmentId) return;
    
    setIsLoading(true);
    try {
      const answersArray = Object.values(answers);
      await api.post(`/assessments/${assessmentId}/save-progress`, {
        answers: answersArray
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save progress');
    } finally {
      setIsLoading(false);
    }
  }, [assessmentId, answers]);

  const submitAssessment = useCallback(async () => {
    if (!assessmentId) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const answersArray = Object.values(answers);
      const response = await api.post(`/assessments/${assessmentId}/submit`, {
        answers: answersArray
      });
      
      // Load full graded results
      const gradeResponse = await api.get(`/assessments/${assessmentId}/grade`);
      setResults(gradeResponse.data);
      
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit assessment');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [assessmentId, answers]);

  const clearError = useCallback(() => setError(null), []);

  const progress = {
    current: currentQuestionIndex + 1,
    total: questions.length,
    percentage: questions.length > 0 ? Math.round(((currentQuestionIndex + 1) / questions.length) * 100) : 0
  };

  return (
    <AssessmentContext.Provider
      value={{
        assessmentId,
        questions,
        answers,
        currentQuestionIndex,
        isLoading,
        error,
        results,
        startAssessment,
        saveAnswer,
        goToNext,
        goToPrevious,
        goToQuestion,
        submitAssessment,
        saveProgress,
        clearError,
        progress
      }}
    >
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment() {
  const context = useContext(AssessmentContext);
  if (context === undefined) {
    throw new Error('useAssessment must be used within an AssessmentProvider');
  }
  return context;
}
