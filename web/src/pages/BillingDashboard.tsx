import { useEffect, useState } from 'react';
import { useBilling } from '../context/BillingContext';
import './BillingDashboard.css';

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
    reactivateSubscription
  } = useBilling();

  const [activeTab, setActiveTab] = useState<'overview' | 'invoices'>('overview');
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscription();
    fetchInvoices();
    fetchConfig();
  }, [fetchSubscription, fetchInvoices, fetchConfig]);

  const handleCancel = async (atPeriodEnd: boolean) => {
    try {
      setActionError(null);
      await cancelSubscription(atPeriodEnd);
      setShowCancelConfirm(false);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to cancel subscription');
    }
  };

  const handleReactivate = async () => {
    try {
      setActionError(null);
      await reactivateSubscription();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to reactivate subscription');
    }
  };

  const formatDate = (timestamp: number | string | null) => {
    if (!timestamp) return 'N/A';
    const date = typeof timestamp === 'number' 
      ? new Date(timestamp * 1000) 
      : new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase()
    }).format(amount);
  };

  const getStatusBadge = (status: string) => {
    const statusClasses: Record<string, string> = {
      active: 'status-active',
      canceled: 'status-canceled',
      past_due: 'status-past-due',
      unpaid: 'status-unpaid',
      incomplete: 'status-incomplete',
      trialing: 'status-trialing'
    };
    return <span className={`status-badge ${statusClasses[status] || 'status-default'}`}>{status}</span>;
  };

  if (isLoading && !subscription) {
    return <div className="billing-dashboard loading">Loading billing information...</div>;
  }

  return (
    <div className="billing-dashboard">
      <div className="page-header">
        <h1>Billing & Subscription</h1>
        <p>Manage your church's subscription and payment methods</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      {actionError && (
        <div className="error-banner">
          {actionError}
          <button onClick={() => setActionError(null)}>×</button>
        </div>
      )}

      {!subscription ? (
        <div className="no-subscription">
          <div className="subscription-card">
            <h2>Choose Your Plan</h2>
            <p>Subscribe to unlock all features for your church members.</p>
            
            <div className="plans-grid">
              <div className="plan-card">
                <h3>Monthly</h3>
                <div className="plan-price">
                  <span className="currency">$</span>
                  <span className="amount">29</span>
                  <span className="period">/month</span>
                </div>
                <ul className="plan-features">
                  <li>Unlimited members</li>
                  <li>Unlimited assessments</li>
                  <li>Analytics dashboard</li>
                  <li>Email support</li>
                </ul>
                <button className="btn-subscribe" disabled={!config?.prices?.monthly}>
                  Subscribe Monthly
                </button>
              </div>

              <div className="plan-card recommended">
                <div className="badge">Save 20%</div>
                <h3>Yearly</h3>
                <div className="plan-price">
                  <span className="currency">$</span>
                  <span className="amount">279</span>
                  <span className="period">/year</span>
                </div>
                <ul className="plan-features">
                  <li>Unlimited members</li>
                  <li>Unlimited assessments</li>
                  <li>Analytics dashboard</li>
                  <li>Priority support</li>
                  <li>2 months free</li>
                </ul>
                <button className="btn-subscribe btn-primary" disabled={!config?.prices?.yearly}>
                  Subscribe Yearly
                </button>
              </div>
            </div>

            <p className="setup-note">
              <strong>Note:</strong> To complete subscription setup, you'll need to add a payment method. 
              Contact support if you need assistance.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="tabs">
            <button 
              className={activeTab === 'overview' ? 'active' : ''}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </button>
            <button 
              className={activeTab === 'invoices' ? 'active' : ''}
              onClick={() => setActiveTab('invoices')}
            >
              Payment History
            </button>
          </div>

          {activeTab === 'overview' && (
            <div className="overview-tab">
              <div className="info-cards">
                <div className="info-card">
                  <h3>Current Plan</h3>
                  <div className="plan-info">
                    <span className="plan-name">{subscription.plan === 'yearly' ? 'Yearly' : 'Monthly'} Plan</span>
                    {getStatusBadge(subscription.status)}
                  </div>
                  <p className="plan-detail">
                    {subscription.quantity} seat{subscription.quantity !== 1 ? 's' : ''}
                  </p>
                </div>

                <div className="info-card">
                  <h3>Payment Method</h3>
                  {subscription.organization.card_brand ? (
                    <div className="payment-method">
                      <span className="card-brand">{subscription.organization.card_brand}</span>
                      <span className="card-last4">•••• {subscription.organization.card_last_four}</span>
                    </div>
                  ) : (
                    <p className="no-payment-method">No payment method on file</p>
                  )}
                </div>

                <div className="info-card">
                  <h3>Next Payment</h3>
                  {subscription.upcoming_invoice ? (
                    <div className="next-payment">
                      <span className="amount">
                        {formatCurrency(subscription.upcoming_invoice.amount_due, subscription.upcoming_invoice.currency)}
                      </span>
                      <span className="date">Due {formatDate(subscription.upcoming_invoice.due_date)}</span>
                    </div>
                  ) : subscription.current_period_end ? (
                    <div className="next-payment">
                      <span className="date">
                        {subscription.cancel_at_period_end 
                          ? `Access until ${formatDate(subscription.current_period_end)}`
                          : `Renews ${formatDate(subscription.current_period_end)}`
                        }
                      </span>
                    </div>
                  ) : (
                    <p className="no-payment">No upcoming payment</p>
                  )}
                </div>
              </div>

              <div className="subscription-actions">
                {subscription.cancel_at_period_end ? (
                  <div className="cancel-notice">
                    <p>⚠️ Your subscription is set to cancel on {formatDate(subscription.current_period_end)}</p>
                    <button className="btn-reactivate" onClick={handleReactivate}>
                      Reactivate Subscription
                    </button>
                  </div>
                ) : (
                  <button 
                    className="btn-cancel"
                    onClick={() => setShowCancelConfirm(true)}
                  >
                    Cancel Subscription
                  </button>
                )}
              </div>

              {subscription.trial_end && new Date(subscription.trial_end) > new Date() && (
                <div className="trial-banner">
                  🎉 You're currently in your trial period. 
                  Trial ends on {formatDate(subscription.trial_end)}
                </div>
              )}
            </div>
          )}

          {activeTab === 'invoices' && (
            <div className="invoices-tab">
              {invoices.length === 0 && payments.length === 0 ? (
                <p className="no-invoices">No payment history yet.</p>
              ) : (
                <div className="invoices-list">
                  {[...invoices, ...payments]
                    .sort((a, b) => (b.created || new Date(b.created_at).getTime() / 1000) - (a.created || new Date(a.created_at).getTime() / 1000))
                    .map((item) => (
                      <div key={item.id} className="invoice-item">
                        <div className="invoice-info">
                          <span className="invoice-date">
                            {formatDate(item.created || item.created_at)}
                          </span>
                          <span className={`invoice-status ${item.status}`}>
                            {item.status}
                          </span>
                        </div>
                        <div className="invoice-amount">
                          {formatCurrency(
                            item.amount_paid || item.amount, 
                            item.currency
                          )}
                        </div>
                        {(item.hosted_invoice_url || item.receipt_url) && (
                          <a 
                            href={item.hosted_invoice_url || item.receipt_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn-view-invoice"
                          >
                            View Receipt
                          </a>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {showCancelConfirm && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Cancel Subscription?</h2>
            <p>
              Are you sure you want to cancel your subscription? 
              You can choose to cancel immediately or at the end of your billing period.
            </p>
            <div className="modal-actions">
              <button 
                className="btn-secondary"
                onClick={() => setShowCancelConfirm(false)}
              >
                Keep Subscription
              </button>
              <button 
                className="btn-warning"
                onClick={() => handleCancel(true)}
              >
                Cancel at Period End
              </button>
              <button 
                className="btn-danger"
                onClick={() => handleCancel(false)}
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
