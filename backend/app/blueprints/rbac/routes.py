"""
RBAC management routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.rbac.services import RBACService
from app.blueprints.rbac.schemas import (
    RoleResponseSchema,
    RoleDetailResponseSchema,
    RoleListResponseSchema,
    CreateRoleSchema,
    UpdateRoleSchema,
    PermissionResponseSchema,
    PermissionListResponseSchema,
    AssignRoleSchema,
    UserRolesResponseSchema,
)
from app.core.decorators import require_permission
from app.core.constants import Permissions
from app.core.exceptions import ValidationError as AppValidationError

rbac_bp = Blueprint("rbac", __name__)


# ==================== Roles ====================

@rbac_bp.route("/roles", methods=["GET"])
@require_permission(Permissions.ROLES_VIEW)
def list_roles():
    """
    List all roles in the current tenant.

    Returns:
        List of roles with total count
    """
    result = RBACService.list_roles()

    response_schema = RoleListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@rbac_bp.route("/roles/<uuid:role_id>", methods=["GET"])
@require_permission(Permissions.ROLES_VIEW)
def get_role(role_id):
    """
    Get a specific role with its permissions.

    Path parameters:
        role_id: UUID of the role

    Returns:
        Role details with permissions and user count
    """
    result = RBACService.get_role(role_id)

    response_schema = RoleDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["role"].id,
        "name": result["role"].name,
        "description": result["role"].description,
        "is_system_role": result["role"].is_system_role,
        "created_at": result["role"].created_at,
        "updated_at": result["role"].updated_at,
        "permissions": result["permissions"],
        "user_count": result["user_count"],
    })), 200


@rbac_bp.route("/roles", methods=["POST"])
@require_permission(Permissions.ROLES_CREATE)
def create_role():
    """
    Create a new custom role.

    Request body:
        name: Role name (required)
        description: Role description (optional)
        permission_ids: List of permission UUIDs (optional)

    Returns:
        Created role with permissions
    """
    schema = CreateRoleSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.create_role(
        name=data["name"],
        description=data.get("description"),
        permission_ids=data.get("permission_ids", [])
    )

    response_schema = RoleDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["role"].id,
        "name": result["role"].name,
        "description": result["role"].description,
        "is_system_role": result["role"].is_system_role,
        "created_at": result["role"].created_at,
        "updated_at": result["role"].updated_at,
        "permissions": result["permissions"],
        "user_count": result["user_count"],
    })), 201


@rbac_bp.route("/roles/<uuid:role_id>", methods=["PUT"])
@require_permission(Permissions.ROLES_EDIT)
def update_role(role_id):
    """
    Update a role's details and permissions.

    Path parameters:
        role_id: UUID of the role

    Request body:
        name: New name (optional)
        description: New description (optional)
        permission_ids: New list of permission UUIDs (optional, replaces existing)

    Returns:
        Updated role with permissions
    """
    schema = UpdateRoleSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.update_role(
        role_id=role_id,
        name=data.get("name"),
        description=data.get("description"),
        permission_ids=data.get("permission_ids")
    )

    response_schema = RoleDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["role"].id,
        "name": result["role"].name,
        "description": result["role"].description,
        "is_system_role": result["role"].is_system_role,
        "created_at": result["role"].created_at,
        "updated_at": result["role"].updated_at,
        "permissions": result["permissions"],
        "user_count": result["user_count"],
    })), 200


@rbac_bp.route("/roles/<uuid:role_id>", methods=["DELETE"])
@require_permission(Permissions.ROLES_DELETE)
def delete_role(role_id):
    """
    Delete a custom role.

    Path parameters:
        role_id: UUID of the role

    Returns:
        Deleted role details
    """
    role = RBACService.delete_role(role_id)

    response_schema = RoleResponseSchema()
    return jsonify(response_schema.dump(role)), 200


# ==================== Permissions ====================

@rbac_bp.route("/permissions", methods=["GET"])
@require_permission(Permissions.PERMISSIONS_VIEW)
def list_permissions():
    """
    List all available permissions.

    Query parameters:
        resource: Filter by resource name (optional)

    Returns:
        List of permissions
    """
    resource = request.args.get("resource")
    result = RBACService.list_permissions(resource=resource)

    response_schema = PermissionListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


# ==================== User Role Assignments ====================

@rbac_bp.route("/users/<uuid:user_id>/roles", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def get_user_roles(user_id):
    """
    Get all role assignments for a user.

    Path parameters:
        user_id: UUID of the user

    Returns:
        User's role assignments
    """
    result = RBACService.get_user_roles(user_id)

    response_schema = UserRolesResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@rbac_bp.route("/users/<uuid:user_id>/roles", methods=["POST"])
@require_permission(Permissions.USERS_MANAGE_ROLES)
def assign_role_to_user(user_id):
    """
    Assign a role to a user.

    Path parameters:
        user_id: UUID of the user

    Request body:
        role_id: UUID of the role to assign (required)
        store_id: UUID of store for store-specific assignment (optional)

    Returns:
        Updated user role assignments
    """
    schema = AssignRoleSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.assign_role_to_user(
        user_id=user_id,
        role_id=data["role_id"],
        store_id=data.get("store_id")
    )

    response_schema = UserRolesResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@rbac_bp.route("/users/<uuid:user_id>/roles/<uuid:role_id>", methods=["DELETE"])
@require_permission(Permissions.USERS_MANAGE_ROLES)
def revoke_role_from_user(user_id, role_id):
    """
    Revoke a role from a user.

    Path parameters:
        user_id: UUID of the user
        role_id: UUID of the role to revoke

    Query parameters:
        store_id: UUID of store for store-specific revocation (optional)

    Returns:
        Updated user role assignments
    """
    store_id = request.args.get("store_id")

    result = RBACService.revoke_role_from_user(
        user_id=user_id,
        role_id=role_id,
        store_id=store_id
    )

    response_schema = UserRolesResponseSchema()
    return jsonify(response_schema.dump(result)), 200
