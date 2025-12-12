"""
Store models
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Time, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models import TenantScopedModel, BaseModel
from app.extensions import db


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


class StoreSettings(db.Model):
    """
    Store-specific configuration settings.
    One-to-one relationship with Store.
    """
    __tablename__ = 'store_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey('stores.id'), nullable=False, unique=True, index=True)

    # Operating hours (JSON format: {"monday": {"open": "08:00", "close": "18:00"}, ...})
    operating_hours = Column(JSON, nullable=True)

    # Receipt settings
    receipt_header = Column(Text, nullable=True)  # Custom text at top of receipt
    receipt_footer = Column(Text, nullable=True)  # Custom text at bottom of receipt
    print_receipt_by_default = Column(Boolean, nullable=False, default=True)

    # Store-specific contact (overrides tenant if set)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)

    # Inventory settings
    allow_negative_stock = Column(Boolean, nullable=False, default=False)
    low_stock_threshold = Column(db.Integer, nullable=False, default=10)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    store = relationship('Store', backref=db.backref('settings', uselist=False, lazy='joined'))

    def __repr__(self):
        return f'<StoreSettings store_id={self.store_id}>'

    def to_dict(self):
        """Convert settings to dictionary."""
        return {
            'operating_hours': self.operating_hours,
            'receipt_header': self.receipt_header,
            'receipt_footer': self.receipt_footer,
            'print_receipt_by_default': self.print_receipt_by_default,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'allow_negative_stock': self.allow_negative_stock,
            'low_stock_threshold': self.low_stock_threshold,
        }
