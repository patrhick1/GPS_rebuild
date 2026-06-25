import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import axios from 'axios';
import { api } from './AuthContext';

function getApiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail || fallback;
  }
  return fallback;
}

interface Subscription {
  id: string;
  status: string;
  plan: string | null;
  quantity: number;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  cancel_at_period_end: string | null;
  canceled_at: string | null;
  stripe_subscription_id: string | null;
  organization: {
    id: string;
    name: string;
    card_brand: string | null;
    card_last_four: string | null;
  };
  upcoming_invoice: {
    amount_due: number;
    currency: string;
    due_date: number;
    period_start: number;
    period_end: number;
  } | null;
  payment_methods: PaymentMethod[];
}

interface PaymentMethod {
  id: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

interface Invoice {
  id: string;
  amount_paid: number;
  currency: string;
  status: string;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
  created: number;
}

interface Payment {
  id: string;
  amount: number;
  currency: string;
  status: string;
  description: string | null;
  receipt_url: string | null;
  created_at: string;
}

interface BillingConfig {
  publishable_key: string | null;
  prices: {
    monthly: string | null;
    yearly: string | null;
  };
}

export interface PromotionCodePreview {
  code: string;
  subtotal: number;
  discount_total: number;
  total: number;
  currency: string;
  label: string;
  duration: string | null;
}

interface BillingContextType {
  subscription: Subscription | null;
  invoices: Invoice[];
  payments: Payment[];
  config: BillingConfig | null;
  isLoading: boolean;
  error: string | null;
  fetchSubscription: () => Promise<void>;
  fetchInvoices: () => Promise<void>;
  fetchConfig: () => Promise<void>;
  previewPromotionCode: (code: string, plan: string, quantity?: number) => Promise<PromotionCodePreview>;
  subscribe: (plan: string, paymentMethodId: string, quantity?: number, promotionCode?: string) => Promise<{ client_secret?: string; requires_action: boolean }>;
  cancelSubscription: (atPeriodEnd?: boolean) => Promise<void>;
  reactivateSubscription: () => Promise<void>;
  addPaymentMethod: (paymentMethodId: string) => Promise<void>;
  removePaymentMethod: (paymentMethodId: string) => Promise<void>;
  setDefaultPaymentMethod: (paymentMethodId: string) => Promise<void>;
  openBillingPortal: () => Promise<void>;
}

const BillingContext = createContext<BillingContextType | undefined>(undefined);

export function BillingProvider({ children }: { children: ReactNode }) {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [config, setConfig] = useState<BillingConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/billing/subscription');
      setSubscription(data.status === 'none' ? null : data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to fetch subscription'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchInvoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/billing/invoices');
      setInvoices(data.stripe_invoices || []);
      setPayments(data.payments || []);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to fetch invoices'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const { data } = await api.get('/billing/config');
      setConfig(data);
    } catch (err) {
      console.error('Failed to fetch billing config:', err);
    }
  }, []);

  const previewPromotionCode = useCallback(async (code: string, plan: string, quantity = 1) => {
    try {
      const { data } = await api.post('/billing/promotion-code/preview', {
        code,
        plan,
        quantity,
      });
      return data as PromotionCodePreview;
    } catch (err: unknown) {
      const message = getApiErrorMessage(err, 'Unable to apply this promotion code');
      throw new Error(message);
    }
  }, []);

  const subscribe = useCallback(async (
    plan: string,
    paymentMethodId: string,
    quantity = 1,
    promotionCode?: string,
  ) => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.post('/billing/subscribe', {
        plan,
        payment_method_id: paymentMethodId,
        quantity,
        promotion_code: promotionCode || null,
      });
      await fetchSubscription();
      return data;
    } catch (err: unknown) {
      const message = getApiErrorMessage(err, 'Failed to create subscription');
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const cancelSubscription = useCallback(async (atPeriodEnd = true) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/billing/subscription/cancel?at_period_end=${atPeriodEnd}`);
      await fetchSubscription();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to cancel subscription'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const reactivateSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post('/billing/subscription/reactivate');
      await fetchSubscription();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to reactivate subscription'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const addPaymentMethod = useCallback(async (paymentMethodId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/billing/payment-method?payment_method_id=${paymentMethodId}&set_default=true`);
      await fetchSubscription();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to add payment method'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const removePaymentMethod = useCallback(async (paymentMethodId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.delete(`/billing/payment-method/${paymentMethodId}`);
      await fetchSubscription();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to remove payment method'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const setDefaultPaymentMethod = useCallback(async (paymentMethodId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/billing/payment-method?payment_method_id=${paymentMethodId}&set_default=true`);
      await fetchSubscription();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to set default payment method'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const openBillingPortal = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.post('/billing/portal');
      window.location.href = data.url;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to open billing portal'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <BillingContext.Provider value={{
      subscription,
      invoices,
      payments,
      config,
      isLoading,
      error,
      fetchSubscription,
      fetchInvoices,
      fetchConfig,
      previewPromotionCode,
      subscribe,
      cancelSubscription,
      reactivateSubscription,
      addPaymentMethod,
      removePaymentMethod,
      setDefaultPaymentMethod,
      openBillingPortal
    }}>
      {children}
    </BillingContext.Provider>
  );
}

export function useBilling() {
  const context = useContext(BillingContext);
  if (context === undefined) {
    throw new Error('useBilling must be used within a BillingProvider');
  }
  return context;
}
