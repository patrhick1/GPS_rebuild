import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { useBilling } from '../context/BillingContext';
import { api } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import adminHeroImg from '../../Graphics for Dev/Images/Admin Accounts Hero.webp';
import tealArrowIcon from '../../Graphics for Dev/Icons/Dark Teal Arrow Circle Icon.svg';

// Stripe promise (loaded once)
let stripePromise: ReturnType<typeof loadStripe> | null = null;

function getStripePromise(publishableKey: string | null) {
  if (!stripePromise && publishableKey) {
    stripePromise = loadStripe(publishableKey);
  }
  return stripePromise;
}

/* ─────────────────────── Checkout Form (inside Elements) ─────────────────────── */

function CheckoutForm({
  plan,
  onSuccess,
  onCancel,
}: {
  plan: 'monthly' | 'yearly';
  onSuccess: () => void;
  onCancel: () => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const { subscribe } = useBilling();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) return;

    try {
      // Create payment method
      const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (pmError) {
        setError(pmError.message || 'Failed to process card');
        setIsProcessing(false);
        return;
      }

      // Subscribe via backend
      const result = await subscribe(plan, paymentMethod.id);

      // Payment confirmation is always required with default_incomplete behavior.
      // A missing client_secret means the backend failed to return it — surface that immediately.
      if (result.requires_action) {
        if (!result.client_secret) {
          setError('Payment setup incomplete — the server did not return a confirmation token. Please try again.');
          setIsProcessing(false);
          return;
        }
        const { error: confirmError } = await stripe.confirmCardPayment(result.client_secret);
        if (confirmError) {
          setError(confirmError.message || 'Payment authentication failed. Please try again.');
          setIsProcessing(false);
          return;
        }
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Subscription failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block font-body font-bold text-base text-brand-charcoal mb-2">
          Card Details
        </label>
        <div className="bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl p-4">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  fontFamily: 'Mulish, sans-serif',
                  color: '#3F4644',
                  '::placeholder': { color: '#797E7C' },
                },
                invalid: { color: '#dc2626' },
              },
            }}
          />
        </div>
      </div>

      {error && (
        <p className="font-body text-sm text-red-600 bg-red-50 px-4 py-3 rounded-xl">
          {error}
        </p>
      )}

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={!stripe || isProcessing}
          className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? 'Processing...' : `Subscribe — ${plan === 'monthly' ? '$10/mo' : '$100/yr'}`}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="h-[50px] px-6 bg-white border border-brand-gray-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/* ─────────────────────── Add Card Form (inside Elements) ─────────────────────── */

function AddCardForm({
  onSuccess,
  onCancel,
}: {
  onSuccess: () => void;
  onCancel: () => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const { addPaymentMethod } = useBilling();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) return;

    try {
      const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (pmError) {
        setError(pmError.message || 'Failed to process card');
        setIsProcessing(false);
        return;
      }

      await addPaymentMethod(paymentMethod.id);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add card. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block font-body font-bold text-base text-brand-charcoal mb-2">
          Card Details
        </label>
        <div className="bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl p-4">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  fontFamily: 'Mulish, sans-serif',
                  color: '#3F4644',
                  '::placeholder': { color: '#797E7C' },
                },
                invalid: { color: '#dc2626' },
              },
            }}
          />
        </div>
      </div>

      {error && (
        <p className="font-body text-sm text-red-600 bg-red-50 px-4 py-3 rounded-xl">
          {error}
        </p>
      )}

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={!stripe || isProcessing}
          className="h-[50px] px-8 bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? 'Adding...' : 'Add Card'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="h-[50px] px-6 bg-white border border-brand-gray-light text-brand-charcoal font-body font-bold text-base rounded-xl hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/* ─────────────────────── Main Billing Dashboard ─────────────────────── */

