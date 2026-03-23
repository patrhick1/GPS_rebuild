# Stripe Billing Setup Guide

## Overview

The GPS Assessment Platform uses Stripe for subscription billing. Churches can subscribe to monthly or yearly plans to unlock full features.

## Quick Start (Development)

### 1. Create a Stripe Account

1. Go to [stripe.com](https://stripe.com) and sign up for a free account
2. Complete the basic profile setup
3. No need to activate your account for test mode

### 2. Get Your Test API Keys

1. In the Stripe Dashboard, go to **Developers → API keys**
2. Copy your **Publishable key** (starts with `pk_test_`)
3. Copy your **Secret key** (starts with `sk_test_`)
4. Add to your `api/.env` file:

```bash
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### 3. Create Products and Prices

1. Go to **Products** in the Stripe Dashboard
2. Click **Add product**
3. Create two products:

   **Monthly Plan:**
   - Name: "GPS Monthly"
   - Description: "Monthly subscription for GPS Assessment Platform"
   - Pricing model: Standard pricing
   - Price: $29.00
   - Billing period: Monthly
   - Click **Save product**

   **Yearly Plan:**
   - Name: "GPS Yearly"
   - Description: "Yearly subscription for GPS Assessment Platform (Save 20%)"
   - Pricing model: Standard pricing
   - Price: $279.00
   - Billing period: Yearly
   - Click **Save product**

4. Copy the **Price IDs** (start with `price_`) and add to your `.env`:

```bash
STRIPE_PRICE_MONTHLY=price_your_monthly_price_id
STRIPE_PRICE_YEARLY=price_your_yearly_price_id
```

### 4. Set Up Webhook (Optional for Local Dev)

For local development, you can skip webhooks and use the dashboard to see events. For production:

1. Go to **Developers → Webhooks**
2. Click **Add endpoint**
3. Endpoint URL: `https://your-domain.com/api/billing/webhook`
4. Select events:
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the **Signing secret** and add to `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

## Test Credit Cards

Use these test card numbers in the frontend:

| Card Number | Brand | Scenario |
|-------------|-------|----------|
| `4242 4242 4242 4242` | Visa | Successful payment |
| `4000 0000 0000 0002` | Visa | Card declined |
| `4000 0000 0000 9995` | Visa | Insufficient funds |

Use any future date for expiry, any 3 digits for CVC, and any ZIP code.

## Production Setup (When Ready)

When you're ready to go live:

1. **Activate your Stripe account**
   - Complete business verification in Stripe Dashboard
   - Add bank account for payouts

2. **Switch to Live Mode**
   - Toggle to "Live mode" in Stripe Dashboard
   - Create products/prices again (test data doesn't transfer)

3. **Get Live API Keys**
   - Copy **Live secret key** (starts with `sk_live_`)
   - Create new webhook endpoint with live URL
   - Copy **Live webhook secret**

4. **Update Environment Variables on Render**
   ```bash
   STRIPE_SECRET_KEY=sk_live_your_live_key
   STRIPE_WEBHOOK_SECRET=whsec_your_live_webhook_secret
   STRIPE_PRICE_MONTHLY=price_your_live_monthly_price
   STRIPE_PRICE_YEARLY=price_your_live_yearly_price
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/billing/config` | GET | Get public Stripe config (publishable key, prices) |
| `/api/billing/subscription` | GET | Get current subscription details |
| `/api/billing/subscribe` | POST | Create new subscription |
| `/api/billing/subscription/cancel` | POST | Cancel subscription |
| `/api/billing/subscription/reactivate` | POST | Reactivate cancelled subscription |
| `/api/billing/payment-method` | POST | Add payment method |
| `/api/billing/payment-method/{id}` | DELETE | Remove payment method |
| `/api/billing/invoices` | GET | Get payment history |
| `/api/billing/webhook` | POST | Stripe webhook endpoint |

## Frontend Integration

The billing dashboard is available at `/admin/billing` for church admins.

Features:
- View current subscription status
- See upcoming payment date
- View payment history with receipts
- Cancel or reactivate subscription
- Plan upgrade/downgrade (coming soon)

## Pricing Recommendations

Default pricing structure:

| Plan | Price | Features |
|------|-------|----------|
| Monthly | $29/month | Unlimited members, assessments, analytics |
| Yearly | $279/year | Same as monthly, save ~20% |

You can adjust these prices in your Stripe Dashboard anytime.

## Troubleshooting

### "Price not configured" error
- Check that `STRIPE_PRICE_MONTHLY` and `STRIPE_PRICE_YEARLY` are set in `.env`
- Verify the Price IDs are correct from Stripe Dashboard

### Webhook errors
- For local development, webhooks are optional
- In production, ensure the webhook URL is correct and uses HTTPS
- Check that the webhook secret matches

### Test payments failing
- Make sure you're using test card numbers (not real cards)
- Check Stripe Dashboard → Developers → Logs for error details

## Support

For Stripe-specific issues:
- Stripe Documentation: [stripe.com/docs](https://stripe.com/docs)
- Stripe Support: [support.stripe.com](https://support.stripe.com)

For GPS Platform issues, contact the development team.
