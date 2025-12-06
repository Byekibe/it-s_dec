"""
Core Models for Multi-Tenant SaaS Application
Flask-SQLAlchemy with PostgreSQL
"""
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Text, Numeric, Index, UniqueConstraint, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ============================================================================
# Base Model with Common Fields
# ============================================================================

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


# ============================================================================
# Enums
# ============================================================================

class TenantStatus(PyEnum):
    """Tenant account status."""
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"


# ============================================================================
# Primary Entity Models
# ============================================================================

class User(BaseModel):
    """
    Global user model representing a person who can log in.
    A user can belong to multiple tenants.
    """
    __tablename__ = 'users'

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant_memberships = relationship('TenantUser', back_populates='user', cascade='all, delete-orphan')
    store_assignments = relationship('StoreUser', back_populates='user', cascade='all, delete-orphan')
    role_assignments = relationship('UserRole', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


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


class Role(TenantScopedModel):
    """
    A named set of permissions defined within a tenant.
    Roles are tenant-specific and can be assigned to users.
    Note: Role inherits tenant_id from TenantScopedModel, no need to redeclare.
    """
    __tablename__ = 'roles'

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)

    # Relationships
    tenant = relationship('Tenant', back_populates='roles')
    permissions = relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')
    user_assignments = relationship('UserRole', back_populates='role', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_role_name_per_tenant'),
        Index('idx_roles_tenant_system', 'tenant_id', 'is_system_role'),
    )

    def __repr__(self):
        return f'<Role {self.name} (Tenant: {self.tenant_id})>'


class Permission(BaseModel):
    """
    Global permission representing a single granular action.
    Permissions are code-defined and seeded, not created by users.
    """
    __tablename__ = 'permissions'

    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    role_assignments = relationship('RolePermission', back_populates='permission')

    __table_args__ = (
        Index('idx_permissions_resource_action', 'resource', 'action'),
    )

    def __repr__(self):
        return f'<Permission {self.name}>'


# ============================================================================
# Junction (Link) Models
# ============================================================================

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


class UserRole(BaseModel):
    """
    Assigns a role to a user, either globally within tenant or scoped to a specific store.
    If store_id is NULL, role applies to entire tenant.
    If store_id is set, role applies only to that specific store.
    """
    __tablename__ = 'user_roles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey('stores.id'), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship('User', back_populates='role_assignments', foreign_keys=[user_id])
    role = relationship('Role', back_populates='user_assignments')
    store = relationship('Store', back_populates='user_roles')
    assigner = relationship('User', foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'store_id', name='uq_user_role_store'),
        Index('idx_user_roles_tenant', 'tenant_id'),
        Index('idx_user_roles_store', 'store_id'),
        Index('idx_user_roles_user_tenant', 'user_id', 'tenant_id'),
    )

    @property
    def is_tenant_wide(self):
        """Check if role applies to entire tenant."""
        return self.store_id is None

    def __repr__(self):
        scope = f"store_id={self.store_id}" if self.store_id else "tenant-wide"
        return f'<UserRole user_id={self.user_id} role_id={self.role_id} ({scope})>'


class RolePermission(BaseModel):
    """
    Links permissions to roles, defining what a role can do.
    """
    __tablename__ = 'role_permissions'

    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('permissions.id'), nullable=False, index=True)

    # Relationships
    role = relationship('Role', back_populates='permissions')
    permission = relationship('Permission', back_populates='role_assignments')

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
        Index('idx_role_permissions_permission', 'permission_id'),
    )

    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'