"""
Stripe integration service for GPS billing
Handles subscriptions, payments, and webhook events
"""
import stripe
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription, Payment
from app.models.organization import Organization
from app.models.audit_log import AuditLog

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for handling Stripe operations"""
    
    @staticmethod
    def create_customer(organization: Organization, email: str) -> stripe.Customer:
        """Create a Stripe customer for an organization"""
        customer = stripe.Customer.create(
            name=organization.name,
            email=email,
            metadata={
                "organization_id": str(organization.id),
                "organization_key": organization.key
            }
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
        payment_method_id: Optional[str] = None
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
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id, "quantity": quantity}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.confirmation_secret"],
            metadata={
                "organization_id": str(organization.id),
                "organization_key": organization.key
            }
        )
        
        # Create local subscription record
        db_subscription = Subscription(
            organization_id=organization.id,
            stripe_customer_id=customer.id,
            stripe_subscription_id=subscription.id,
            stripe_price_id=price_id,
            status=subscription.status,
            plan=plan,
            quantity=quantity,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start) if subscription.get("current_period_start") else None,
            current_period_end=datetime.fromtimestamp(subscription.current_period_end) if subscription.get("current_period_end") else None,
            trial_start=datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
            trial_end=datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
        )
        
        return {
            "subscription": subscription,
            "db_subscription": db_subscription
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
    def get_payment_methods(customer_id: str) -> list:
        """Get all payment methods for a customer"""
        methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card"
        )
        return methods.data
    
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
            return stripe.Invoice.upcoming_preview(**params)
        except Exception:
            return None
    
    @staticmethod
    def get_invoices(customer_id: str, limit: int = 10) -> list:
        """Get recent invoices for a customer"""
        invoices = stripe.Invoice.list(
            customer=customer_id,
            limit=limit,
            expand=["data.charge"]
        )
        return invoices.data
    
    @staticmethod
    def construct_event(payload: bytes, sig_header: str) -> stripe.Event:
        """Verify and construct a webhook event"""
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    
    @staticmethod
    def handle_subscription_updated(event: stripe.Event, db: Session) -> None:
        """Handle subscription updated webhook"""
        subscription_data = event.data.object
        
        # Find local subscription
        db_subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_data.id
        ).first()
        
        if db_subscription:
            db_subscription.status = subscription_data.status
            db_subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
            db_subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)
            db_subscription.cancel_at_period_end = subscription_data.cancel_at_period_end
            db_subscription.quantity = subscription_data.items.data[0].quantity if subscription_data.items.data else 1
            db_subscription.updated_at = datetime.now(timezone.utc)
            
            db.commit()
    
    @staticmethod
    def handle_invoice_payment_succeeded(event: stripe.Event, db: Session) -> None:
        """Handle successful payment webhook"""
        invoice = event.data.object
        
        # Get organization from customer
        customer_id = invoice.customer
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            # Create payment record
            payment = Payment(
                organization_id=subscription.organization_id,
                stripe_invoice_id=invoice.id,
                stripe_payment_intent_id=invoice.payment_intent,
                amount=invoice.amount_paid / 100,  # Convert from cents
                currency=invoice.currency,
                status="succeeded",
                description=invoice.description or "Subscription payment",
                receipt_url=invoice.hosted_invoice_url
            )
            db.add(payment)
            
            # Log to audit
            audit_log = AuditLog(
                action="payment_succeeded",
                target_type="organization",
                target_id=subscription.organization_id,
                details={
                    "invoice_id": invoice.id,
                    "amount": float(payment.amount),
                    "currency": payment.currency
                }
            )
            db.add(audit_log)
            db.commit()
    
    @staticmethod
    def handle_invoice_payment_failed(event: stripe.Event, db: Session) -> None:
        """Handle failed payment webhook"""
        invoice = event.data.object
        
        customer_id = invoice.customer
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            # Create failed payment record
            payment = Payment(
                organization_id=subscription.organization_id,
                stripe_invoice_id=invoice.id,
                stripe_payment_intent_id=invoice.payment_intent,
                amount=invoice.amount_due / 100,
                currency=invoice.currency,
                status="failed",
                description="Payment failed"
            )
            db.add(payment)
            
            # Log to audit
            audit_log = AuditLog(
                action="payment_failed",
                target_type="organization",
                target_id=subscription.organization_id,
                details={
                    "invoice_id": invoice.id,
                    "amount": float(payment.amount),
                    "attempt_count": invoice.attempt_count
                }
            )
            db.add(audit_log)
            db.commit()
    
    @staticmethod
    def get_price_info(price_id: str) -> Optional[stripe.Price]:
        """Get price details from Stripe"""
        try:
            return stripe.Price.retrieve(price_id)
        except stripe.error.InvalidRequestError:
            return None


stripe_service = StripeService()
