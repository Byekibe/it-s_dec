"""
User management routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.users.services import UserService
from app.blueprints.users.schemas import (
    UserResponseSchema,
    UserDetailResponseSchema,
    UpdateCurrentUserSchema,
    CreateUserSchema,
    UpdateUserSchema,
    UserListResponseSchema,
    UserListQuerySchema,
    InviteUserSchema,
    InvitationResponseSchema,
    UserTenantListResponseSchema,
)
from app.core.decorators import jwt_required, require_permission, require_can_add_user
from app.core.constants import Permissions
from app.core.exceptions import ValidationError as AppValidationError

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user():
    """
    Get current authenticated user's profile.

    Returns:
        User profile with roles and store assignments
    """
    result = UserService.get_current_user_details()

    response_schema = UserDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["user"].id,
        "email": result["user"].email,
        "full_name": result["user"].full_name,
        "is_active": result["user"].is_active,
        "created_at": result["user"].created_at,
        "updated_at": result["user"].updated_at,
        "roles": result["roles"],
        "stores": result["stores"],
    })), 200


@users_bp.route("/me", methods=["PUT"])
@jwt_required
def update_current_user():
    """
    Update current authenticated user's profile.

    Request body:
        full_name: New full name (optional)
        current_password: Current password (required if changing password)
        new_password: New password (optional)

    Returns:
        Updated user profile
    """
    schema = UpdateCurrentUserSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    user = UserService.update_current_user(
        full_name=data.get("full_name"),
        current_password=data.get("current_password"),
        new_password=data.get("new_password")
    )

    response_schema = UserResponseSchema()
    return jsonify(response_schema.dump(user)), 200


@users_bp.route("", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def list_users():
    """
    List users in the current tenant.

    Query parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        search: Search term for email or name
        is_active: Filter by active status (true/false)
        store_id: Filter by store assignment

    Returns:
        Paginated list of users
    """
    query_schema = UserListQuerySchema()

    try:
        # Parse query parameters
        query_params = {
            "page": request.args.get("page", type=int),
            "per_page": request.args.get("per_page", type=int),
            "search": request.args.get("search"),
            "is_active": request.args.get("is_active"),
            "store_id": request.args.get("store_id"),
        }
        # Remove None values to use schema defaults
        query_params = {k: v for k, v in query_params.items() if v is not None}

        # Handle boolean conversion for is_active
        if "is_active" in query_params:
            query_params["is_active"] = query_params["is_active"].lower() in ("true", "1", "yes")

        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.list_users(
        page=data["page"],
        per_page=data["per_page"],
        search=data.get("search"),
        is_active=data.get("is_active"),
        store_id=data.get("store_id")
    )

    response_schema = UserListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@users_bp.route("/<uuid:user_id>", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def get_user(user_id):
    """
    Get a specific user's details.

    Path parameters:
        user_id: UUID of the user

    Returns:
        User profile with roles and store assignments
    """
    result = UserService.get_user(user_id)

    response_schema = UserDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["user"].id,
        "email": result["user"].email,
        "full_name": result["user"].full_name,
        "is_active": result["user"].is_active,
        "created_at": result["user"].created_at,
        "updated_at": result["user"].updated_at,
        "roles": result["roles"],
        "stores": result["stores"],
    })), 200


@users_bp.route("", methods=["POST"])
@require_permission(Permissions.USERS_CREATE)
@require_can_add_user
def create_user():
    """
    Create/invite a new user to the tenant.

    Request body:
        email: User's email (required)
        full_name: User's full name (required)
        password: User's password (optional)
        role_ids: List of role UUIDs to assign (optional)
        store_ids: List of store UUIDs to assign (optional)

    Returns:
        Created user profile with roles and stores
    """
    schema = CreateUserSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.create_user(
        email=data["email"],
        full_name=data["full_name"],
        password=data.get("password"),
        role_ids=data.get("role_ids", []),
        store_ids=data.get("store_ids", [])
    )

    response_schema = UserDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["user"].id,
        "email": result["user"].email,
        "full_name": result["user"].full_name,
        "is_active": result["user"].is_active,
        "created_at": result["user"].created_at,
        "updated_at": result["user"].updated_at,
        "roles": result["roles"],
        "stores": result["stores"],
    })), 201


@users_bp.route("/<uuid:user_id>", methods=["PUT"])
@require_permission(Permissions.USERS_EDIT)
def update_user(user_id):
    """
    Update a user's details (admin operation).

    Path parameters:
        user_id: UUID of the user

    Request body:
        full_name: New full name (optional)
        is_active: New active status (optional)
        role_ids: New list of role UUIDs (optional, replaces existing)
        store_ids: New list of store UUIDs (optional, replaces existing)

    Returns:
        Updated user profile with roles and stores
    """
    schema = UpdateUserSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.update_user(
        user_id=user_id,
        full_name=data.get("full_name"),
        is_active=data.get("is_active"),
        role_ids=data.get("role_ids"),
        store_ids=data.get("store_ids")
    )

    response_schema = UserDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["user"].id,
        "email": result["user"].email,
        "full_name": result["user"].full_name,
        "is_active": result["user"].is_active,
        "created_at": result["user"].created_at,
        "updated_at": result["user"].updated_at,
        "roles": result["roles"],
        "stores": result["stores"],
    })), 200


@users_bp.route("/<uuid:user_id>", methods=["DELETE"])
@require_permission(Permissions.USERS_DELETE)
def deactivate_user(user_id):
    """
    Deactivate a user (soft delete).

    Path parameters:
        user_id: UUID of the user

    Returns:
        Deactivated user profile
    """
    user = UserService.deactivate_user(user_id)

    response_schema = UserResponseSchema()
    return jsonify(response_schema.dump(user)), 200


@users_bp.route("/invite", methods=["POST"])
@require_permission(Permissions.USERS_CREATE)
@require_can_add_user
def invite_user():
    """
    Invite a user to join the tenant.

    Request body:
        email: Email address to invite (required)
        role_id: UUID of role to assign on acceptance (optional)

    Returns:
        Invitation details with expiration
    """
    schema = InviteUserSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.invite_user(
        email=data["email"],
        role_id=data.get("role_id")
    )

    response_schema = InvitationResponseSchema()
    return jsonify(response_schema.dump(result)), 201


@users_bp.route("/me/tenants", methods=["GET"])
@jwt_required
def list_user_tenants():
    """
    List all tenants the current user belongs to.

    Returns a list of tenants with an `is_current` flag indicating
    which tenant is currently active.

    Returns:
        List of tenants with membership details
    """
    tenants = UserService.list_user_tenants()

    response_schema = UserTenantListResponseSchema()
    return jsonify(response_schema.dump({"tenants": tenants})), 200
