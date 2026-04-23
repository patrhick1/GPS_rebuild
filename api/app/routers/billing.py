"""
Billing API endpoints for Stripe integration
"""
from typing import Optional
from datetime import datetime, timezone
import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limits import limiter, ADMIN_RATE
from app.core.exceptions import handle_exception, handle_stripe_exception
from app.dependencies.auth import (
    get_current_verified_user,
    require_admin,
    require_primary_admin,
    require_primary_admin_no_impersonation
)
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription import Subscription, Payment
from app.models.membership import Membership
from app.models.audit_log import AuditLog
from app.services.stripe_service import stripe_service

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/config")
@limiter.limit(ADMIN_RATE)
async def get_billing_config(
    request: Request,
    current_user: User = Depends(get_current_verified_user)
):
    """Get public Stripe configuration"""
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "prices": {
            "monthly": settings.STRIPE_PRICE_MONTHLY,
            "yearly": settings.STRIPE_PRICE_YEARLY
        }
    }


@router.get("/subscription/status")
@limiter.limit(ADMIN_RATE)
async def get_subscription_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get subscription status for the organization — accessible to all admins (primary and secondary)."""
    membership = next(
        (m for m in current_user.memberships if m.organization_id is not None),
        None,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )

    subscription = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).order_by(desc(Subscription.created_at)).first()

    sub_status = subscription.status if subscription else "no_subscription"

    result = {"status": sub_status}

    # For secondary admins, include the primary admin's name/email so the
    # frontend can tell them who to contact about subscription issues.
    if not membership.is_primary_admin:
        primary_mem = db.query(Membership).filter(
            Membership.organization_id == membership.organization_id,
            Membership.is_primary_admin == True,
        ).first()
        if primary_mem:
            primary_user = db.query(User).filter(User.id == primary_mem.user_id).first()
            if primary_user:
                name_parts = [primary_user.first_name, primary_user.last_name]
                result["primary_admin_name"] = " ".join(p for p in name_parts if p)
                result["primary_admin_email"] = primary_user.email

    return result


@router.get("/subscription")
@limiter.limit(ADMIN_RATE)
async def get_subscription(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin)
):
    """Get current subscription for the organization"""
    
    # Get user's organization
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
    
    if not subscription or (subscription.status == "incomplete" and not subscription.stripe_subscription_id):
        return {
            "status": "none",
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "stripe_id": organization.stripe_id
            }
        }
    
    # If still incomplete, re-sync from Stripe (webhooks may not have fired in dev)
    if subscription.status == "incomplete" and subscription.stripe_subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            if stripe_sub.status != subscription.status:
                subscription.status = stripe_sub.status
                if stripe_sub.get("current_period_start"):
                    subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
                if stripe_sub.get("current_period_end"):
                    subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
                db.commit()
        except Exception:
            pass

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
        try:
            methods = stripe_service.get_payment_methods(subscription.stripe_customer_id)
            payment_methods = [{
                "id": m.id,
                "brand": m.card.brand,
                "last4": m.card.last4,
                "exp_month": m.card.exp_month,
                "exp_year": m.card.exp_year,
                "is_default": m.id == stripe_service.get_or_create_customer(organization, current_user.email).invoice_settings.default_payment_method
            } for m in methods]
        except stripe.error.InvalidRequestError:
            pass
    
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
@limiter.limit(ADMIN_RATE)
async def create_subscription(
    request: Request,
    plan: str,  # "monthly" or "yearly"
    payment_method_id: str,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
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
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
            plan=plan,
            quantity=quantity,
            payment_method_id=payment_method_id
        )

        # Upsert local subscription record — one row per organization.
        # If an earlier attempt left an "incomplete" zombie with NULL ids,
        # reuse it; otherwise update the existing real row in place so
        # resubscribes don't accumulate duplicate rows.
        new_sub = result["db_subscription"]
        existing = db.query(Subscription).filter(
            Subscription.organization_id == organization.id
        ).order_by(desc(Subscription.created_at)).first()

        if existing:
            existing.stripe_customer_id = new_sub.stripe_customer_id
            existing.stripe_subscription_id = new_sub.stripe_subscription_id
            existing.stripe_price_id = new_sub.stripe_price_id
            existing.status = new_sub.status
            existing.plan = new_sub.plan
            existing.quantity = new_sub.quantity
            existing.current_period_start = new_sub.current_period_start
            existing.current_period_end = new_sub.current_period_end
            existing.trial_start = new_sub.trial_start
            existing.trial_end = new_sub.trial_end
            existing.canceled_at = None
            existing.cancel_at_period_end = False
        else:
            db.add(new_sub)
        db.commit()
        
        # Save card info to organization so it shows on the billing page
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        organization.card_brand = pm.card.brand
        organization.card_last_four = pm.card.last4
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
        
        # Get client secret for payment confirmation.
        # Stripe API 2026-02-25+ removed payment_intent from Invoice; use confirmation_secret instead.
        client_secret = None
        inv = result["subscription"].get("latest_invoice")
        if inv:
            cs = inv.get("confirmation_secret")
            if cs:
                client_secret = cs.get("client_secret")
        
        return {
            "subscription_id": result["subscription"].id,
            "status": result["subscription"].status,
            "client_secret": client_secret,
            "requires_action": result["subscription"].status == "incomplete"
        }
        
    except Exception as e:
        raise handle_stripe_exception(e)


@router.post("/subscription/cancel")
@limiter.limit(ADMIN_RATE)
async def cancel_subscription(
    request: Request,
    at_period_end: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
):
    """Cancel the current subscription"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
        subscription.canceled_at = datetime.now(timezone.utc) if not at_period_end else None
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
        
    except stripe.error.InvalidRequestError as e:
        if e.code == "resource_missing":
            # Subscription no longer exists in Stripe — mark cancelled locally
            subscription.status = "canceled"
            subscription.canceled_at = datetime.now(timezone.utc)
            subscription.cancel_at_period_end = False
            audit_log = AuditLog(
                user_id=current_user.id,
                action="subscription_canceled",
                target_type="organization",
                target_id=membership.organization_id,
                details={"at_period_end": at_period_end, "note": "subscription not found in Stripe, marked cancelled locally"}
            )
            db.add(audit_log)
            db.commit()
            return {
                "message": "Subscription canceled",
                "status": "canceled",
                "cancel_at_period_end": False
            }
        raise handle_stripe_exception(e)
    except Exception as e:
        raise handle_stripe_exception(e)


