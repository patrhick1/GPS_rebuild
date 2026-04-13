import { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect, type ReactNode } from 'react';
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
  section?: string;
  question_type_name?: string;  // "likert", "multiple_choice", "text"
  type_name?: string;           // "Spiritual Gift", "Influencing Style", "Story"
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

// MyImpact specific types
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

interface MyImpactResults {
  character: CharacterScores;
  calling: CallingScores;
  myimpact_score: number;
}

// GPS page-based navigation types
type GPSSection = 'gifts' | 'passion' | 'story';
type PageType = 'likert' | 'abilities' | 'people' | 'causes' | 'text';

interface AssessmentPage {
  section: GPSSection;
  pageType: PageType;
  questions: Question[];
}

interface AssessmentContextType {
  assessmentId: string | null;
  instrumentType: 'gps' | 'myimpact' | null;
  questions: Question[];
  answers: Record<string, Answer>;
  currentQuestionIndex: number;
  isLoading: boolean;
  error: string | null;
  results: GradedResults | null;
  myimpactResults: MyImpactResults | null;
  // GPS page-based navigation
  pages: AssessmentPage[];
  currentPageIndex: number;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  answeredCount: number;
  assessmentStartDate: string | null;
  // Shared
  fetchResults: (id: string) => Promise<void>;
  startAssessment: (type?: 'gps' | 'myimpact') => Promise<void>;
  continueAssessment: (id: string) => Promise<void>;
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

function buildPages(questions: Question[]): AssessmentPage[] {
  const pages: AssessmentPage[] = [];
  let likertBatch: Question[] = [];
  let currentSection: GPSSection = 'gifts';

  const flush = () => {
    if (likertBatch.length > 0) {
      pages.push({ section: currentSection, pageType: 'likert', questions: [...likertBatch] });
      likertBatch = [];
    }
  };

  for (const q of questions) {
    const typeName = q.type_name || '';
    const qtypeName = q.question_type_name || '';
    const passion = q.passion_type || '';

    // Determine section
    let section: GPSSection = 'gifts';
    if (typeName === 'Influencing Style') section = 'passion';
    else if (typeName === 'Story') section = 'story';

    // Determine page type
    let pageType: PageType = 'likert';
    if (qtypeName === 'text') {
      pageType = 'text';
    } else if (qtypeName === 'multiple_choice') {
      if (passion === 'People') pageType = 'people';
      else if (passion === 'Cause') pageType = 'causes';
      else pageType = 'abilities';
    }

    if (pageType === 'likert') {
      // If section changed, flush previous batch
      if (section !== currentSection && likertBatch.length > 0) {
        flush();
      }
      currentSection = section;
      likertBatch.push(q);
      if (likertBatch.length === 5) {
        flush();
      }
    } else {
      // Non-likert: flush any pending likert batch, then add as single-question page
      flush();
      currentSection = section;
      pages.push({ section, pageType, questions: [q] });
    }
  }

  // Flush any remaining likert questions
  flush();

  return pages;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [instrumentType, setInstrumentType] = useState<'gps' | 'myimpact' | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<GradedResults | null>(null);
  const [myimpactResults, setMyImpactResults] = useState<MyImpactResults | null>(null);
  const [assessmentStartDate, setAssessmentStartDate] = useState<string | null>(null);

  // Build pages from questions (GPS only)
  const pages = useMemo(() => {
    if (instrumentType !== 'gps' || questions.length === 0) return [];
    return buildPages(questions);
  }, [questions, instrumentType]);

  // Count answered questions
  const answeredCount = useMemo(() => {
    return Object.keys(answers).filter(key => {
      const a = answers[key];
      return a.numeric_value != null || a.text_value || a.multiple_choice_answer;
    }).length;
  }, [answers]);

  const fetchResults = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const gradeResponse = await api.get(`/assessments/${id}/grade`);
      // Determine instrument type from response shape
      if (gradeResponse.data.character && gradeResponse.data.calling) {
        setMyImpactResults(gradeResponse.data);
        setInstrumentType('myimpact');
      } else {
        setResults(gradeResponse.data);
        setInstrumentType('gps');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load results');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const startAssessment = useCallback(async (type: 'gps' | 'myimpact' = 'gps') => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post(`/assessments/start?instrument_type=${type}`);
      setAssessmentId(response.data.assessment_id);
      setInstrumentType(response.data.instrument_type);
      setQuestions(response.data.questions);
      setAnswers({});
      setCurrentQuestionIndex(0);
      setCurrentPageIndex(0);
      setResults(null);
      setMyImpactResults(null);
      setAssessmentStartDate(new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' }));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start assessment');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const continueAssessment = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get(`/assessments/${id}/continue`);
      setAssessmentId(response.data.assessment_id);
      setInstrumentType(response.data.instrument_type);
      setQuestions(response.data.questions);

      // Populate answers from saved data
      const savedAnswers: Record<string, Answer> = {};
      if (response.data.saved_answers) {
        for (const sa of response.data.saved_answers) {
          savedAnswers[sa.question_id] = {
            question_id: sa.question_id,
            numeric_value: sa.numeric_value,
            text_value: sa.text_value,
            multiple_choice_answer: sa.multiple_choice_answer,
          };
        }
      }
      setAnswers(savedAnswers);

      // Find first page with unanswered questions
      if (response.data.instrument_type === 'gps') {
        const builtPages = buildPages(response.data.questions);
        let resumePageIndex = 0;
        for (let i = 0; i < builtPages.length; i++) {
          const pageQuestions = builtPages[i].questions;
          const allAnswered = pageQuestions.every((q: Question) => {
            const a = savedAnswers[q.id];
            return a && (a.numeric_value != null || a.text_value || a.multiple_choice_answer);
          });
          if (!allAnswered) {
            resumePageIndex = i;
            break;
          }
          resumePageIndex = i + 1;
        }
        setCurrentPageIndex(Math.min(resumePageIndex, builtPages.length - 1));
      } else {
        // MyImpact: find first unanswered question
        const qs = response.data.questions;
        let resumeIdx = 0;
        for (let i = 0; i < qs.length; i++) {
          if (!savedAnswers[qs[i].id]) {
            resumeIdx = i;
            break;
          }
          resumeIdx = i + 1;
        }
        setCurrentQuestionIndex(Math.min(resumeIdx, qs.length - 1));
      }

      setResults(null);
      setMyImpactResults(null);
      setAssessmentStartDate(null); // Could parse from assessment created_at if needed
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to continue assessment');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-save: debounced save after each answer change
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const answersRef = useRef(answers);
  answersRef.current = answers;

  const triggerAutoSave = useCallback(() => {
    if (!assessmentId) return;
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        const answersArray = Object.values(answersRef.current);
        await api.post(`/assessments/${assessmentId}/save-progress`, {
          answers: answersArray
        });
      } catch {
        // Silent fail for auto-save — don't disrupt the user
      }
    }, 2000); // 2-second debounce
  }, [assessmentId]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
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
    triggerAutoSave();
  }, [triggerAutoSave]);

  // MyImpact question-level navigation (kept for compatibility)
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

  // GPS page-level navigation
  const goToNextPage = useCallback(() => {
    if (currentPageIndex < pages.length - 1) {
      setCurrentPageIndex(prev => prev + 1);
    }
  }, [currentPageIndex, pages.length]);

  const goToPreviousPage = useCallback(() => {
    if (currentPageIndex > 0) {
      setCurrentPageIndex(prev => prev - 1);
    }
  }, [currentPageIndex]);

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
      await api.post(`/assessments/${assessmentId}/submit`, {
        answers: answersArray
      });

      // Load full graded results based on instrument type
      const gradeResponse = await api.get(`/assessments/${assessmentId}/grade`);

      if (instrumentType === 'myimpact') {
        setMyImpactResults(gradeResponse.data);
      } else {
        setResults(gradeResponse.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit assessment');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [assessmentId, answers, instrumentType]);

  const clearError = useCallback(() => setError(null), []);

  // Progress: for GPS use answeredCount, for MyImpact use question index
  const progress = useMemo(() => {
    if (instrumentType === 'gps') {
      return {
        current: answeredCount,
        total: questions.length,
        percentage: questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0
      };
    }
    return {
      current: currentQuestionIndex + 1,
      total: questions.length,
      percentage: questions.length > 0 ? Math.round(((currentQuestionIndex + 1) / questions.length) * 100) : 0
    };
  }, [instrumentType, answeredCount, currentQuestionIndex, questions.length]);

  return (
    <AssessmentContext.Provider
      value={{
        assessmentId,
        instrumentType,
        questions,
        answers,
        currentQuestionIndex,
        isLoading,
        error,
        results,
        myimpactResults,
        pages,
        currentPageIndex,
        goToNextPage,
        goToPreviousPage,
        answeredCount,
        assessmentStartDate,
        fetchResults,
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
