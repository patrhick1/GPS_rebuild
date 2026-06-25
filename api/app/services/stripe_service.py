"""
Stripe integration service for GPS billing
Handles subscriptions, payments, and webhook events
"""
import logging
import stripe
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription, Payment
from app.models.organization import Organization


# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
# Default Stripe SDK timeout is 80 seconds; cap at 10 so a Stripe stall
# doesn't hold a request worker open for over a minute. Two automatic
# retries on transient network errors.
stripe.max_network_retries = 2
stripe.api_request_timeout = 10


def _period_dates(sub) -> tuple[Optional[datetime], Optional[datetime]]:
    """Extract (current_period_start, current_period_end) from a Stripe Subscription.

    Stripe API version 2026-02-25+ moved these fields off the top-level
    Subscription object onto subscription.items.data[0]. This helper
    handles both old and new payload shapes via .get() lookups, so the
    read path doesn't break when the API version rolls forward.
    """
    if sub is None:
        return None, None
    items = (sub.get("items") or {}).get("data") or []
    if items:
        first = items[0] or {}
        cps = first.get("current_period_start")
        cpe = first.get("current_period_end")
    else:
        cps = sub.get("current_period_start")
        cpe = sub.get("current_period_end")
    return (
        datetime.fromtimestamp(cps) if cps else None,
        datetime.fromtimestamp(cpe) if cpe else None,
    )


