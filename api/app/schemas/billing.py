"""
Billing/Payment schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class SubscriptionResponse(BaseModel):
    id: UUID
    status: str
    plan: Optional[str]
    quantity: int
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    cancel_at_period_end: Optional[datetime]
    canceled_at: Optional[datetime]
    stripe_subscription_id: Optional[str]
    
    class Config:
        from_attributes = True


class PaymentMethodResponse(BaseModel):
    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool


class InvoiceResponse(BaseModel):
    id: str
    amount_paid: float
    currency: str
    status: str
    hosted_invoice_url: Optional[str]
    invoice_pdf: Optional[str]
    created: int


class PaymentHistoryResponse(BaseModel):
    id: UUID
    amount: float
    currency: str
    status: str
    description: Optional[str]
    receipt_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UpcomingInvoiceResponse(BaseModel):
    amount_due: float
    currency: str
    due_date: int
    period_start: int
    period_end: int


class SubscribeRequest(BaseModel):
    plan: str  # "monthly" or "yearly"
    payment_method_id: str
    quantity: int = 1


class SubscribeResponse(BaseModel):
    subscription_id: str
    status: str
    client_secret: Optional[str]
    requires_action: bool


class CancelSubscriptionResponse(BaseModel):
    message: str
    status: str
    cancel_at_period_end: bool


class BillingConfigResponse(BaseModel):
    publishable_key: Optional[str]
    prices: dict
