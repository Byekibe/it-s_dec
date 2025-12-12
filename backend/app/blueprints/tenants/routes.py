"""
Tenant management routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.tenants.services import TenantService
from app.blueprints.tenants.schemas import (
    TenantResponseSchema,
    TenantDetailResponseSchema,
    UpdateTenantSchema,
    TenantSettingsResponseSchema,
    UpdateTenantSettingsSchema,
)
from app.core.decorators import require_permission
from app.core.constants import Permissions
from app.core.exceptions import ValidationError as AppValidationError

tenants_bp = Blueprint("tenants", __name__, url_prefix="/tenants")


@tenants_bp.route("/current", methods=["GET"])
@require_permission(Permissions.TENANTS_VIEW)
def get_current_tenant():
    """
    Get current tenant's details.

    Returns:
        Tenant profile with user and store counts
    """
    result = TenantService.get_current_tenant_details()

    response_schema = TenantDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["tenant"].id,
        "name": result["tenant"].name,
        "slug": result["tenant"].slug,
        "status": result["tenant"].status,
        "trial_ends_at": result["tenant"].trial_ends_at,
        "created_at": result["tenant"].created_at,
        "updated_at": result["tenant"].updated_at,
        "user_count": result["user_count"],
        "store_count": result["store_count"],
    })), 200


@tenants_bp.route("/current", methods=["PUT"])
@require_permission(Permissions.TENANTS_EDIT)
def update_current_tenant():
    """
    Update current tenant's settings.

    Request body:
        name: New tenant name (optional)
        slug: New tenant slug (optional)

    Returns:
        Updated tenant profile
    """
    schema = UpdateTenantSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    tenant = TenantService.update_current_tenant(
        name=data.get("name"),
        slug=data.get("slug")
    )

    response_schema = TenantResponseSchema()
    return jsonify(response_schema.dump(tenant)), 200


@tenants_bp.route("/current/settings", methods=["GET"])
@require_permission(Permissions.TENANTS_VIEW)
def get_tenant_settings():
    """
    Get current tenant's settings.

    Returns:
        Tenant settings (regional, tax, business info)
    """
    settings = TenantService.get_settings()

    response_schema = TenantSettingsResponseSchema()
    return jsonify(response_schema.dump(settings.to_dict())), 200


@tenants_bp.route("/current/settings", methods=["PUT"])
@require_permission(Permissions.TENANTS_EDIT)
def update_tenant_settings():
    """
    Update current tenant's settings.

    Request body:
        timezone: Timezone string (e.g., 'Africa/Nairobi')
        currency: 3-letter currency code (e.g., 'KES')
        locale: Locale string (e.g., 'en-KE')
        date_format: Date format ('DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD')
        time_format: Time format ('12h', '24h')
        tax_rate: Tax rate percentage (0-100)
        tax_inclusive_pricing: Whether prices include tax
        tax_id: KRA PIN or tax ID
        fiscal_year_start_month: Month (1-12)
        fiscal_year_start_day: Day (1-31)
        business_name: Business name for receipts
        business_address: Business address
        business_phone: Business phone
        business_email: Business email

    Returns:
        Updated tenant settings
    """
    schema = UpdateTenantSettingsSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    settings = TenantService.update_settings(
        timezone=data.get("timezone"),
        currency=data.get("currency"),
        locale=data.get("locale"),
        date_format=data.get("date_format"),
        time_format=data.get("time_format"),
        tax_rate=data.get("tax_rate"),
        tax_inclusive_pricing=data.get("tax_inclusive_pricing"),
        tax_id=data.get("tax_id"),
        fiscal_year_start_month=data.get("fiscal_year_start_month"),
        fiscal_year_start_day=data.get("fiscal_year_start_day"),
        business_name=data.get("business_name"),
        business_address=data.get("business_address"),
        business_phone=data.get("business_phone"),
        business_email=data.get("business_email"),
    )

    response_schema = TenantSettingsResponseSchema()
    return jsonify(response_schema.dump(settings.to_dict())), 200
