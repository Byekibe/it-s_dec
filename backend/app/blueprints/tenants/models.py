"""
Tenant models
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models import BaseModel


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
