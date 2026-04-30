import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { api, useAuth } from './AuthContext';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  link?: string;
  is_read: string;
  created_at: string;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  fetchNotifications: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

const POLL_INTERVAL = 30000; // 30 seconds

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isVerified = isAuthenticated && user?.email_verified === 'Y';

  const fetchUnreadCount = useCallback(async () => {
    if (!isVerified) return;
    try {
      const res = await api.get('/notifications/unread-count');
      setUnreadCount(res.data.count);
    } catch {
      // Silently fail — polling should not show errors
    }
  }, [isVerified]);

  const fetchNotifications = useCallback(async () => {
    if (!isVerified) return;
    setIsLoading(true);
    try {
      const res = await api.get('/notifications', { params: { limit: 20 } });
      setNotifications(res.data.notifications);
      setUnreadCount(res.data.unread_count);
    } catch {
      // Silently fail
    } finally {
      setIsLoading(false);
    }
  }, [isVerified]);

  const markAsRead = useCallback(async (id: string) => {
    try {
      await api.patch(`/notifications/${id}/read`);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: 'Y' } : n))
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // Silently fail
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await api.patch('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: 'Y' })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }, []);

  // Start/stop polling based on auth state
  useEffect(() => {
    if (isVerified) {
      fetchUnreadCount();
      intervalRef.current = setInterval(fetchUnreadCount, POLL_INTERVAL);
    } else {
      setNotifications([]);
      setUnreadCount(0);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isVerified, fetchUnreadCount]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        isLoading,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
