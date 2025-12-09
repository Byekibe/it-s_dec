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
