import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { api } from './AuthContext';

export type WebhookEventType = 'assessment_completed' | 'user_registered';

export interface WebhookConfig {
  id: string;
  organization_id: string;
  event_type: WebhookEventType;
  webhook_url: string;
  is_active: boolean;
  has_secret: boolean;
  secret_masked?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookConfigCreated extends WebhookConfig {
  /** Plaintext signing secret. Returned only on create / regenerate. */
  secret_plaintext?: string | null;
}

export interface WebhookDelivery {
  id: string;
  webhook_config_id: string;
  event_type: string;
  status: 'pending' | 'success' | 'failed' | 'dead';
  http_status_code?: number | null;
  error_message?: string | null;
  attempts: number;
  next_retry_at?: string | null;
  created_at: string;
}

export interface WebhookTestResult {
  ok: boolean;
  status_code?: number | null;
  error?: string | null;
}

interface CreateInput {
  webhook_url: string;
  event_type: WebhookEventType;
  is_active?: boolean;
  generate_secret?: boolean;
}

interface UpdateInput {
  webhook_url?: string;
  is_active?: boolean;
  generate_secret?: boolean;
}

interface WebhookContextType {
  webhooks: WebhookConfig[];
  isLoading: boolean;
  loadError: string | null;
  loadWebhooks: () => Promise<void>;
  createWebhook: (input: CreateInput) => Promise<WebhookConfigCreated>;
  updateWebhook: (id: string, input: UpdateInput) => Promise<WebhookConfigCreated>;
  deleteWebhook: (id: string) => Promise<void>;
  testWebhook: (id: string) => Promise<WebhookTestResult>;
  fetchDeliveries: (id: string, params?: { status?: string; limit?: number; offset?: number }) => Promise<{ deliveries: WebhookDelivery[]; total_count: number }>;
}

const WebhookContext = createContext<WebhookContextType | undefined>(undefined);

export function WebhookProvider({ children }: { children: ReactNode }) {
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadWebhooks = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await api.get('/admin/webhooks');
      setWebhooks(res.data.webhooks);
    } catch (err: any) {
      setLoadError(err?.response?.data?.detail ?? 'Failed to load webhooks');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createWebhook = useCallback(async (input: CreateInput) => {
    const res = await api.post('/admin/webhooks', input);
    const created = res.data as WebhookConfigCreated;
    setWebhooks(prev => [...prev.filter(w => w.id !== created.id), created]);
    return created;
  }, []);

  const updateWebhook = useCallback(async (id: string, input: UpdateInput) => {
    const res = await api.put(`/admin/webhooks/${id}`, input);
    const updated = res.data as WebhookConfigCreated;
    setWebhooks(prev => prev.map(w => (w.id === id ? updated : w)));
    return updated;
  }, []);

  const deleteWebhook = useCallback(async (id: string) => {
    await api.delete(`/admin/webhooks/${id}`);
    setWebhooks(prev => prev.filter(w => w.id !== id));
  }, []);

  const testWebhook = useCallback(async (id: string) => {
    const res = await api.post(`/admin/webhooks/${id}/test`);
    return res.data as WebhookTestResult;
  }, []);

  const fetchDeliveries = useCallback(
    async (id: string, params?: { status?: string; limit?: number; offset?: number }) => {
      const res = await api.get(`/admin/webhooks/${id}/deliveries`, { params });
      return res.data as { deliveries: WebhookDelivery[]; total_count: number };
    },
    [],
  );

  return (
    <WebhookContext.Provider
      value={{
        webhooks,
        isLoading,
        loadError,
        loadWebhooks,
        createWebhook,
        updateWebhook,
        deleteWebhook,
        testWebhook,
        fetchDeliveries,
      }}
    >
      {children}
    </WebhookContext.Provider>
  );
}

export function useWebhooks() {
  const ctx = useContext(WebhookContext);
  if (!ctx) {
    throw new Error('useWebhooks must be used within a WebhookProvider');
  }
  return ctx;
}
