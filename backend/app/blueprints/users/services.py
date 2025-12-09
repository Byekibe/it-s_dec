"""
User service with business logic for user management.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from flask import g

from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import TenantUser
from app.blueprints.stores.models import Store, StoreUser
from app.blueprints.rbac.models import Role, UserRole
from app.core.exceptions import (
    UserNotFoundError,
    DuplicateResourceError,
    BadRequestError,
    InvalidCredentialsError,
    ForbiddenError,
    StoreNotFoundError,
    RoleNotFoundError,
)


class UserService:
    """Service handling user management operations."""

    @staticmethod
    def get_current_user() -> User:
        """
        Get the currently authenticated user.

        Returns:
            User object from request context
        """
        return g.user

    @staticmethod
    def get_current_user_details() -> dict:
        """
        Get current user with roles and store assignments.

        Returns:
            Dict with user data, roles, and stores
        """
        user = g.user
        tenant_id = g.tenant.id

        # Get user's roles in this tenant
        role_assignments = db.session.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.tenant_id == tenant_id
        ).all()

        roles = []
        for ra in role_assignments:
            role = db.session.get(Role, ra.role_id)
            if role:
                store_name = None
                if ra.store_id:
                    store = db.session.get(Store, ra.store_id)
                    store_name = store.name if store else None
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "store_id": ra.store_id,
                    "store_name": store_name,
                })

        # Get user's store assignments in this tenant
        store_assignments = db.session.query(StoreUser).filter(
            StoreUser.user_id == user.id,
            StoreUser.tenant_id == tenant_id
        ).all()

        stores = []
        for sa in store_assignments:
            store = db.session.get(Store, sa.store_id)
            if store:
                stores.append({
                    "id": store.id,
                    "name": store.name,
                })

        return {
            "user": user,
            "roles": roles,
            "stores": stores,
        }

    @staticmethod
    def update_current_user(
        full_name: Optional[str] = None,
        current_password: Optional[str] = None,
        new_password: Optional[str] = None
    ) -> User:
        """
        Update current user's profile.

        Args:
            full_name: New full name (optional)
            current_password: Current password (required if changing password)
            new_password: New password (optional)

        Returns:
            Updated User object

        Raises:
            BadRequestError: If new_password provided without current_password
            InvalidCredentialsError: If current_password is incorrect
        """
        user = g.user

        if full_name is not None:
            user.full_name = full_name

        if new_password is not None:
            if current_password is None:
                raise BadRequestError("Current password required to change password")
            if not user.check_password(current_password):
                raise InvalidCredentialsError("Current password is incorrect")
            user.set_password(new_password)

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return user

    @staticmethod
    def list_users(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        store_id: Optional[UUID] = None
    ) -> dict:
        """
        List users in the current tenant with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            search: Search term for email or name
            is_active: Filter by active status
            store_id: Filter by store assignment

        Returns:
            Dict with users list and pagination info
        """
        tenant_id = g.tenant.id

        # Base query: users who are members of this tenant
        query = db.session.query(User).join(
            TenantUser, TenantUser.user_id == User.id
        ).filter(
            TenantUser.tenant_id == tenant_id
        )

        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if store_id:
            query = query.join(
                StoreUser, StoreUser.user_id == User.id
            ).filter(
                StoreUser.store_id == store_id,
                StoreUser.tenant_id == tenant_id
            )

        # Get total count
        total = query.count()

        # Apply pagination
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        users = query.all()

        # Calculate total pages
        pages = (total + per_page - 1) // per_page if total > 0 else 1

        return {
            "users": users,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    @staticmethod
    def get_user(user_id: UUID) -> dict:
        """
        Get a specific user in the current tenant with their roles and stores.

        Args:
            user_id: UUID of the user

        Returns:
            Dict with user data, roles, and stores

        Raises:
            UserNotFoundError: If user not found or not in tenant
        """
        tenant_id = g.tenant.id

        # Check user exists and is member of tenant
        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        # Get user's roles in this tenant
        role_assignments = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        ).all()

        roles = []
        for ra in role_assignments:
            role = db.session.get(Role, ra.role_id)
            if role:
                store_name = None
                if ra.store_id:
                    store = db.session.get(Store, ra.store_id)
                    store_name = store.name if store else None
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "store_id": ra.store_id,
                    "store_name": store_name,
                })

        # Get user's store assignments
        store_assignments = db.session.query(StoreUser).filter(
            StoreUser.user_id == user_id,
            StoreUser.tenant_id == tenant_id
        ).all()

        stores = []
        for sa in store_assignments:
            store = db.session.get(Store, sa.store_id)
            if store:
                stores.append({
                    "id": store.id,
                    "name": store.name,
                })

        return {
            "user": user,
            "roles": roles,
            "stores": stores,
        }

    @staticmethod
    def create_user(
        email: str,
        full_name: str,
        password: Optional[str] = None,
        role_ids: Optional[List[UUID]] = None,
        store_ids: Optional[List[UUID]] = None
    ) -> dict:
        """
        Create a new user and add them to the current tenant.

        Args:
            email: User's email
            full_name: User's full name
            password: User's password (optional - can be set later)
            role_ids: List of role UUIDs to assign
            store_ids: List of store UUIDs to assign

        Returns:
            Dict with created user data

        Raises:
            DuplicateResourceError: If email already exists
            RoleNotFoundError: If any role_id is invalid
            StoreNotFoundError: If any store_id is invalid
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id
        email = email.lower()

        # Check if email already exists
        existing_user = db.session.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            # Check if they're already in this tenant
            existing_membership = db.session.query(TenantUser).filter(
                TenantUser.user_id == existing_user.id,
                TenantUser.tenant_id == tenant_id
            ).first()

            if existing_membership:
                raise DuplicateResourceError("User already exists in this tenant")

            # Add existing user to this tenant
            user = existing_user
        else:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                is_active=True
            )
            if password:
                user.set_password(password)
            else:
                # Set a random unusable password - user will need to reset
                import secrets
                user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            db.session.flush()

        # Create tenant membership
        if not existing_user or not db.session.query(TenantUser).filter(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == tenant_id
        ).first():
            tenant_user = TenantUser(
                user_id=user.id,
                tenant_id=tenant_id,
                joined_at=datetime.utcnow(),
                invited_by=current_user_id
            )
            db.session.add(tenant_user)

        # Validate and assign roles
        role_ids = role_ids or []
        for role_id in role_ids:
            role = db.session.get(Role, role_id)
            if not role or role.tenant_id != tenant_id:
                raise RoleNotFoundError(f"Role {role_id} not found")

            # Check if assignment already exists
            existing_role = db.session.query(UserRole).filter(
                UserRole.user_id == user.id,
                UserRole.role_id == role_id,
                UserRole.store_id.is_(None)
            ).first()

            if not existing_role:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role_id,
                    tenant_id=tenant_id,
                    store_id=None,
                    assigned_at=datetime.utcnow(),
                    assigned_by=current_user_id
                )
                db.session.add(user_role)

        # Validate and assign stores
        store_ids = store_ids or []
        for store_id in store_ids:
            store = db.session.get(Store, store_id)
            if not store or store.tenant_id != tenant_id:
                raise StoreNotFoundError(f"Store {store_id} not found")

            # Check if assignment already exists
            existing_store = db.session.query(StoreUser).filter(
                StoreUser.user_id == user.id,
                StoreUser.store_id == store_id
            ).first()

            if not existing_store:
                store_user = StoreUser(
                    user_id=user.id,
                    store_id=store_id,
                    tenant_id=tenant_id,
                    assigned_at=datetime.utcnow(),
                    assigned_by=current_user_id
                )
                db.session.add(store_user)

        db.session.commit()

        # Return user details
        return UserService.get_user(user.id)

    @staticmethod
    def update_user(
        user_id: UUID,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        role_ids: Optional[List[UUID]] = None,
        store_ids: Optional[List[UUID]] = None
    ) -> dict:
        """
        Update a user's details (admin operation).

        Args:
            user_id: UUID of the user to update
            full_name: New full name
            is_active: New active status
            role_ids: New list of role UUIDs (replaces existing)
            store_ids: New list of store UUIDs (replaces existing)

        Returns:
            Dict with updated user data

        Raises:
            UserNotFoundError: If user not found or not in tenant
            ForbiddenError: If trying to deactivate self
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        # Get user and verify membership
        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        # Prevent self-deactivation
        if is_active is False and user_id == current_user_id:
            raise ForbiddenError("Cannot deactivate your own account")

        # Update basic fields
        if full_name is not None:
            user.full_name = full_name

        if is_active is not None:
            user.is_active = is_active

        user.updated_at = datetime.utcnow()

        # Update roles if provided
        if role_ids is not None:
            # Remove existing tenant-wide roles
            db.session.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                UserRole.store_id.is_(None)
            ).delete()

            # Add new roles
            for role_id in role_ids:
                role = db.session.get(Role, role_id)
                if not role or role.tenant_id != tenant_id:
                    raise RoleNotFoundError(f"Role {role_id} not found")

                user_role = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    tenant_id=tenant_id,
                    store_id=None,
                    assigned_at=datetime.utcnow(),
                    assigned_by=current_user_id
                )
                db.session.add(user_role)

        # Update store assignments if provided
        if store_ids is not None:
            # Remove existing store assignments
            db.session.query(StoreUser).filter(
                StoreUser.user_id == user_id,
                StoreUser.tenant_id == tenant_id
            ).delete()

            # Add new store assignments
            for store_id in store_ids:
                store = db.session.get(Store, store_id)
                if not store or store.tenant_id != tenant_id:
                    raise StoreNotFoundError(f"Store {store_id} not found")

                store_user = StoreUser(
                    user_id=user_id,
                    store_id=store_id,
                    tenant_id=tenant_id,
                    assigned_at=datetime.utcnow(),
                    assigned_by=current_user_id
                )
                db.session.add(store_user)

        db.session.commit()

        return UserService.get_user(user_id)

    @staticmethod
    def deactivate_user(user_id: UUID) -> User:
        """
        Deactivate a user (soft delete alternative).

        Args:
            user_id: UUID of the user to deactivate

        Returns:
            Updated User object

        Raises:
            UserNotFoundError: If user not found or not in tenant
            ForbiddenError: If trying to deactivate self
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        if user_id == current_user_id:
            raise ForbiddenError("Cannot deactivate your own account")

        user = db.session.get(User, user_id)
        if not user:
            raise UserNotFoundError()

        # Verify user is in this tenant
        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id
        ).first()

        if not tenant_user:
            raise UserNotFoundError()

        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return user
