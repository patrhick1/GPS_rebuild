"""
Billing API endpoints for Stripe integration
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.config import settings
from app.dependencies.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription import Subscription, Payment
from app.models.membership import Membership
from app.models.audit_log import AuditLog
from app.services.stripe_service import stripe_service

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/config")
async def get_billing_config(
    current_user: User = Depends(get_current_active_user)
):
    """Get public Stripe configuration"""
    return {
        "publishable_key": settings.STRIPE_SECRET_KEY.replace("sk_", "pk_") if settings.STRIPE_SECRET_KEY else None,
        "prices": {
            "monthly": settings.STRIPE_PRICE_MONTHLY,
            "yearly": settings.STRIPE_PRICE_YEARLY
        }
    }


@router.get("/subscription")
async def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get current subscription for the organization"""
    
    # Get user's organization
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    organization = membership.organization
    
    # Get subscription from database
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id
    ).order_by(desc(Subscription.created_at)).first()
    
    if not subscription:
        return {
            "status": "none",
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "stripe_id": organization.stripe_id
            }
        }
    
    # Get upcoming invoice if subscription is active
    upcoming_invoice = None
    if subscription.stripe_customer_id:
        upcoming = stripe_service.get_upcoming_invoice(
            subscription.stripe_customer_id,
            subscription.stripe_subscription_id
        )
        if upcoming:
            upcoming_invoice = {
                "amount_due": upcoming.amount_due / 100,
                "currency": upcoming.currency,
                "due_date": upcoming.due_date,
                "period_start": upcoming.period_start,
                "period_end": upcoming.period_end
            }
    
    # Get payment methods
    payment_methods = []
    if subscription.stripe_customer_id:
        methods = stripe_service.get_payment_methods(subscription.stripe_customer_id)
        payment_methods = [{
            "id": m.id,
            "brand": m.card.brand,
            "last4": m.card.last4,
            "exp_month": m.card.exp_month,
            "exp_year": m.card.exp_year,
            "is_default": m.id == stripe_service.get_or_create_customer(organization, current_user.email).invoice_settings.default_payment_method
        } for m in methods]
    
    return {
        "id": str(subscription.id),
        "status": subscription.status,
        "plan": subscription.plan,
        "quantity": subscription.quantity,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "trial_start": subscription.trial_start,
        "trial_end": subscription.trial_end,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at,
        "stripe_subscription_id": subscription.stripe_subscription_id,
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "card_brand": organization.card_brand,
            "card_last_four": organization.card_last_four
        },
        "upcoming_invoice": upcoming_invoice,
        "payment_methods": payment_methods
    }


@router.post("/subscribe")
async def create_subscription(
    plan: str,  # "monthly" or "yearly"
    payment_method_id: str,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new subscription"""
    
    # Get price ID based on plan
    price_id = settings.STRIPE_PRICE_MONTHLY if plan == "monthly" else settings.STRIPE_PRICE_YEARLY
    
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price not configured for {plan} plan"
        )
    
    # Get user's organization
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    organization = membership.organization
    
    try:
        result = stripe_service.create_subscription(
            organization=organization,
            price_id=price_id,
            quantity=quantity,
            payment_method_id=payment_method_id
        )
        
        # Save to database
        db.add(result["db_subscription"])
        db.commit()
        
        # Log to audit
        audit_log = AuditLog(
            user_id=current_user.id,
            action="subscription_created",
            target_type="organization",
            target_id=organization.id,
            details={
                "plan": plan,
                "quantity": quantity,
                "stripe_subscription_id": result["subscription"].id
            }
        )
        db.add(audit_log)
        db.commit()
        
        # Get client secret for payment if needed
        client_secret = None
        if hasattr(result["subscription"], 'latest_invoice') and result["subscription"].latest_invoice:
            if hasattr(result["subscription"].latest_invoice, 'payment_intent') and result["subscription"].latest_invoice.payment_intent:
                client_secret = result["subscription"].latest_invoice.payment_intent.client_secret
        
        return {
            "subscription_id": result["subscription"].id,
            "status": result["subscription"].status,
            "client_secret": client_secret,
            "requires_action": result["subscription"].status == "incomplete"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscription/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Cancel the current subscription"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).order_by(desc(Subscription.created_at)).first()
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        result = stripe_service.cancel_subscription(
            subscription.stripe_subscription_id,
            at_period_end=at_period_end
        )
        
        # Update local record
        subscription.status = result.status
        subscription.canceled_at = datetime.utcnow() if not at_period_end else None
        subscription.cancel_at_period_end = result.cancel_at_period_end
        
        # Log to audit
        audit_log = AuditLog(
            user_id=current_user.id,
            action="subscription_canceled" if not at_period_end else "subscription_scheduled_cancel",
            target_type="organization",
            target_id=membership.organization_id,
            details={"at_period_end": at_period_end}
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Subscription canceled" if not at_period_end else "Subscription will cancel at period end",
            "status": result.status,
            "cancel_at_period_end": result.cancel_at_period_end
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Reactivate a subscription that was set to cancel at period end"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).order_by(desc(Subscription.created_at)).first()
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        result = stripe_service.reactivate_subscription(subscription.stripe_subscription_id)
        
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        
        # Log to audit
        audit_log = AuditLog(
            user_id=current_user.id,
            action="subscription_reactivated",
            target_type="organization",
            target_id=membership.organization_id
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Subscription reactivated",
            "status": result.status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-method")
async def add_payment_method(
    payment_method_id: str,
    set_default: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Add a new payment method"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    organization = membership.organization
    
    # Get or create customer
    customer = stripe_service.get_or_create_customer(organization, current_user.email)
    
    try:
        # Attach payment method
        stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
        
        if set_default:
            stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
        
        # Update organization card info
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        organization.card_brand = payment_method.card.brand
        organization.card_last_four = payment_method.card.last4
        
        db.commit()
        
        return {"message": "Payment method added successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/payment-method/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Remove a payment method"""
    
    try:
        stripe_service.detach_payment_method(payment_method_id)
        return {"message": "Payment method removed"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/invoices")
async def get_invoices(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get payment history / invoices"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    # Get from local database first
    payments = db.query(Payment).filter(
        Payment.organization_id == membership.organization_id
    ).order_by(desc(Payment.created_at)).limit(limit).all()
    
    # Also get from Stripe for complete history
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).first()
    
    stripe_invoices = []
    if subscription and subscription.stripe_customer_id:
        stripe_invoices = stripe_service.get_invoices(
            subscription.stripe_customer_id,
            limit=limit
        )
    
    return {
        "payments": [{
            "id": str(p.id),
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status,
            "description": p.description,
            "receipt_url": p.receipt_url,
            "created_at": p.created_at
        } for p in payments],
        "stripe_invoices": [{
            "id": inv.id,
            "amount_paid": inv.amount_paid / 100,
            "currency": inv.currency,
            "status": inv.status,
            "hosted_invoice_url": inv.hosted_invoice_url,
            "invoice_pdf": inv.invoice_pdf,
            "created": inv.created
        } for inv in stripe_invoices]
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )
    
    try:
        event = stripe_service.construct_event(payload, sig_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Handle event types
    if event.type == "customer.subscription.updated":
        stripe_service.handle_subscription_updated(event, db)
    elif event.type == "customer.subscription.deleted":
        stripe_service.handle_subscription_updated(event, db)
    elif event.type == "invoice.payment_succeeded":
        stripe_service.handle_invoice_payment_succeeded(event, db)
    elif event.type == "invoice.payment_failed":
        stripe_service.handle_invoice_payment_failed(event, db)
    
    return {"status": "success"}


from datetime import datetime
