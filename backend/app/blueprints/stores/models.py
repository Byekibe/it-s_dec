"""
Store models
"""
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models import TenantScopedModel, BaseModel


class Store(TenantScopedModel):
    """
    A specific location or branch belonging to a tenant.
    All stores must belong to exactly one tenant.
    Note: Store inherits tenant_id from TenantScopedModel, no need to redeclare.
    """
    __tablename__ = 'stores'

    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship('Tenant', back_populates='stores')
    store_users = relationship('StoreUser', back_populates='store', cascade='all, delete-orphan')
    user_roles = relationship('UserRole', back_populates='store')

    __table_args__ = (
        Index('idx_stores_tenant_active', 'tenant_id', 'is_active'),
    )

    def __repr__(self):
        return f'<Store {self.name} (Tenant: {self.tenant_id})>'


class StoreUser(BaseModel):
    """
    Links a user to specific stores they can access within a tenant.
    """
    __tablename__ = 'store_users'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey('stores.id'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship('User', back_populates='store_assignments', foreign_keys=[user_id])
    store = relationship('Store', back_populates='store_users')
    assigner = relationship('User', foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'store_id', name='uq_user_store'),
        Index('idx_store_users_tenant', 'tenant_id'),
        Index('idx_store_users_store', 'store_id'),
    )

    def __repr__(self):
        return f'<StoreUser user_id={self.user_id} store_id={self.store_id}>'
