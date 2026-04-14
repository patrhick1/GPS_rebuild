import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { api } from './AuthContext';

interface Gift {
  id: string;
  name: string;
  short_code: string;
  score: number;
  description: string;
}

interface Passion {
  id: string;
  name: string;
  short_code: string;
  score: number;
  description: string;
}

interface LatestAssessment {
  id: string;
  completed_at: string;
  top_gifts?: Gift[];
  top_passions?: Passion[];
}

interface Organization {
  id: string;
  name: string;
  role?: string;
}

interface PendingOrganization {
  id: string;
  name: string;
  status: 'pending' | 'declined';
}

interface DashboardSummary {
  user: {
    id: string;
    first_name?: string;
    last_name?: string;
    email: string;
  };
  latest_assessment?: LatestAssessment;
  stats: {
    total_assessments: number;
    has_organization: boolean;
  };
  organization?: Organization;
  pending_organization?: PendingOrganization;
}

interface AssessmentHistoryItem {
  id: string;
  status: string;
  instrument_type: string;
  completed_at?: string;
  created_at: string;
  progress_percentage: number;
  top_gifts: { name: string; short_code: string; score: number }[];
  top_passions: { name: string; short_code: string; score: number }[];
  myimpact_score?: number;
  character_score?: number;
  calling_score?: number;
}

interface AssessmentDetail {
  id: string;
  completed_at?: string;
  created_at: string;
  gifts: { id: string; name: string; short_code: string; score: number }[];
  passions: { id: string; name: string; short_code: string; score: number }[];
  selections: {
    people: string[];
    causes: string[];
    abilities: string[];
  };
  stories: {
    gift?: string;
    ability?: string;
    passion?: string;
    influencing?: string;
    onechange?: string;
    closestpeople?: string;
    oneregret?: string;
  };
}

interface ComparisonResult {
  assessment_1: {
    id: string;
    completed_at?: string;
    gifts: { id: string; name: string; short_code: string; score: number }[];
    passions: { id: string; name: string; short_code: string; score: number }[];
  };
  assessment_2: {
    id: string;
    completed_at?: string;
    gifts: { id: string; name: string; short_code: string; score: number }[];
    passions: { id: string; name: string; short_code: string; score: number }[];
  };
}

interface ChurchSearchResult {
  id: string;
  name: string;
  city?: string;
  state?: string;
  member_count: number;
}

interface DashboardContextType {
  summary: DashboardSummary | null;
  history: AssessmentHistoryItem[];
  myimpactHistory: AssessmentHistoryItem[];
  isLoading: boolean;
  error: string | null;
  fetchSummary: () => Promise<void>;
  fetchHistory: () => Promise<void>;
  fetchMyImpactHistory: () => Promise<void>;
  getAssessmentDetail: (id: string) => Promise<AssessmentDetail>;
  compareAssessments: (id1: string, id2: string) => Promise<ComparisonResult>;
  exportCSV: () => Promise<void>;
  searchChurches: (query: string) => Promise<ChurchSearchResult[]>;
  requestChurchLink: (organizationId: string) => Promise<void>;
  leaveOrganization: () => Promise<void>;
  clearError: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [history, setHistory] = useState<AssessmentHistoryItem[]>([]);
  const [myimpactHistory, setMyImpactHistory] = useState<AssessmentHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/dashboard/summary');
      setSummary(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/dashboard/assessments?instrument_type=gps');
      setHistory(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchMyImpactHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/dashboard/assessments?instrument_type=myimpact');
      setMyImpactHistory(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load MyImpact history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getAssessmentDetail = useCallback(async (id: string): Promise<AssessmentDetail> => {
    const response = await api.get(`/dashboard/assessments/${id}`);
    return response.data;
  }, []);

  const compareAssessments = useCallback(async (id1: string, id2: string): Promise<ComparisonResult> => {
    const response = await api.post('/dashboard/compare', {
      assessment_id_1: id1,
      assessment_id_2: id2
    });
    return response.data;
  }, []);

  const exportCSV = useCallback(async () => {
    const response = await api.get('/dashboard/export/csv', {
      responseType: 'blob'
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', response.headers['content-disposition']?.split('filename=')[1] || 'assessments.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, []);

  const searchChurches = useCallback(async (query: string): Promise<ChurchSearchResult[]> => {
    const response = await api.get('/dashboard/churches/search', {
      params: { query }
    });
    return response.data;
  }, []);

  const requestChurchLink = useCallback(async (organizationId: string) => {
    await api.post('/dashboard/link-request', {
      organization_id: organizationId
    });
    // Refresh summary to show updated status
    await fetchSummary();
  }, [fetchSummary]);

  const leaveOrganization = useCallback(async () => {
    await api.post('/dashboard/leave-organization');
    // Refresh summary
    await fetchSummary();
  }, [fetchSummary]);

  const clearError = useCallback(() => setError(null), []);

  return (
    <DashboardContext.Provider
      value={{
        summary,
        history,
        myimpactHistory,
        isLoading,
        error,
        fetchSummary,
        fetchHistory,
        fetchMyImpactHistory,
        getAssessmentDetail,
        compareAssessments,
        exportCSV,
        searchChurches,
        requestChurchLink,
        leaveOrganization,
        clearError
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}
