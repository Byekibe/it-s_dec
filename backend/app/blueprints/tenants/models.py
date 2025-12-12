"""
Tenant models
"""
from datetime import datetime
from enum import Enum as PyEnum

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index, UniqueConstraint, Integer, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models import BaseModel
from app.extensions import db


class TenantStatus(PyEnum):
    """Tenant account status."""
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"


class Tenant(BaseModel):
    """
    Top-level entity representing a company/organization.
    Primary container for data segregation.
    """
    __tablename__ = 'tenants'

    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(TenantStatus), default=TenantStatus.TRIAL, nullable=False, index=True)
    trial_ends_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    users = relationship('TenantUser', back_populates='tenant', cascade='all, delete-orphan')
    stores = relationship('Store', back_populates='tenant', cascade='all, delete-orphan')
    roles = relationship('Role', back_populates='tenant', cascade='all, delete-orphan')

    @property
    def is_active(self):
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE

    @property
    def is_trial(self):
        """Check if tenant is in trial period."""
        return self.status == TenantStatus.TRIAL

    @property
    def is_deleted(self):
        """Check if tenant is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Mark tenant as deleted."""
        self.deleted_at = datetime.utcnow()
        self.status = TenantStatus.CANCELED

    def __repr__(self):
        return f'<Tenant {self.name} ({self.slug})>'


class TenantUser(BaseModel):
    """
    Links a user to a tenant, establishing tenant membership.
    """
    __tablename__ = 'tenant_users'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship('User', back_populates='tenant_memberships', foreign_keys=[user_id])
    tenant = relationship('Tenant', back_populates='users')
    inviter = relationship('User', foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),
        Index('idx_tenant_users_tenant', 'tenant_id'),
    )

    def __repr__(self):
        return f'<TenantUser user_id={self.user_id} tenant_id={self.tenant_id}>'


class TenantSettings(db.Model):
    """
    Tenant-specific configuration settings.
    One-to-one relationship with Tenant.
    """
    __tablename__ = 'tenant_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, unique=True, index=True)

    # Regional settings
    timezone = Column(String(50), nullable=False, default='Africa/Nairobi')
    currency = Column(String(3), nullable=False, default='KES')
    locale = Column(String(10), nullable=False, default='en-KE')

    # Display formats
    date_format = Column(String(20), nullable=False, default='DD/MM/YYYY')
    time_format = Column(String(10), nullable=False, default='24h')

    # Tax settings
    tax_rate = Column(Numeric(5, 2), nullable=False, default=16.00)  # Kenya VAT 16%
    tax_inclusive_pricing = Column(Boolean, nullable=False, default=True)
    tax_id = Column(String(50), nullable=True)  # KRA PIN

    # Fiscal/Accounting
    fiscal_year_start_month = Column(Integer, nullable=False, default=1)  # January
    fiscal_year_start_day = Column(Integer, nullable=False, default=1)

    # Business info (for receipts/invoices)
    business_name = Column(String(255), nullable=True)
    business_address = Column(String(500), nullable=True)
    business_phone = Column(String(50), nullable=True)
    business_email = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    tenant = relationship('Tenant', backref=db.backref('settings', uselist=False, lazy='joined'))

    def __repr__(self):
        return f'<TenantSettings tenant_id={self.tenant_id}>'

    def to_dict(self):
        """Convert settings to dictionary."""
        return {
            'timezone': self.timezone,
            'currency': self.currency,
            'locale': self.locale,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 16.00,
            'tax_inclusive_pricing': self.tax_inclusive_pricing,
            'tax_id': self.tax_id,
            'fiscal_year_start_month': self.fiscal_year_start_month,
            'fiscal_year_start_day': self.fiscal_year_start_day,
            'business_name': self.business_name,
            'business_address': self.business_address,
            'business_phone': self.business_phone,
            'business_email': self.business_email,
        }