export function BillingDashboard() {
  const {
    subscription,
    invoices,
    payments,
    config,
    isLoading,
    error,
    fetchSubscription,
    fetchInvoices,
    fetchConfig,
    cancelSubscription,
    reactivateSubscription,
    removePaymentMethod,
    setDefaultPaymentMethod,
    openBillingPortal,
  } = useBilling();

  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly' | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices'>('overview');
  const [isExporting, setIsExporting] = useState(false);
  const [removeCardConfirmId, setRemoveCardConfirmId] = useState<string | null>(null);
  const [showAddCard, setShowAddCard] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const response = await api.get('/admin/export/csv', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'church-data.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to export data. Please try again.' });
    } finally {
      setIsExporting(false);
    }
  };
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchSubscription();
    fetchInvoices();
    fetchConfig();
  }, [fetchSubscription, fetchInvoices, fetchConfig]);

  const handleCancel = async (atPeriodEnd: boolean) => {
    try {
      setActionMessage(null);
      await cancelSubscription(atPeriodEnd);
      setShowCancelConfirm(false);
      setActionMessage({
        type: 'success',
        text: atPeriodEnd
          ? 'Your subscription will cancel at the end of the billing period.'
          : 'Your subscription has been canceled.',
      });
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to cancel subscription. Please try again.' });
    }
  };

  const handleReactivate = async () => {
    try {
      setActionMessage(null);
      await reactivateSubscription();
      setActionMessage({ type: 'success', text: 'Subscription reactivated successfully!' });
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to reactivate subscription.' });
    }
  };

  const handleMakeDefault = async (paymentMethodId: string) => {
    try {
      setActionMessage(null);
      await setDefaultPaymentMethod(paymentMethodId);
      setActionMessage({ type: 'success', text: 'Default payment method updated.' });
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to update default payment method.' });
    }
  };

  const handleRemoveCard = async (paymentMethodId: string) => {
    try {
      setActionMessage(null);
      await removePaymentMethod(paymentMethodId);
      setRemoveCardConfirmId(null);
      setActionMessage({ type: 'success', text: 'Payment method removed.' });
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to remove payment method.' });
    }
  };

  const handleOpenPortal = async () => {
    try {
      setActionMessage(null);
      await openBillingPortal();
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to open billing portal. Please try again.' });
    }
  };

  const formatCardBrand = (brand: string) =>
    brand.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const formatDate = (timestamp: number | string | null) => {
    if (!timestamp) return 'N/A';
    const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const formatCurrency = (amount: number, currency: string) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: currency.toUpperCase() }).format(amount);

  const getStatusStyles = (status: string) => {
    const map: Record<string, string> = {
      active: 'bg-green-100 text-green-800',
      canceled: 'bg-red-100 text-red-800',
      past_due: 'bg-yellow-100 text-yellow-800',
      unpaid: 'bg-red-100 text-red-800',
      incomplete: 'bg-gray-100 text-gray-700',
      trialing: 'bg-blue-100 text-blue-800',
    };
    return map[status] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ── Hero ── */}
      <div className="relative w-full h-[220px] md:h-[280px] overflow-hidden">
        <img
          src={adminHeroImg}
          alt=""
          className="absolute inset-0 w-full h-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-[rgba(63,70,68,0.84)] mix-blend-multiply" />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <h1 className="font-heading font-black text-3xl md:text-[52px] md:leading-[60px] text-white text-center">
            Subscription &amp; Billing
          </h1>
          <p className="font-body font-semibold text-lg text-white/80 mt-2">
            Manage your church's plan and payment
          </p>
        </div>
      </div>

      <main className="flex-1 bg-white">
        {/* ── Messages ── */}
        {(error || actionMessage) && (
          <div className="max-w-[1057px] mx-auto px-6 pt-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-xl font-body text-base mb-4">
                {error}
              </div>
            )}
            {actionMessage && (
              <div
                className={`px-5 py-4 rounded-xl font-body text-base mb-4 ${
                  actionMessage.type === 'success'
                    ? 'bg-green-50 border border-green-200 text-green-700'
                    : 'bg-red-50 border border-red-200 text-red-700'
                }`}
              >
                {actionMessage.text}
              </div>
            )}
          </div>
        )}

        {isLoading && !subscription ? (
          <div className="flex items-center justify-center py-24">
            <div className="w-10 h-10 border-4 border-brand-teal border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !subscription ? (
          /* ── No Subscription: Plan Selection ── */
          <>
            {/* Checkout overlay */}
            {selectedPlan && config?.publishable_key && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8">
                  <h2 className="font-heading font-black text-2xl text-brand-charcoal mb-1">
                    Complete Your Subscription
                  </h2>
                  <p className="font-body text-brand-gray-med mb-6">
                    {selectedPlan === 'monthly' ? 'Monthly Plan — $10/month' : 'Annual Plan — $100/year (save $20)'}
                  </p>
                  <Elements stripe={getStripePromise(config.publishable_key)}>
                    <CheckoutForm
                      plan={selectedPlan}
                      onSuccess={() => {
                        setSelectedPlan(null);
                        fetchSubscription();
                        setActionMessage({ type: 'success', text: 'Subscription created successfully! Welcome aboard.' });
                      }}
                      onCancel={() => setSelectedPlan(null)}
                    />
                  </Elements>
                </div>
              </div>
            )}

            {/* Plan Cards Section */}
            <section className="max-w-[1057px] mx-auto px-6 py-12 md:py-16">
              <div className="text-center mb-12">
                <h2 className="font-heading font-black text-3xl md:text-[44px] md:leading-[50px] text-brand-charcoal mb-4">
                  Choose Your Plan
                </h2>
                <p className="font-body font-semibold text-lg text-brand-gray-med max-w-2xl mx-auto">
                  Unlock the full potential of personal calling in your organization. Track and manage your church&apos;s assessment results.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-8 max-w-[800px] mx-auto">
                {/* Monthly Plan */}
                <div className="bg-white border border-brand-gray-light rounded-2xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-8 flex flex-col">
                  <h3 className="font-heading font-black text-2xl text-brand-charcoal mb-2">Monthly</h3>
                  <div className="mb-6">
                    <span className="font-heading font-black text-[56px] leading-none text-brand-teal">$10</span>
                    <span className="font-body font-bold text-lg text-brand-gray-med ml-1">/month</span>
                  </div>

                  <ul className="space-y-3 mb-8 flex-1">
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Exclusive Dashboard Access</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Unique Invitation Link for Members</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">View &amp; Export Assessment Results</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Unlimited Members</span>
                    </li>
                  </ul>

                  <button
                    onClick={() => setSelectedPlan('monthly')}
                    className="w-full h-[50px] bg-white border-2 border-brand-teal text-brand-teal font-body font-bold text-lg rounded-xl hover:bg-brand-teal hover:text-white transition-colors"
                  >
                    Choose Monthly
                  </button>
                </div>

                {/* Yearly Plan */}
                <div className="relative bg-white border-2 border-brand-teal rounded-2xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-8 flex flex-col">
                  {/* Best Value badge */}
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-brand-gold text-white font-body font-bold text-sm px-5 py-1.5 rounded-full whitespace-nowrap">
                    Best Value — Save $20
                  </div>

                  <h3 className="font-heading font-black text-2xl text-brand-charcoal mb-2 mt-2">Annual</h3>
                  <div className="mb-2">
                    <span className="font-heading font-black text-[56px] leading-none text-brand-teal">$100</span>
                    <span className="font-body font-bold text-lg text-brand-gray-med ml-1">/year</span>
                  </div>
                  <p className="font-body text-sm text-brand-gray-med mb-6">
                    That&apos;s just $8.33/month
                  </p>

                  <ul className="space-y-3 mb-8 flex-1">
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Everything in Monthly</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Priority Email Support</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">2 Months Free vs Monthly</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <img src={tealArrowIcon} alt="" className="w-5 h-5 mt-0.5 shrink-0" />
                      <span className="font-body text-base text-brand-charcoal">Locked-in Rate Guarantee</span>
                    </li>
                  </ul>

                  <button
                    onClick={() => setSelectedPlan('yearly')}
                    className="w-full h-[50px] bg-brand-teal text-white font-body font-bold text-lg rounded-xl hover:bg-brand-teal/90 transition-colors"
                  >
                    Choose Annual
                  </button>
                </div>
              </div>

              {/* Contact line */}
              <p className="text-center font-body font-semibold text-base text-brand-gray-med mt-10">
                Have questions?{' '}
                <a
                  href="mailto:support@giftpassionstory.com"
                  className="text-brand-teal underline hover:text-brand-teal/80 transition-colors"
                >
                  Email us at support@giftpassionstory.com
                </a>
              </p>
            </section>
          </>
        ) : (
          /* ── Active Subscription: Management ── */
          <section className="max-w-[1057px] mx-auto px-6 py-10">
            {/* Resubscribe banner for dead subscriptions */}
            {(subscription.status === 'incomplete_expired' || subscription.status === 'canceled') && (
              <>
                {config?.publishable_key && selectedPlan && (
                  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8">
                      <h2 className="font-heading font-black text-2xl text-brand-charcoal mb-1">
                        Complete Your Subscription
                      </h2>
                      <p className="font-body text-brand-gray-med mb-6">
                        {selectedPlan === 'monthly' ? 'Monthly Plan — $10/month' : 'Annual Plan — $100/year (save $20)'}
                      </p>
                      <Elements stripe={getStripePromise(config.publishable_key)}>
                        <CheckoutForm
                          plan={selectedPlan}
                          onSuccess={() => {
                            setSelectedPlan(null);
                            fetchSubscription();
                            fetchInvoices();
                            setActionMessage({ type: 'success', text: 'Subscription activated! Welcome back.' });
                          }}
                          onCancel={() => setSelectedPlan(null)}
                        />
                      </Elements>
                    </div>
                  </div>
                )}
                <div className="bg-yellow-50 border border-yellow-300 rounded-xl px-6 py-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <p className="font-body font-bold text-base text-yellow-800">
                      {subscription.status === 'incomplete_expired'
                        ? 'Your previous subscription attempt did not complete. Please subscribe again to access the dashboard.'
                        : 'Your subscription has been canceled. Subscribe again to restore access.'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3 shrink-0">
                    <button
                      onClick={() => setSelectedPlan('monthly')}
                      className="h-[44px] px-5 bg-white border-2 border-brand-teal text-brand-teal font-body font-bold text-sm rounded-xl hover:bg-brand-teal hover:text-white transition-colors"
                    >
                      Monthly — $10
                    </button>
                    <button
                      onClick={() => setSelectedPlan('yearly')}
                      className="h-[44px] px-5 bg-brand-teal text-white font-body font-bold text-sm rounded-xl hover:bg-brand-teal/90 transition-colors"
                    >
                      Annual — $100
                    </button>
                    <button
                      onClick={handleExport}
                      disabled={isExporting}
                      className="h-[44px] px-5 bg-white border border-brand-gray-light text-brand-charcoal font-body font-bold text-sm rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isExporting ? 'Exporting…' : 'Export Your Data'}
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Tabs + Back link */}
            <div className="flex items-center justify-between border-b border-brand-gray-light mb-8">
              <div className="flex gap-1">
                <button
                  className={`px-6 py-3 font-body font-bold text-base border-b-2 transition-colors ${
                    activeTab === 'overview'
                      ? 'border-brand-teal text-brand-teal'
                      : 'border-transparent text-brand-gray-med hover:text-brand-charcoal'
                  }`}
                  onClick={() => setActiveTab('overview')}
                >
                  Overview
                </button>
                <button
                  className={`px-6 py-3 font-body font-bold text-base border-b-2 transition-colors ${
                    activeTab === 'invoices'
                      ? 'border-brand-teal text-brand-teal'
                      : 'border-transparent text-brand-gray-med hover:text-brand-charcoal'
                  }`}
                  onClick={() => setActiveTab('invoices')}
                >
                  Payment History
                </button>
              </div>
              <Link
                to="/admin"
                className="font-body font-bold text-sm text-brand-teal hover:text-brand-teal/80 transition-colors"
              >
                ← Back to Dashboard
              </Link>
            </div>

            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Info cards */}
                <div className="grid md:grid-cols-3 gap-6">
                  {/* Current Plan */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <p className="font-body font-bold text-sm text-brand-gray-med uppercase tracking-wide mb-3">
                      Current Plan
                    </p>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-heading font-black text-xl text-brand-charcoal">
                        {subscription.plan === 'yearly' ? 'Annual' : 'Monthly'}
                      </span>
                      <span
                        className={`px-3 py-1 rounded-full font-body font-bold text-xs uppercase ${getStatusStyles(subscription.status)}`}
                      >
                        {subscription.status}
                      </span>
                    </div>
                    <p className="font-body text-sm text-brand-gray-med">
                      {subscription.quantity} seat{subscription.quantity !== 1 ? 's' : ''}
                    </p>
                  </div>

                  {/* Payment Method */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <p className="font-body font-bold text-sm text-brand-gray-med uppercase tracking-wide mb-3">
                      Payment Method
                    </p>
                    {subscription.organization.card_brand ? (
                      <div>
                        <span className="font-heading font-black text-xl text-brand-charcoal capitalize">
                          {subscription.organization.card_brand}
                        </span>
                        <span className="font-body text-base text-brand-gray-med ml-2">
                          **** {subscription.organization.card_last_four}
                        </span>
                      </div>
                    ) : (
                      <p className="font-body text-base text-brand-gray-med">No payment method on file</p>
                    )}
                  </div>

                  {/* Next Payment */}
                  <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                    <p className="font-body font-bold text-sm text-brand-gray-med uppercase tracking-wide mb-3">
                      Next Payment
                    </p>
                    {subscription.upcoming_invoice ? (
                      <>
                        <p className="font-heading font-black text-xl text-brand-charcoal">
                          {formatCurrency(subscription.upcoming_invoice.amount_due, subscription.upcoming_invoice.currency)}
                        </p>
                        <p className="font-body text-sm text-brand-gray-med">
                          Due {formatDate(subscription.upcoming_invoice.due_date)}
                        </p>
                      </>
                    ) : subscription.current_period_end ? (
                      <p className="font-body text-base text-brand-charcoal">
                        {subscription.cancel_at_period_end
                          ? `Access until ${formatDate(subscription.current_period_end)}`
                          : `Renews ${formatDate(subscription.current_period_end)}`}
                      </p>
                    ) : (
                      <p className="font-body text-base text-brand-gray-med">No upcoming payment</p>
                    )}
                  </div>
                </div>

                {/* Trial banner */}
                {subscription.trial_end && new Date(subscription.trial_end) > new Date() && (
                  <div className="bg-brand-teal/10 border border-brand-teal rounded-xl px-6 py-4 text-center">
                    <p className="font-body font-bold text-base text-brand-teal">
                      You're currently in your trial period. Trial ends on {formatDate(subscription.trial_end)}.
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                  {subscription.cancel_at_period_end ? (
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <p className="font-body font-bold text-base text-yellow-700">
                        Your subscription is set to cancel on {formatDate(subscription.current_period_end)}.
                      </p>
                      <button
                        onClick={handleReactivate}
                        className="h-[44px] px-6 bg-green-600 text-white font-body font-bold text-base rounded-xl hover:bg-green-700 transition-colors"
                      >
                        Reactivate Subscription
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                      <p className="font-body text-base text-brand-gray-med">
                        Need to make changes to your subscription?
                      </p>
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={handleOpenPortal}
                          disabled={isLoading}
                          className="h-[44px] px-6 bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Manage Billing in Stripe
                        </button>
                        <button
                          onClick={() => setShowCancelConfirm(true)}
                          className="h-[44px] px-6 bg-white border border-red-300 text-red-600 font-body font-bold text-base rounded-xl hover:bg-red-50 transition-colors"
                        >
                          Cancel Subscription
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Payment Methods Management */}
                <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-heading font-black text-xl text-brand-charcoal">
                      Payment Methods
                    </h3>
                    {!showAddCard && (
                      <button
                        onClick={() => setShowAddCard(true)}
                        className="h-[40px] px-5 bg-white border-2 border-brand-teal text-brand-teal font-body font-bold text-sm rounded-xl hover:bg-brand-teal hover:text-white transition-colors"
                      >
                        + Add Card
                      </button>
                    )}
                  </div>

                  {subscription.payment_methods && subscription.payment_methods.length > 0 ? (
                    <ul className="divide-y divide-brand-gray-light">
                      {subscription.payment_methods.map((pm) => {
                        const isOnlyCard = subscription.payment_methods.length === 1;
                        const disableRemove = pm.is_default && isOnlyCard;
                        return (
                          <li key={pm.id} className="py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="font-heading font-black text-lg text-brand-charcoal">
                                {formatCardBrand(pm.brand)}
                              </span>
                              <span className="font-body text-base text-brand-gray-med">
                                **** {pm.last4}
                              </span>
                              <span className="font-body text-sm text-brand-gray-med">
                                Expires {String(pm.exp_month).padStart(2, '0')}/{String(pm.exp_year).slice(-2)}
                              </span>
                              {pm.is_default && (
                                <span className="px-2.5 py-0.5 rounded-full font-body font-bold text-xs uppercase bg-brand-teal/10 text-brand-teal">
                                  Default
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {!pm.is_default && (
                                <button
                                  onClick={() => handleMakeDefault(pm.id)}
                                  disabled={isLoading}
                                  className="h-[36px] px-4 bg-white border border-brand-teal text-brand-teal font-body font-bold text-sm rounded-lg hover:bg-brand-teal/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  Make Default
                                </button>
                              )}
                              <button
                                onClick={() => setRemoveCardConfirmId(pm.id)}
                                disabled={disableRemove || isLoading}
                                title={disableRemove ? 'Cannot remove your only payment method' : undefined}
                                className="h-[36px] px-4 bg-white border border-red-300 text-red-600 font-body font-bold text-sm rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                Remove
                              </button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  ) : subscription.organization.card_brand ? (
                    <div className="py-2 flex items-center gap-3">
                      <span className="font-heading font-black text-lg text-brand-charcoal capitalize">
                        {subscription.organization.card_brand}
                      </span>
                      <span className="font-body text-base text-brand-gray-med">
                        **** {subscription.organization.card_last_four}
                      </span>
                    </div>
                  ) : (
                    <p className="font-body text-base text-brand-gray-med py-2">
                      No payment methods on file.
                    </p>
                  )}

                  {showAddCard && config?.publishable_key && (
                    <div className="mt-6 pt-6 border-t border-brand-gray-light">
                      <h4 className="font-heading font-black text-base text-brand-charcoal mb-4">
                        Add a new card
                      </h4>
                      <Elements stripe={getStripePromise(config.publishable_key)}>
                        <AddCardForm
                          onSuccess={() => {
                            setShowAddCard(false);
                            setActionMessage({ type: 'success', text: 'Payment method added.' });
                          }}
                          onCancel={() => setShowAddCard(false)}
                        />
                      </Elements>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'invoices' && (
              <div className="bg-white border border-brand-gray-light rounded-xl shadow-[0_4px_4px_rgba(0,0,0,0.25)] overflow-hidden">
                {invoices.length === 0 && payments.length === 0 ? (
                  <p className="text-center font-body text-base text-brand-gray-med py-16">
                    No payment history yet.
                  </p>
                ) : (
                  <div className="divide-y divide-brand-gray-light">
                    {[...invoices, ...payments]
                      .sort(
                        (a: any, b: any) =>
                          (b.created || new Date(b.created_at).getTime() / 1000) -
                          (a.created || new Date(a.created_at).getTime() / 1000)
                      )
                      .map((item: any) => (
                        <div key={item.id} className="flex items-center justify-between px-6 py-4">
                          <div>
                            <p className="font-body font-bold text-base text-brand-charcoal">
                              {formatDate(item.created || item.created_at)}
                            </p>
                            <span
                              className={`inline-block mt-1 px-3 py-0.5 rounded-full font-body font-bold text-xs uppercase ${
                                item.status === 'paid' || item.status === 'succeeded'
                                  ? 'bg-green-100 text-green-800'
                                  : item.status === 'open' || item.status === 'pending'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {item.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="font-heading font-black text-lg text-brand-charcoal">
                              {formatCurrency(
                                item.amount_paid > 0 ? item.amount_paid : (item.amount_due ?? item.amount ?? 0),
                                item.currency
                              )}
                            </span>
                            {(item.receipt_url || item.hosted_invoice_url) && (
                              <a
                                href={item.receipt_url || item.hosted_invoice_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-body font-bold text-sm text-brand-teal underline hover:text-brand-teal/80 transition-colors"
                              >
                                {item.receipt_url ? 'View Receipt' : 'View Invoice'}
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      <Footer />

      {/* Remove card confirmation modal */}
      {removeCardConfirmId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
            <h2 className="font-heading font-black text-2xl text-brand-charcoal mb-3">
              Remove Payment Method?
            </h2>
            <p className="font-body text-base text-brand-gray-med mb-6">
              This will detach the card from your account. You can add it again later if needed.
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => setRemoveCardConfirmId(null)}
                className="h-[50px] bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 transition-colors"
              >
                Keep Card
              </button>
              <button
                onClick={() => handleRemoveCard(removeCardConfirmId)}
                disabled={isLoading}
                className="h-[50px] bg-white border border-red-300 text-red-600 font-body font-bold text-base rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Remove Card
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel confirmation modal */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
            <h2 className="font-heading font-black text-2xl text-brand-charcoal mb-3">
              Cancel Subscription?
            </h2>
            <p className="font-body text-base text-brand-gray-med mb-6">
              Are you sure you want to cancel? You can cancel at the end of your billing period to keep
              access until then, or cancel immediately.
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="h-[50px] bg-brand-teal text-white font-body font-bold text-base rounded-xl hover:bg-brand-teal/90 transition-colors"
              >
                Keep My Subscription
              </button>
              <button
                onClick={() => handleCancel(true)}
                className="h-[50px] bg-white border border-yellow-400 text-yellow-700 font-body font-bold text-base rounded-xl hover:bg-yellow-50 transition-colors"
              >
                Cancel at Period End
              </button>
              <button
                onClick={() => handleCancel(false)}
                className="h-[50px] bg-white border border-red-300 text-red-600 font-body font-bold text-base rounded-xl hover:bg-red-50 transition-colors"
              >
                Cancel Immediately
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
