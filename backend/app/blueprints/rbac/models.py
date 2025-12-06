"""
RBAC (Role-Based Access Control) models
"""
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models import BaseModel, TenantScopedModel


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
