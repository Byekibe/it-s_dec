"""
Subscription models for plans and tenant subscriptions.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions import db


class SubscriptionStatus(PyEnum):
    """Subscription status options."""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class PaymentMethod(PyEnum):
    """Payment method options."""
    NONE = "none"
    MPESA = "mpesa"
    MANUAL = "manual"


class Plan(db.Model):
    """
    Subscription plan definition.
    Global model - not tenant-scoped.
    """
    __tablename__ = 'plans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Pricing (in KES)
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0)
    price_yearly = Column(Numeric(10, 2), nullable=False, default=0)

    # Limits
    max_users = Column(Integer, nullable=True)  # NULL = unlimited
    max_stores = Column(Integer, nullable=True)
    max_products = Column(Integer, nullable=True)

    # Features (JSON for flexibility)
    features = Column(JSON, nullable=True)

    # Plan settings
    is_active = Column(Boolean, nullable=False, default=True)
    trial_days = Column(Integer, nullable=False, default=14)
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship('Subscription', back_populates='plan')

    def __repr__(self):
        return f'<Plan {self.name} ({self.slug})>'

    def to_dict(self):
        """Convert plan to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price_monthly': float(self.price_monthly) if self.price_monthly else 0,
            'price_yearly': float(self.price_yearly) if self.price_yearly else 0,
            'max_users': self.max_users,
            'max_stores': self.max_stores,
            'max_products': self.max_products,
            'features': self.features or {},
            'trial_days': self.trial_days,
        }


class Subscription(db.Model):
    """
    Tenant subscription to a plan.
    One subscription per tenant.
    """
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, unique=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('plans.id'), nullable=False, index=True)

    # Status
    status = Column(String(20), nullable=False, default=SubscriptionStatus.TRIALING.value)

    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)

    # Trial
    trial_ends_at = Column(DateTime, nullable=True)

    # Cancellation
    canceled_at = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    # Payment
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.NONE.value)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship('Tenant', backref=db.backref('subscription', uselist=False, lazy='joined'))
    plan = relationship('Plan', back_populates='subscriptions')

    def __repr__(self):
        return f'<Subscription tenant_id={self.tenant_id} plan={self.plan_id} status={self.status}>'

    @property
    def is_active(self):
        """Check if subscription allows access."""
        return self.status in [SubscriptionStatus.TRIALING.value, SubscriptionStatus.ACTIVE.value]

    @property
    def is_trialing(self):
        """Check if subscription is in trial."""
        return self.status == SubscriptionStatus.TRIALING.value

    def to_dict(self):
        """Convert subscription to dictionary."""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'plan_id': str(self.plan_id),
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'payment_method': self.payment_method,
        }
