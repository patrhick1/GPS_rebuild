import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Track refresh promise to prevent multiple simultaneous refresh attempts
let refreshPromise: Promise<string> | null = null;

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important: sends httpOnly cookies
});

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  status: string;
  role?: string;
  organization_id?: string;
  organization_name?: string;
  is_primary_admin?: boolean;
}

interface ChurchRegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  org_name: string;
  org_city?: string;
  org_state?: string;
  org_country?: string;
}

interface ChurchUpgradeData {
  org_name: string;
  org_city?: string;
  org_state?: string;
  org_country?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (data: RegisterData) => Promise<void>;
  registerChurch: (data: ChurchRegisterData) => Promise<User>;
  upgradeToChurchAdmin: (data: ChurchUpgradeData) => Promise<User>;
  logout: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

interface RegisterData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  organization_key?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const userRef = useRef<User | null>(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem('access_token')
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if user is already logged in on mount using refresh token
  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Sync localStorage and axios Authorization header whenever accessToken changes
  useEffect(() => {
    if (accessToken) {
      localStorage.setItem('access_token', accessToken);
      api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    } else {
      localStorage.removeItem('access_token');
      delete api.defaults.headers.common['Authorization'];
    }
  }, [accessToken]);

  const checkAuthStatus = async () => {
    const stored = localStorage.getItem('access_token');

    // Apply stored token to header immediately — can't wait for useEffect
    if (stored) {
      api.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
    }

    try {
      if (!stored) {
        // No local token — try refresh cookie path
        const newToken = await refreshAccessToken();
        setAccessToken(newToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      }
      const response = await api.get('/auth/me');
      setUser(response.data);
    } catch {
      if (stored) {
        // Stored token rejected (expired) — fall back to refresh cookie
        try {
          const newToken = await refreshAccessToken();
          setAccessToken(newToken);
          api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
          const response = await api.get('/auth/me');
          setUser(response.data);
        } catch {
          setAccessToken(null);
          setUser(null);
        }
      } else {
        setAccessToken(null);
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const refreshAccessToken = async (): Promise<string> => {
    // If a refresh is already in progress, wait for it
    if (refreshPromise) {
      return refreshPromise;
    }

    // Create new refresh promise
    refreshPromise = (async () => {
      try {
        const response = await axios.post(
          `${API_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        return response.data.access_token;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  };

  // Add response interceptor for automatic token refresh
  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // If 402, check detail to distinguish no subscription vs expired/readonly
        if (error.response?.status === 402) {
          const detail = error.response?.data?.detail;
          if (detail === 'no_subscription' && userRef.current?.is_primary_admin) {
            // Only primary admins are redirected to billing — they're the ones who can subscribe
            window.location.href = '/admin/billing';
          }
          // For secondary admins or other 402s, let the error propagate so the component can handle it
          return Promise.reject(error);
        }

        // If 401 and not already retrying (skip for login endpoint — let it surface its own error)
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          !originalRequest.url?.endsWith('/auth/login')
        ) {
          originalRequest._retry = true;

          try {
            const newToken = await refreshAccessToken();
            setAccessToken(newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return api(originalRequest);
          } catch (refreshError) {
            // Refresh failed, logout user
            setAccessToken(null);
            setUser(null);
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(interceptor);
    };
  }, []);

  const fetchUser = async (): Promise<User> => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      return response.data;
    } catch (err) {
      setAccessToken(null);
      setUser(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string): Promise<User> => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token } = response.data;
      // Store in memory only - NOT localStorage
      setAccessToken(access_token);
      return await fetchUser();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await api.post('/auth/register', data);
      // Auto-login after registration
      await login(data.email, data.password);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const upgradeToChurchAdmin = async (data: ChurchUpgradeData): Promise<User> => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await api.post('/auth/upgrade/church', data);
      // Update user in context with fresh role/org data returned by the endpoint
      setUser(response.data);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upgrade failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const registerChurch = async (data: ChurchRegisterData): Promise<User> => {
    setError(null);
    setIsLoading(true);
    try {
      await api.post('/auth/register/church', data);
      return await login(data.email, data.password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.post('/auth/logout');
    } catch (err) {
      // Ignore error
    } finally {
      setAccessToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        accessToken,
        login,
        register,
        registerChurch,
        upgradeToChurchAdmin,
        logout,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { api };
