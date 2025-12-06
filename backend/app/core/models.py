"""
Core Abstract Models for Multi-Tenant SaaS Application
These base classes provide common functionality for all models.
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class BaseModel(db.Model):
    """Abstract base model with common fields and methods."""
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TenantScopedModel(BaseModel):
    """Abstract base for tenant-scoped models with audit fields."""
    __abstract__ = True

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self):
        """Check if model is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.deleted_at = datetime.utcnow()


class StoreScopedModel(TenantScopedModel):
    """Abstract base for store-scoped models (scoped to both tenant AND store)."""
    __abstract__ = True

    store_id = Column(UUID(as_uuid=True), ForeignKey('stores.id'), nullable=False, index=True)
