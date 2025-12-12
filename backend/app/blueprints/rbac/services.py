"""
RBAC service with business logic for role and permission management.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import joinedload
from flask import g

from app.extensions import db
from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission
from app.blueprints.users.models import User
from app.blueprints.tenants.models import TenantUser
from app.blueprints.stores.models import Store
from app.core.exceptions import (
    RoleNotFoundError,
    UserNotFoundError,
    StoreNotFoundError,
    DuplicateResourceError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
)


class RBACService:
    """Service handling RBAC operations."""

    # ==================== Roles ====================

    @staticmethod
    def list_roles() -> dict:
        """
        List all roles in the current tenant.

        Returns:
            Dict with roles list and total count
        """
        tenant_id = g.tenant.id

        roles = db.session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).order_by(Role.is_system_role.desc(), Role.name).all()

        return {
            "roles": roles,
            "total": len(roles),
        }

    @staticmethod
    def get_role(role_id: UUID) -> dict:
        """
        Get a specific role with its permissions.

        Args:
            role_id: UUID of the role

        Returns:
            Dict with role data, permissions, and user count

        Raises:
            RoleNotFoundError: If role not found or not in tenant
        """
        tenant_id = g.tenant.id

        role = db.session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).first()

        if not role:
            raise RoleNotFoundError()

        # Get permissions for this role
        permissions = db.session.query(Permission).join(
            RolePermission, RolePermission.permission_id == Permission.id
        ).filter(
            RolePermission.role_id == role_id
        ).all()

        # Get user count with this role
        user_count = db.session.query(UserRole).filter(
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id
        ).count()

        return {
            "role": role,
            "permissions": permissions,
            "user_count": user_count,
        }

    @staticmethod
    def create_role(
        name: str,
        description: Optional[str] = None,
        permission_ids: Optional[List[UUID]] = None
    ) -> dict:
        """
        Create a new custom role in the current tenant.

        Args:
            name: Role name
            description: Role description (optional)
            permission_ids: List of permission UUIDs to assign

        Returns:
            Dict with created role and permissions

        Raises:
            DuplicateResourceError: If role name already exists in tenant
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        # Check if role name already exists
        existing = db.session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == name,
            Role.deleted_at.is_(None)
        ).first()

        if existing:
            raise DuplicateResourceError(f"Role '{name}' already exists")

        # Create role
        role = Role(
            tenant_id=tenant_id,
            name=name,
            description=description,
            is_system_role=False,
            created_by=current_user_id,
            updated_by=current_user_id
        )
        db.session.add(role)
        db.session.flush()

        # Assign permissions
        permissions = []
        permission_ids = permission_ids or []
        for perm_id in permission_ids:
            permission = db.session.get(Permission, perm_id)
            if not permission:
                raise NotFoundError(f"Permission {perm_id} not found")

            role_permission = RolePermission(
                role_id=role.id,
                permission_id=perm_id
            )
            db.session.add(role_permission)
            permissions.append(permission)

        db.session.commit()

        return {
            "role": role,
            "permissions": permissions,
            "user_count": 0,
        }

    @staticmethod
    def update_role(
        role_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission_ids: Optional[List[UUID]] = None
    ) -> dict:
        """
        Update a role's details and permissions.

        Args:
            role_id: UUID of the role
            name: New name (optional)
            description: New description (optional)
            permission_ids: New list of permission UUIDs (optional, replaces existing)

        Returns:
            Dict with updated role and permissions

        Raises:
            RoleNotFoundError: If role not found
            ForbiddenError: If trying to modify system role name
            DuplicateResourceError: If new name already exists
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        role = db.session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).first()

        if not role:
            raise RoleNotFoundError()

        # System roles can have permissions modified but not name
        if role.is_system_role and name is not None and name != role.name:
            raise ForbiddenError("Cannot rename system roles")

        if name is not None and name != role.name:
            # Check for duplicate name
            existing = db.session.query(Role).filter(
                Role.tenant_id == tenant_id,
                Role.name == name,
                Role.id != role_id,
                Role.deleted_at.is_(None)
            ).first()

            if existing:
                raise DuplicateResourceError(f"Role '{name}' already exists")

            role.name = name

        if description is not None:
            role.description = description

        role.updated_at = datetime.utcnow()
        role.updated_by = current_user_id

        # Update permissions if provided
        permissions = []
        if permission_ids is not None:
            # Remove existing permissions
            db.session.query(RolePermission).filter(
                RolePermission.role_id == role_id
            ).delete()

            # Add new permissions
            for perm_id in permission_ids:
                permission = db.session.get(Permission, perm_id)
                if not permission:
                    raise NotFoundError(f"Permission {perm_id} not found")

                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=perm_id
                )
                db.session.add(role_permission)
                permissions.append(permission)
        else:
            # Get current permissions
            permissions = db.session.query(Permission).join(
                RolePermission, RolePermission.permission_id == Permission.id
            ).filter(
                RolePermission.role_id == role_id
            ).all()

        db.session.commit()

        # Get user count
        user_count = db.session.query(UserRole).filter(
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id
        ).count()

        return {
            "role": role,
            "permissions": permissions,
            "user_count": user_count,
        }

    @staticmethod
    def delete_role(role_id: UUID) -> Role:
        """
        Soft delete a role.

        Args:
            role_id: UUID of the role

        Returns:
            Deleted Role object

        Raises:
            RoleNotFoundError: If role not found
            ForbiddenError: If trying to delete system role
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        role = db.session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).first()

        if not role:
            raise RoleNotFoundError()

        if role.is_system_role:
            raise ForbiddenError("Cannot delete system roles")

        # Remove all user role assignments for this role
        db.session.query(UserRole).filter(
            UserRole.role_id == role_id
        ).delete()

        # Soft delete the role
        role.deleted_at = datetime.utcnow()
        role.updated_at = datetime.utcnow()
        role.updated_by = current_user_id

        db.session.commit()

        return role

    # ==================== Permissions ====================

    @staticmethod
    def list_permissions(resource: Optional[str] = None) -> dict:
        """
        List all available permissions.

        Args:
            resource: Filter by resource name (optional)

        Returns:
            Dict with permissions list and total count
        """
        query = db.session.query(Permission)

        if resource:
            query = query.filter(Permission.resource == resource)

        permissions = query.order_by(Permission.resource, Permission.action).all()

        return {
            "permissions": permissions,
            "total": len(permissions),
        }

    # ==================== User Role Assignments ====================

    @staticmethod
    def get_user_roles(user_id: UUID) -> dict:
        """
        Get all role assignments for a user in the current tenant.

        Args:
            user_id: UUID of the user

        Returns:
            Dict with user_id and list of role assignments

        Raises:
            UserNotFoundError: If user not found or not in tenant
        """
        tenant_id = g.tenant.id

        # Verify user exists and is in tenant
        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        # Get role assignments, eagerly loading role and store names to avoid N+1 queries
        role_assignments = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        ).options(
            joinedload(UserRole.role),
            joinedload(UserRole.store)
        ).all()

        return {
            "user_id": user_id,
            "roles": role_assignments,  # Return model objects directly for schema to handle
        }

    @staticmethod
    def assign_role_to_user(
        user_id: UUID,
        role_id: UUID,
        store_id: Optional[UUID] = None
    ) -> dict:
        """
        Assign a role to a user.

        Args:
            user_id: UUID of the user
            role_id: UUID of the role
            store_id: UUID of store for store-specific role (optional)

        Returns:
            Dict with user_id and updated role assignments

        Raises:
            UserNotFoundError: If user not found or not in tenant
            RoleNotFoundError: If role not found or not in tenant
            StoreNotFoundError: If store not found or not in tenant
            DuplicateResourceError: If role already assigned
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        # Verify user exists and is in tenant
        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        # Verify role exists and is in tenant
        role = db.session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).first()

        if not role:
            raise RoleNotFoundError()

        # Verify store if provided
        if store_id:
            store = db.session.query(Store).filter(
                Store.id == store_id,
                Store.tenant_id == tenant_id,
                Store.deleted_at.is_(None)
            ).first()

            if not store:
                raise StoreNotFoundError()

        # Check if assignment already exists
        existing = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id,
            UserRole.store_id == store_id if store_id else UserRole.store_id.is_(None)
        ).first()

        if existing:
            raise DuplicateResourceError("Role already assigned to user")

        # Create assignment
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            store_id=store_id,
            assigned_at=datetime.utcnow(),
            assigned_by=current_user_id
        )
        db.session.add(user_role)
        db.session.commit()

        return RBACService.get_user_roles(user_id)

    @staticmethod
    def revoke_role_from_user(
        user_id: UUID,
        role_id: UUID,
        store_id: Optional[UUID] = None
    ) -> dict:
        """
        Revoke a role from a user.

        Args:
            user_id: UUID of the user
            role_id: UUID of the role
            store_id: UUID of store for store-specific role (optional)

        Returns:
            Dict with user_id and updated role assignments

        Raises:
            UserNotFoundError: If user not found or not in tenant
            NotFoundError: If role assignment not found
        """
        tenant_id = g.tenant.id

        # Verify user exists and is in tenant
        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        # Find and delete the assignment
        query = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id
        )

        if store_id:
            query = query.filter(UserRole.store_id == store_id)
        else:
            query = query.filter(UserRole.store_id.is_(None))

        assignment = query.first()

        if not assignment:
            raise NotFoundError("Role assignment not found")

        db.session.delete(assignment)
        db.session.commit()

        return RBACService.get_user_roles(user_id)
