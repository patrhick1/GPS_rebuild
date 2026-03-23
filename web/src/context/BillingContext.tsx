import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

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
  subscribe: (plan: string, paymentMethodId: string, quantity?: number) => Promise<{ client_secret?: string; requires_action: boolean }>;
  cancelSubscription: (atPeriodEnd?: boolean) => Promise<void>;
  reactivateSubscription: () => Promise<void>;
  addPaymentMethod: (paymentMethodId: string) => Promise<void>;
  removePaymentMethod: (paymentMethodId: string) => Promise<void>;
}

const BillingContext = createContext<BillingContextType | undefined>(undefined);

export function BillingProvider({ children }: { children: ReactNode }) {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [config, setConfig] = useState<BillingConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => localStorage.getItem('access_token');

  const fetchSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/billing/subscription', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch subscription');
      
      const data = await response.json();
      setSubscription(data.status === 'none' ? null : data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchInvoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/billing/invoices', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch invoices');
      
      const data = await response.json();
      setInvoices(data.stripe_invoices || []);
      setPayments(data.payments || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const response = await fetch('/api/billing/config', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch config');
      
      const data = await response.json();
      setConfig(data);
    } catch (err) {
      console.error('Failed to fetch billing config:', err);
    }
  }, []);

  const subscribe = useCallback(async (plan: string, paymentMethodId: string, quantity = 1) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/billing/subscribe?plan=${plan}&payment_method_id=${paymentMethodId}&quantity=${quantity}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to create subscription');
      }
      
      const data = await response.json();
      await fetchSubscription();
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const cancelSubscription = useCallback(async (atPeriodEnd = true) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/billing/subscription/cancel?at_period_end=${atPeriodEnd}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to cancel subscription');
      
      await fetchSubscription();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const reactivateSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/billing/subscription/reactivate', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to reactivate subscription');
      
      await fetchSubscription();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const addPaymentMethod = useCallback(async (paymentMethodId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/billing/payment-method?payment_method_id=${paymentMethodId}&set_default=true`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to add payment method');
      
      await fetchSubscription();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  const removePaymentMethod = useCallback(async (paymentMethodId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/billing/payment-method/${paymentMethodId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      if (!response.ok) throw new Error('Failed to remove payment method');
      
      await fetchSubscription();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

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
      subscribe,
      cancelSubscription,
      reactivateSubscription,
      addPaymentMethod,
      removePaymentMethod
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
