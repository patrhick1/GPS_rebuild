import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from './AuthContext';

interface Member {
  id: string;
  first_name?: string;
  last_name?: string;
  email: string;
  status: string;
  role?: string;
  joined_at: string;
  assessment_count: number;
  last_assessment_date?: string;
  phone_number?: string;
}

interface Invite {
  id: string;
  email: string;
  status: string;
  created_at: string;
  expires_at?: string;
  accepted_at?: string;
}

interface PendingMember {
  membership_id: string;
  user_id: string;
  first_name?: string;
  last_name?: string;
  email: string;
  requested_at: string;
}

interface ChurchStats {
  total_members: number;
  active_members: number;
  pending_members: number;
  total_assessments: number;
}

interface MemberListResponse {
  members: Member[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface AdminContextType {
  members: Member[];
  invites: Invite[];
  pending: PendingMember[];
  stats: ChurchStats | null;
  isLoading: boolean;
  error: string | null;
  totalPages: number;
  currentPage: number;
  fetchMembers: (page?: number, search?: string, status?: string) => Promise<void>;
  fetchInvites: () => Promise<void>;
  fetchPending: () => Promise<void>;
  fetchStats: () => Promise<void>;
  updateMember: (id: string, data: { role?: string; status?: string }) => Promise<void>;
  removeMember: (id: string) => Promise<void>;
  createInvite: (email: string) => Promise<void>;
  bulkInvite: (emails: string[]) => Promise<{ created: string[]; failed: any[] }>;
  uploadCSV: (file: File) => Promise<any>;
  resendInvite: (id: string) => Promise<void>;
  cancelInvite: (id: string) => Promise<void>;
  approvePending: (id: string) => Promise<void>;
  declinePending: (id: string) => Promise<void>;
  clearError: () => void;
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

export function AdminProvider({ children }: { children: ReactNode }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [pending, setPending] = useState<PendingMember[]>([]);
  const [stats, setStats] = useState<ChurchStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchMembers = useCallback(async (page = 1, search?: string, status?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = { page };
      if (search) params.search = search;
      if (status) params.status = status;
      
      const response = await api.get('/admin/members', { params });
      setMembers(response.data.members);
      setTotalPages(response.data.total_pages);
      setCurrentPage(response.data.page);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load members');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchInvites = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/invites');
      setInvites(response.data.invites);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load invites');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchPending = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/pending');
      setPending(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load pending requests');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/admin/stats');
      setStats(response.data);
    } catch (err: any) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  const updateMember = useCallback(async (id: string, data: { role?: string; status?: string }) => {
    await api.put(`/admin/members/${id}`, data);
  }, []);

  const removeMember = useCallback(async (id: string) => {
    await api.delete(`/admin/members/${id}`);
  }, []);

  const createInvite = useCallback(async (email: string) => {
    await api.post('/admin/invites', { email });
  }, []);

  const bulkInvite = useCallback(async (emails: string[]) => {
    const response = await api.post('/admin/invites/bulk', { emails });
    return response.data;
  }, []);

  const uploadCSV = useCallback(async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/admin/invites/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }, []);

  const resendInvite = useCallback(async (id: string) => {
    await api.post(`/admin/invites/${id}/resend`);
  }, []);

  const cancelInvite = useCallback(async (id: string) => {
    await api.delete(`/admin/invites/${id}`);
  }, []);

  const approvePending = useCallback(async (id: string) => {
    await api.post(`/admin/pending/${id}/approve`);
  }, []);

  const declinePending = useCallback(async (id: string) => {
    await api.post(`/admin/pending/${id}/decline`);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AdminContext.Provider
      value={{
        members,
        invites,
        pending,
        stats,
        isLoading,
        error,
        totalPages,
        currentPage,
        fetchMembers,
        fetchInvites,
        fetchPending,
        fetchStats,
        updateMember,
        removeMember,
        createInvite,
        bulkInvite,
        uploadCSV,
        resendInvite,
        cancelInvite,
        approvePending,
        declinePending,
        clearError
      }}
    >
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin() {
  const context = useContext(AdminContext);
  if (context === undefined) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
}
