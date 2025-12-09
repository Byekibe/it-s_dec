"""
Store service with business logic for store management.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from flask import g

from app.extensions import db
from app.blueprints.stores.models import Store, StoreUser
from app.blueprints.tenants.models import TenantUser
from app.blueprints.users.models import User
from app.core.exceptions import (
    StoreNotFoundError,
    UserNotFoundError,
    BadRequestError,
)


class StoreService:
    """Service handling store management operations."""

    @staticmethod
    def list_stores(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> dict:
        """
        List stores in the current tenant with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            search: Search term for name or address
            is_active: Filter by active status

        Returns:
            Dict with stores list and pagination info
        """
        tenant_id = g.tenant.id

        # Base query: stores belonging to this tenant (not soft deleted)
        query = db.session.query(Store).filter(
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        )

        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Store.name.ilike(search_term),
                    Store.address.ilike(search_term)
                )
            )

        if is_active is not None:
            query = query.filter(Store.is_active == is_active)

        # Get total count
        total = query.count()

        # Apply pagination
        query = query.order_by(Store.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        stores = query.all()

        # Calculate total pages
        pages = (total + per_page - 1) // per_page if total > 0 else 1

        return {
            "stores": stores,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    @staticmethod
    def get_store(store_id: UUID) -> dict:
        """
        Get a specific store with user count.

        Args:
            store_id: UUID of the store

        Returns:
            Dict with store data and user count

        Raises:
            StoreNotFoundError: If store not found or not in tenant
        """
        tenant_id = g.tenant.id

        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        # Get user count for this store
        user_count = db.session.query(StoreUser).filter(
            StoreUser.store_id == store_id,
            StoreUser.tenant_id == tenant_id
        ).count()

        return {
            "store": store,
            "user_count": user_count,
        }

    @staticmethod
    def create_store(
        name: str,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Store:
        """
        Create a new store in the current tenant.

        Args:
            name: Store name
            address: Store address (optional)
            phone: Store phone (optional)
            email: Store email (optional)

        Returns:
            Created Store object
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        store = Store(
            tenant_id=tenant_id,
            name=name,
            address=address,
            phone=phone,
            email=email,
            is_active=True,
            created_by=current_user_id,
            updated_by=current_user_id
        )

        db.session.add(store)
        db.session.commit()

        return store

    @staticmethod
    def update_store(
        store_id: UUID,
        name: Optional[str] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Store:
        """
        Update a store's details.

        Args:
            store_id: UUID of the store
            name: New name (optional)
            address: New address (optional)
            phone: New phone (optional)
            email: New email (optional)
            is_active: New active status (optional)

        Returns:
            Updated Store object

        Raises:
            StoreNotFoundError: If store not found or not in tenant
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        if name is not None:
            store.name = name

        # Allow setting to None for optional fields
        if "address" in locals() and address is not None or address is None:
            store.address = address

        if "phone" in locals() and phone is not None or phone is None:
            store.phone = phone

        if "email" in locals() and email is not None or email is None:
            store.email = email

        if is_active is not None:
            store.is_active = is_active

        store.updated_at = datetime.utcnow()
        store.updated_by = current_user_id

        db.session.commit()

        return store

    @staticmethod
    def delete_store(store_id: UUID) -> Store:
        """
        Soft delete a store.

        Args:
            store_id: UUID of the store

        Returns:
            Deleted Store object

        Raises:
            StoreNotFoundError: If store not found or not in tenant
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        store.deleted_at = datetime.utcnow()
        store.is_active = False
        store.updated_at = datetime.utcnow()
        store.updated_by = current_user_id

        db.session.commit()

        return store

    @staticmethod
    def get_store_users(store_id: UUID) -> List[User]:
        """
        Get all users assigned to a store.

        Args:
            store_id: UUID of the store

        Returns:
            List of User objects

        Raises:
            StoreNotFoundError: If store not found or not in tenant
        """
        tenant_id = g.tenant.id

        # Verify store exists
        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        # Get users assigned to this store
        users = db.session.query(User).join(
            StoreUser, StoreUser.user_id == User.id
        ).filter(
            StoreUser.store_id == store_id,
            StoreUser.tenant_id == tenant_id
        ).all()

        return users

    @staticmethod
    def assign_users_to_store(store_id: UUID, user_ids: List[UUID]) -> List[User]:
        """
        Assign users to a store.

        Args:
            store_id: UUID of the store
            user_ids: List of user UUIDs to assign

        Returns:
            List of assigned User objects

        Raises:
            StoreNotFoundError: If store not found
            UserNotFoundError: If any user not found or not in tenant
        """
        tenant_id = g.tenant.id
        current_user_id = g.user.id

        # Verify store exists
        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        assigned_users = []

        for user_id in user_ids:
            # Verify user exists and is member of tenant
            user = db.session.get(User, user_id)
            if not user:
                raise UserNotFoundError(f"User {user_id} not found")

            tenant_user = db.session.query(TenantUser).filter(
                TenantUser.user_id == user_id,
                TenantUser.tenant_id == tenant_id
            ).first()

            if not tenant_user:
                raise UserNotFoundError(f"User {user_id} is not a member of this tenant")

            # Check if already assigned
            existing = db.session.query(StoreUser).filter(
                StoreUser.user_id == user_id,
                StoreUser.store_id == store_id
            ).first()

            if not existing:
                store_user = StoreUser(
                    user_id=user_id,
                    store_id=store_id,
                    tenant_id=tenant_id,
                    assigned_at=datetime.utcnow(),
                    assigned_by=current_user_id
                )
                db.session.add(store_user)

            assigned_users.append(user)

        db.session.commit()

        return assigned_users

    @staticmethod
    def remove_users_from_store(store_id: UUID, user_ids: List[UUID]) -> None:
        """
        Remove users from a store.

        Args:
            store_id: UUID of the store
            user_ids: List of user UUIDs to remove

        Raises:
            StoreNotFoundError: If store not found
        """
        tenant_id = g.tenant.id

        # Verify store exists
        store = db.session.query(Store).filter(
            Store.id == store_id,
            Store.tenant_id == tenant_id,
            Store.deleted_at.is_(None)
        ).first()

        if not store:
            raise StoreNotFoundError()

        # Remove store user assignments
        db.session.query(StoreUser).filter(
            StoreUser.store_id == store_id,
            StoreUser.tenant_id == tenant_id,
            StoreUser.user_id.in_(user_ids)
        ).delete(synchronize_session=False)

        db.session.commit()
