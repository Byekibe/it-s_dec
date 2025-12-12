"""
Tenant service with business logic for tenant management.
"""

from datetime import datetime
from typing import Optional

from flask import g

from app.extensions import db
from app.blueprints.tenants.models import Tenant, TenantUser, TenantSettings
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

    @staticmethod
    def get_settings() -> TenantSettings:
        """
        Get settings for the current tenant.
        Creates default settings if none exist.

        Returns:
            TenantSettings object
        """
        tenant = g.tenant

        settings = db.session.query(TenantSettings).filter(
            TenantSettings.tenant_id == tenant.id
        ).first()

        if not settings:
            # Create default settings
            settings = TenantSettings(tenant_id=tenant.id)
            db.session.add(settings)
            db.session.commit()
            db.session.refresh(settings)

        return settings

    @staticmethod
    def update_settings(
        timezone: Optional[str] = None,
        currency: Optional[str] = None,
        locale: Optional[str] = None,
        date_format: Optional[str] = None,
        time_format: Optional[str] = None,
        tax_rate: Optional[float] = None,
        tax_inclusive_pricing: Optional[bool] = None,
        tax_id: Optional[str] = None,
        fiscal_year_start_month: Optional[int] = None,
        fiscal_year_start_day: Optional[int] = None,
        business_name: Optional[str] = None,
        business_address: Optional[str] = None,
        business_phone: Optional[str] = None,
        business_email: Optional[str] = None,
    ) -> TenantSettings:
        """
        Update settings for the current tenant.

        Args:
            All settings fields are optional

        Returns:
            Updated TenantSettings object
        """
        # Get or create settings
        settings = TenantService.get_settings()

        # Update fields if provided
        if timezone is not None:
            settings.timezone = timezone
        if currency is not None:
            settings.currency = currency.upper()
        if locale is not None:
            settings.locale = locale
        if date_format is not None:
            settings.date_format = date_format
        if time_format is not None:
            settings.time_format = time_format
        if tax_rate is not None:
            settings.tax_rate = tax_rate
        if tax_inclusive_pricing is not None:
            settings.tax_inclusive_pricing = tax_inclusive_pricing
        if tax_id is not None:
            settings.tax_id = tax_id
        if fiscal_year_start_month is not None:
            settings.fiscal_year_start_month = fiscal_year_start_month
        if fiscal_year_start_day is not None:
            settings.fiscal_year_start_day = fiscal_year_start_day
        if business_name is not None:
            settings.business_name = business_name
        if business_address is not None:
            settings.business_address = business_address
        if business_phone is not None:
            settings.business_phone = business_phone
        if business_email is not None:
            settings.business_email = business_email

        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return settings