class StripeService:
    """Service for handling Stripe operations"""

    @staticmethod
    def resolve_promotion_code(
        code: str,
        customer_id: Optional[str] = None,
    ) -> stripe.PromotionCode:
        """Resolve an active customer-facing promotion code.

        Stripe performs the authoritative eligibility checks when the code is
        applied to an invoice/subscription. Keeping lookup here prevents the
        client from submitting arbitrary coupon or promotion-code IDs.
        """
        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("Enter a promotion code.")

        promotion_codes = stripe.PromotionCode.list(
            code=normalized_code,
            active=True,
            limit=100,
            expand=["data.promotion.coupon"],
        )
        for promotion_code in promotion_codes.data:
            restricted_customer = promotion_code.get("customer")
            if isinstance(restricted_customer, dict):
                restricted_customer = restricted_customer.get("id")
            if not restricted_customer or restricted_customer == customer_id:
                return promotion_code

        raise ValueError("This promotion code is invalid or no longer available.")

    @staticmethod
    def _promotion_code_description(
        promotion_code: stripe.PromotionCode,
    ) -> tuple[str, Optional[str]]:
        """Build a safe, user-facing description from the expanded coupon."""
        promotion = promotion_code.get("promotion") or {}
        coupon = promotion.get("coupon") or {}
        if isinstance(coupon, str):
            coupon = stripe.Coupon.retrieve(coupon)

        percent_off = coupon.get("percent_off")
        amount_off = coupon.get("amount_off")
        currency = (coupon.get("currency") or "usd").upper()
        if percent_off is not None:
            percent = float(percent_off)
            label = f"{percent:g}% off"
        elif amount_off is not None:
            label = f"{amount_off / 100:.2f} {currency} off"
        else:
            label = "Promotion applied"

        duration = coupon.get("duration")
        if duration == "once":
            duration_label = "first payment"
        elif duration == "repeating":
            months = coupon.get("duration_in_months")
            duration_label = f"{months} months" if months else "limited time"
        elif duration == "forever":
            duration_label = "for the life of the subscription"
        else:
            duration_label = None

        return label, duration_label

    @staticmethod
    def preview_promotion_code(
        organization: Organization,
        email: str,
        price_id: str,
        code: str,
        quantity: int = 1,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Preview Stripe's exact total for a promotion code and plan."""
        if not customer_id:
            customer = StripeService.get_or_create_customer(organization, email)
            customer_id = customer.id
        promotion_code = StripeService.resolve_promotion_code(code, customer_id)

        invoice = stripe.Invoice.create_preview(
            customer=customer_id,
            discounts=[{"promotion_code": promotion_code.id}],
            subscription_details={
                "items": [{"price": price_id, "quantity": quantity}],
            },
        )
        discount_total = sum(
            item.get("amount", 0)
            for item in (invoice.get("total_discount_amounts") or [])
        )
        label, duration = StripeService._promotion_code_description(promotion_code)

        return {
            "code": promotion_code.code,
            "promotion_code_id": promotion_code.id,
            "subtotal": invoice.get("subtotal", 0),
            "discount_total": discount_total,
            "total": invoice.get("total", 0),
            "currency": invoice.get("currency", "usd"),
            "label": label,
            "duration": duration,
        }
    
    @staticmethod
    def create_customer(organization: Organization, email: str) -> stripe.Customer:
        """Create a Stripe customer for an organization.

        Uses idempotency_key=customer-{org_id} so that two concurrent
        get_or_create_customer calls (e.g., a double-clicked /subscribe)
        return the same Stripe customer instead of creating two and
        orphaning the first when organization.stripe_id is overwritten.
        """
        customer = stripe.Customer.create(
            name=organization.name,
            email=email,
            metadata={
                "organization_id": str(organization.id),
                "organization_key": organization.key
            },
            idempotency_key=f"customer-create-{organization.id}",
        )

        organization.stripe_id = customer.id
        return customer
    
    @staticmethod
    def get_or_create_customer(organization: Organization, email: str) -> stripe.Customer:
        """Get existing customer or create new one"""
        if organization.stripe_id:
            try:
                return stripe.Customer.retrieve(organization.stripe_id)
            except stripe.error.InvalidRequestError:
                pass  # Customer not found, create new
        
        return StripeService.create_customer(organization, email)
    
    @staticmethod
    def create_subscription(
        organization: Organization,
        price_id: str,
        plan: str = "monthly",
        quantity: int = 1,
        payment_method_id: Optional[str] = None,
        promotion_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new subscription for an organization"""
        
        # Get or create customer
        customer = StripeService.get_or_create_customer(
            organization, 
            organization.memberships[0].user.email if organization.memberships else None
        )
        
        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
            stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
        
        promotion = (
            StripeService.resolve_promotion_code(promotion_code, customer.id)
            if promotion_code
            else None
        )
        metadata = {
            "organization_id": str(organization.id),
            "organization_key": organization.key,
        }
        create_params = {
            "customer": customer.id,
            "items": [{"price": price_id, "quantity": quantity}],
            "payment_behavior": "default_incomplete",
            "expand": ["latest_invoice.confirmation_secret"],
            "metadata": metadata,
        }
        if promotion:
            create_params["discounts"] = [{"promotion_code": promotion.id}]
            metadata["promotion_code"] = promotion.code
            metadata["promotion_code_id"] = promotion.id

        # The payment-method ID makes retries of the same checkout attempt
        # idempotent without preventing a later, intentional resubscription.
        idempotency_key = (
            f"subscription-create-{organization.id}-{payment_method_id}"
            if payment_method_id
            else None
        )
        subscription = stripe.Subscription.create(
            **create_params,
            idempotency_key=idempotency_key,
        )
        
        # Create local subscription record
        cps, cpe = _period_dates(subscription)
        db_subscription = Subscription(
            organization_id=organization.id,
            stripe_customer_id=customer.id,
            stripe_subscription_id=subscription.id,
            stripe_price_id=price_id,
            status=subscription.status,
            plan=plan,
            quantity=quantity,
            current_period_start=cps,
            current_period_end=cpe,
            trial_start=datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
            trial_end=datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
        )
        
        return {
            "subscription": subscription,
            "db_subscription": db_subscription,
            "promotion_code": promotion.code if promotion else None,
            "promotion_code_id": promotion.id if promotion else None,
        }
    
    @staticmethod
    def update_subscription(
        subscription_id: str,
        quantity: Optional[int] = None,
        price_id: Optional[str] = None
    ) -> stripe.Subscription:
        """Update an existing subscription"""
        params = {}
        
        if quantity is not None:
            params["quantity"] = quantity
        
        if price_id:
            params["items"] = [{"price": price_id}]
        
        return stripe.Subscription.modify(subscription_id, **params)
    
    @staticmethod
    def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> stripe.Subscription:
        """Cancel a subscription"""
        if at_period_end:
            return stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            return stripe.Subscription.delete(subscription_id)
    
    @staticmethod
    def reactivate_subscription(subscription_id: str) -> stripe.Subscription:
        """Reactivate a subscription that was set to cancel at period end"""
        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )
    
    @staticmethod
    def create_setup_intent(customer_id: str) -> stripe.SetupIntent:
        """Create a setup intent for adding/updating payment method"""
        return stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=["card"]
        )

    @staticmethod
    def create_billing_portal_session(customer_id: str, return_url: str) -> stripe.billing_portal.Session:
        """Create a Stripe-hosted billing portal session for self-service management"""
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    
    @staticmethod
    def get_payment_methods(customer_id: str) -> list:
        """Get all payment methods for a customer"""
        try:
            methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            return methods.data
        except stripe.error.InvalidRequestError:
            return []
    
    @staticmethod
    def detach_payment_method(payment_method_id: str) -> stripe.PaymentMethod:
        """Remove a payment method from a customer"""
        return stripe.PaymentMethod.detach(payment_method_id)
    
    @staticmethod
    def get_upcoming_invoice(customer_id: str, subscription_id: Optional[str] = None) -> Optional[stripe.Invoice]:
        """Get the upcoming invoice for a customer"""
        try:
            params = {"customer": customer_id}
            if subscription_id:
                params["subscription"] = subscription_id
            return stripe.Invoice.create_preview(**params)
        except Exception:
            return None
    
    @staticmethod
    def get_invoices(customer_id: str, limit: int = 10) -> list:
        """Get recent invoices for a customer"""
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit,
            )
            return invoices.data
        except stripe.error.InvalidRequestError:
            return []
    
    @staticmethod
    def construct_event(payload: bytes, sig_header: str) -> stripe.Event:
        """Verify and construct a webhook event"""
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    
    @staticmethod
    def handle_subscription_updated(event: stripe.Event, db: Session) -> None:
        """Handle subscription updated webhook"""
        sub = event.data.object
        if hasattr(sub, "to_dict"):
            sub = sub.to_dict()

        sub_id = sub.get("id")
        items_data = sub.get("items", {}).get("data", [])
        first_item = items_data[0] if items_data else {}
        quantity = first_item.get("quantity", 1)
        price_id = first_item.get("price", {}).get("id")
        plan_obj = sub.get("plan") or {}
        interval = plan_obj.get("interval")
        metadata = sub.get("metadata") or {}

        # Find local subscription
        db_subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == sub_id
        ).first()

        cps, cpe = _period_dates(sub)
        org_id_for_uncomp = None
        if db_subscription:
            db_subscription.status = sub.get("status")
            db_subscription.current_period_start = cps
            db_subscription.current_period_end = cpe
            db_subscription.cancel_at_period_end = sub.get("cancel_at_period_end", False)
            db_subscription.quantity = quantity
            db_subscription.updated_at = datetime.now(timezone.utc)
            db.commit()
            org_id_for_uncomp = db_subscription.organization_id
        else:
            # New subscription from webhook — extract org from metadata
            org_id = metadata.get("organization_id")
            if not org_id:
                return

            plan = "yearly" if interval == "year" else "monthly"
            db_subscription = Subscription(
                organization_id=org_id,
                stripe_customer_id=sub.get("customer"),
                stripe_subscription_id=sub_id,
                stripe_price_id=price_id,
                status=sub.get("status"),
                plan=plan,
                quantity=quantity,
                current_period_start=cps,
                current_period_end=cpe,
                cancel_at_period_end=sub.get("cancel_at_period_end", False),
            )
            db.add(db_subscription)
            db.commit()
            org_id_for_uncomp = org_id

        # Auto-un-COMP: when a comped org starts paying via Stripe, flip
        # is_comped off so billing state matches reality. Per Sherri's
        # 2026-06-09 ask for Group 2 churches — they sit COMPED until their
        # legacy renewal date, at which point they sign up via the new link
        # and this webhook fires.
        if org_id_for_uncomp and sub.get("status") in ("active", "trialing"):
            org = db.query(Organization).filter(
                Organization.id == org_id_for_uncomp
            ).first()
            if org and org.is_comped:
                org.is_comped = False
                org.updated_at = datetime.now(timezone.utc)
                db.commit()
                logging.info(
                    "auto-un-COMP'd org %s on subscription %s status=%s",
                    org.id, sub_id, sub.get("status"),
                )

        # Platform-wide Zapier (Disciples Made's central Kit). Gated on
        # Toolkit price_id so future products can't accidentally fire.
        # fire_toolkit_* are idempotent via Subscription.zapier_*_at
        # columns — duplicate Stripe deliveries can't double-fire.
        try:
            from app.services.platform_webhook_service import (
                fire_toolkit_activated,
                fire_toolkit_canceled,
                is_toolkit_subscription,
            )
            current_status = sub.get("status")
            event_type = event.get("type") if isinstance(event, dict) else event.type
            if db_subscription and is_toolkit_subscription(db_subscription.stripe_price_id):
                if current_status in ("active", "trialing"):
                    fire_toolkit_activated(db, db_subscription)
                elif (
                    current_status in ("canceled", "unpaid", "incomplete_expired")
                    or event_type == "customer.subscription.deleted"
                ):
                    fire_toolkit_canceled(db, db_subscription)
        except Exception:
            logging.exception(
                "platform fire_toolkit_* failed for subscription %s", sub_id,
            )
    
    @staticmethod
    def handle_invoice_payment_succeeded(event: stripe.Event, db: Session) -> None:
        """Handle successful payment webhook"""
        inv = event.data.object
        if hasattr(inv, "to_dict"):
            inv = inv.to_dict()

        customer_id = inv.get("customer")
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()

        if subscription:
            payment = Payment(
                organization_id=subscription.organization_id,
                stripe_invoice_id=inv.get("id"),
                stripe_payment_intent_id=inv.get("payment_intent"),
                amount=inv.get("amount_paid", 0) / 100,
                currency=inv.get("currency", "usd"),
                status="succeeded",
                description=inv.get("description") or "Subscription payment",
                receipt_url=inv.get("hosted_invoice_url")
            )
            db.add(payment)
            db.commit()
    
    @staticmethod
    def handle_invoice_payment_failed(event: stripe.Event, db: Session) -> None:
        """Handle failed payment webhook"""
        inv = event.data.object
        if hasattr(inv, "to_dict"):
            inv = inv.to_dict()

        customer_id = inv.get("customer")
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()

        if subscription:
            payment = Payment(
                organization_id=subscription.organization_id,
                stripe_invoice_id=inv.get("id"),
                stripe_payment_intent_id=inv.get("payment_intent"),
                amount=inv.get("amount_due", 0) / 100,
                currency=inv.get("currency", "usd"),
                status="failed",
                description="Payment failed"
            )
            db.add(payment)
            db.commit()
    
    @staticmethod
    def get_price_info(price_id: str) -> Optional[stripe.Price]:
        """Get price details from Stripe"""
        try:
            return stripe.Price.retrieve(price_id)
        except stripe.error.InvalidRequestError:
            return None


stripe_service = StripeService()