@router.post("/subscription/reactivate")
@limiter.limit(ADMIN_RATE)
async def reactivate_subscription(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
):
    """Reactivate a subscription that was set to cancel at period end"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
        raise handle_stripe_exception(e)


@router.post("/payment-method")
@limiter.limit(ADMIN_RATE)
async def add_payment_method(
    request: Request,
    payment_method_id: str,
    set_default: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
):
    """Add a new payment method"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
        raise handle_stripe_exception(e)


@router.delete("/payment-method/{payment_method_id}")
@limiter.limit(ADMIN_RATE)
async def remove_payment_method(
    request: Request,
    payment_method_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
):
    """Remove a payment method"""

    try:
        stripe_service.detach_payment_method(payment_method_id)
        return {"message": "Payment method removed"}
    except Exception as e:
        raise handle_stripe_exception(e)


@router.post("/portal")
@limiter.limit(ADMIN_RATE)
async def create_billing_portal(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin_no_impersonation)
):
    """Create a Stripe Customer Portal session — primary admin only, no impersonation"""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )

    customer = stripe_service.get_or_create_customer(membership.organization, current_user.email)

    try:
        session = stripe_service.create_billing_portal_session(
            customer_id=customer.id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return {"url": session.url}
    except Exception as e:
        raise handle_stripe_exception(e)


@router.get("/invoices")
@limiter.limit(ADMIN_RATE)
async def get_invoices(
    request: Request,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin)
):
    """Get payment history / invoices"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
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
    
    # Also get from Stripe for complete history. Pick the most recent
    # subscription row that actually has a Stripe customer id — older rows
    # may exist from abandoned "incomplete" attempts with NULL customer_id.
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id,
        Subscription.stripe_customer_id.isnot(None),
    ).order_by(desc(Subscription.created_at)).first()

    stripe_invoices = []
    if subscription and subscription.stripe_customer_id:
        try:
            stripe_invoices = stripe_service.get_invoices(
                subscription.stripe_customer_id,
                limit=limit
            )
        except stripe.error.InvalidRequestError as e:
            # Only swallow "no such customer" — surface everything else so the
            # UI can show a real error instead of a silently empty tab.
            if "No such customer" not in str(e):
                raise handle_stripe_exception(e)
    
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
            "amount_due": inv.amount_due / 100,
            "currency": inv.currency,
            "status": inv.status,
            "receipt_url": inv.hosted_invoice_url,
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
    try:
        if event.type in ("customer.subscription.updated", "customer.subscription.created"):
            stripe_service.handle_subscription_updated(event, db)
        elif event.type == "customer.subscription.deleted":
            stripe_service.handle_subscription_updated(event, db)
        elif event.type == "invoice.payment_succeeded":
            stripe_service.handle_invoice_payment_succeeded(event, db)
        elif event.type == "invoice.payment_failed":
            stripe_service.handle_invoice_payment_failed(event, db)
    except Exception as e:
        logging.error(f"Webhook handler error for {event.type}: {e}", exc_info=True)

    return {"status": "success"}
