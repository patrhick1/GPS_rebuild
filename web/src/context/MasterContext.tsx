import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from './AuthContext';

interface SystemStats {
  total_users: number;
  total_churches: number;
  total_assessments: number;
  active_churches: number;
  recent_stats: {
    "30_days": { new_users: number; assessments: number };
    "90_days": { new_users: number; assessments: number };
    "365_days": { new_users: number; assessments: number };
  };
}

interface Church {
  id: string;
  name: string;
  key: string;
  city?: string;
  state?: string;
  country?: string;
  member_count: number;
  assessment_count: number;
  admins: { id: string; email: string; name: string }[];
  last_activity?: string;
  created_at: string;
}

interface User {
  id: string;
  first_name?: string;
  last_name?: string;
  email: string;
  status: string;
  organization?: { id: string; name: string; role?: string };
  assessment_count: number;
  created_at: string;
}

interface AuditEntry {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  action: string;
  target_type?: string;
  target_id?: string;
  details?: any;
  created_at: string;
}

interface MasterContextType {
  stats: SystemStats | null;
  churches: Church[];
  users: User[];
  auditLog: AuditEntry[];
  isLoading: boolean;
  error: string | null;
  totalChurchPages: number;
  totalUserPages: number;
  totalAuditPages: number;
  fetchStats: () => Promise<void>;
  fetchChurches: (page?: number, search?: string) => Promise<void>;
  fetchUsers: (page?: number, search?: string) => Promise<void>;
  fetchAuditLog: (page?: number, filters?: any) => Promise<void>;
  addChurchAdmin: (churchId: string, userId: string) => Promise<void>;
  removeChurchAdmin: (churchId: string, userId: string) => Promise<void>;
  impersonateUser: (userId: string, reason: string) => Promise<string>;
  exportData: (type: string, filters?: any) => Promise<void>;
  clearError: () => void;
}

const MasterContext = createContext<MasterContextType | undefined>(undefined);

export function MasterProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [churches, setChurches] = useState<Church[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalChurchPages, setTotalChurchPages] = useState(1);
  const [totalUserPages, setTotalUserPages] = useState(1);
  const [totalAuditPages, setTotalAuditPages] = useState(1);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/master/stats');
      setStats(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load stats');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchChurches = useCallback(async (page = 1, search?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = { page };
      if (search) params.search = search;
      
      const response = await api.get('/master/churches', { params });
      setChurches(response.data.churches);
      setTotalChurchPages(response.data.total_pages);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load churches');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchUsers = useCallback(async (page = 1, search?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = { page };
      if (search) params.search = search;
      
      const response = await api.get('/master/users', { params });
      setUsers(response.data.users);
      setTotalUserPages(response.data.total_pages);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAuditLog = useCallback(async (page = 1, filters?: any) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = { page, ...filters };
      
      const response = await api.get('/master/audit-log', { params });
      setAuditLog(response.data.entries);
      setTotalAuditPages(response.data.total_pages);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load audit log');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const addChurchAdmin = useCallback(async (churchId: string, userId: string) => {
    await api.post(`/master/churches/${churchId}/admins/${userId}`);
  }, []);

  const removeChurchAdmin = useCallback(async (churchId: string, userId: string) => {
    await api.delete(`/master/churches/${churchId}/admins/${userId}`);
  }, []);

  const impersonateUser = useCallback(async (userId: string, reason: string): Promise<string> => {
    const response = await api.post('/master/impersonate', {
      user_id: userId,
      reason
    });
    return response.data.token;
  }, []);

  const exportData = useCallback(async (type: string, filters?: any) => {
    const response = await api.post('/master/export', {
      export_type: type,
      ...filters
    }, {
      responseType: 'blob'
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `export_${type}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <MasterContext.Provider
      value={{
        stats,
        churches,
        users,
        auditLog,
        isLoading,
        error,
        totalChurchPages,
        totalUserPages,
        totalAuditPages,
        fetchStats,
        fetchChurches,
        fetchUsers,
        fetchAuditLog,
        addChurchAdmin,
        removeChurchAdmin,
        impersonateUser,
        exportData,
        clearError
      }}
    >
      {children}
    </MasterContext.Provider>
  );
}

export function useMaster() {
  const context = useContext(MasterContext);
  if (context === undefined) {
    throw new Error('useMaster must be used within a MasterProvider');
  }
  return context;
}
