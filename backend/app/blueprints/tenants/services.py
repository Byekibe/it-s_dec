"""
Tenant service with business logic for tenant management.
"""

from datetime import datetime
from typing import Optional

from flask import g

from app.extensions import db
from app.blueprints.tenants.models import Tenant, TenantUser
from app.blueprints.stores.models import Store
from app.core.exceptions import DuplicateResourceError


class TenantService:
    """Service handling tenant management operations."""

    @staticmethod
    def get_current_tenant() -> Tenant:
        """
        Get the current tenant from request context.

        Returns:
            Tenant object from request context
        """
        return g.tenant

    @staticmethod
    def get_current_tenant_details() -> dict:
        """
        Get current tenant with additional stats.

        Returns:
            Dict with tenant data and stats
        """
        tenant = g.tenant

        # Get user count
        user_count = db.session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant.id
        ).count()

        # Get store count (active stores only)
        store_count = db.session.query(Store).filter(
            Store.tenant_id == tenant.id,
            Store.is_active == True,
            Store.deleted_at.is_(None)
        ).count()

        return {
            "tenant": tenant,
            "user_count": user_count,
            "store_count": store_count,
        }

    @staticmethod
    def update_current_tenant(
        name: Optional[str] = None,
        slug: Optional[str] = None
    ) -> Tenant:
        """
        Update current tenant's settings.

        Args:
            name: New tenant name (optional)
            slug: New tenant slug (optional)

        Returns:
            Updated Tenant object

        Raises:
            DuplicateResourceError: If slug already exists
        """
        tenant = g.tenant

        if name is not None:
            tenant.name = name

        if slug is not None:
            slug = slug.lower()
            # Check if slug is already taken by another tenant
            existing = db.session.query(Tenant).filter(
                Tenant.slug == slug,
                Tenant.id != tenant.id
            ).first()

            if existing:
                raise DuplicateResourceError("Tenant slug already taken")

            tenant.slug = slug

        tenant.updated_at = datetime.utcnow()
        db.session.commit()

        return tenant
