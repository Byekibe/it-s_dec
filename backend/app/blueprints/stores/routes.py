"""
Store management routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.stores.services import StoreService
from app.blueprints.stores.schemas import (
    StoreResponseSchema,
    StoreDetailResponseSchema,
    CreateStoreSchema,
    UpdateStoreSchema,
    StoreListResponseSchema,
    StoreListQuerySchema,
    StoreUserAssignmentSchema,
)
from app.blueprints.users.schemas import UserResponseSchema
from app.core.decorators import require_permission
from app.core.constants import Permissions
from app.core.exceptions import ValidationError as AppValidationError

stores_bp = Blueprint("stores", __name__, url_prefix="/stores")


@stores_bp.route("", methods=["GET"])
@require_permission(Permissions.STORES_VIEW)
def list_stores():
    """
    List stores in the current tenant.

    Query parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        search: Search term for name or address
        is_active: Filter by active status (true/false)

    Returns:
        Paginated list of stores
    """
    query_schema = StoreListQuerySchema()

    try:
        query_params = {
            "page": request.args.get("page", type=int),
            "per_page": request.args.get("per_page", type=int),
            "search": request.args.get("search"),
            "is_active": request.args.get("is_active"),
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}

        if "is_active" in query_params:
            query_params["is_active"] = query_params["is_active"].lower() in ("true", "1", "yes")

        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = StoreService.list_stores(
        page=data["page"],
        per_page=data["per_page"],
        search=data.get("search"),
        is_active=data.get("is_active")
    )

    response_schema = StoreListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@stores_bp.route("/<uuid:store_id>", methods=["GET"])
@require_permission(Permissions.STORES_VIEW)
def get_store(store_id):
    """
    Get a specific store's details.

    Path parameters:
        store_id: UUID of the store

    Returns:
        Store details with user count
    """
    result = StoreService.get_store(store_id)

    response_schema = StoreDetailResponseSchema()
    return jsonify(response_schema.dump({
        "id": result["store"].id,
        "name": result["store"].name,
        "address": result["store"].address,
        "phone": result["store"].phone,
        "email": result["store"].email,
        "is_active": result["store"].is_active,
        "created_at": result["store"].created_at,
        "updated_at": result["store"].updated_at,
        "user_count": result["user_count"],
    })), 200


@stores_bp.route("", methods=["POST"])
@require_permission(Permissions.STORES_CREATE)
def create_store():
    """
    Create a new store.

    Request body:
        name: Store name (required)
        address: Store address (optional)
        phone: Store phone (optional)
        email: Store email (optional)

    Returns:
        Created store details
    """
    schema = CreateStoreSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    store = StoreService.create_store(
        name=data["name"],
        address=data.get("address"),
        phone=data.get("phone"),
        email=data.get("email")
    )

    response_schema = StoreResponseSchema()
    return jsonify(response_schema.dump(store)), 201


@stores_bp.route("/<uuid:store_id>", methods=["PUT"])
@require_permission(Permissions.STORES_EDIT)
def update_store(store_id):
    """
    Update a store's details.

    Path parameters:
        store_id: UUID of the store

    Request body:
        name: New name (optional)
        address: New address (optional)
        phone: New phone (optional)
        email: New email (optional)
        is_active: New active status (optional)

    Returns:
        Updated store details
    """
    schema = UpdateStoreSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    store = StoreService.update_store(
        store_id=store_id,
        name=data.get("name"),
        address=data.get("address"),
        phone=data.get("phone"),
        email=data.get("email"),
        is_active=data.get("is_active")
    )

    response_schema = StoreResponseSchema()
    return jsonify(response_schema.dump(store)), 200


@stores_bp.route("/<uuid:store_id>", methods=["DELETE"])
@require_permission(Permissions.STORES_DELETE)
def delete_store(store_id):
    """
    Soft delete a store.

    Path parameters:
        store_id: UUID of the store

    Returns:
        Deleted store details
    """
    store = StoreService.delete_store(store_id)

    response_schema = StoreResponseSchema()
    return jsonify(response_schema.dump(store)), 200


@stores_bp.route("/<uuid:store_id>/users", methods=["GET"])
@require_permission(Permissions.STORES_VIEW)
def get_store_users(store_id):
    """
    Get users assigned to a store.

    Path parameters:
        store_id: UUID of the store

    Returns:
        List of users assigned to the store
    """
    users = StoreService.get_store_users(store_id)

    response_schema = UserResponseSchema(many=True)
    return jsonify({"users": response_schema.dump(users)}), 200


@stores_bp.route("/<uuid:store_id>/users", methods=["POST"])
@require_permission(Permissions.STORES_MANAGE_USERS)
def assign_users_to_store(store_id):
    """
    Assign users to a store.

    Path parameters:
        store_id: UUID of the store

    Request body:
        user_ids: List of user UUIDs to assign

    Returns:
        List of assigned users
    """
    schema = StoreUserAssignmentSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    users = StoreService.assign_users_to_store(
        store_id=store_id,
        user_ids=data["user_ids"]
    )

    response_schema = UserResponseSchema(many=True)
    return jsonify({"users": response_schema.dump(users)}), 200


@stores_bp.route("/<uuid:store_id>/users", methods=["DELETE"])
@require_permission(Permissions.STORES_MANAGE_USERS)
def remove_users_from_store(store_id):
    """
    Remove users from a store.

    Path parameters:
        store_id: UUID of the store

    Request body:
        user_ids: List of user UUIDs to remove

    Returns:
        Success message
    """
    schema = StoreUserAssignmentSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    StoreService.remove_users_from_store(
        store_id=store_id,
        user_ids=data["user_ids"]
    )

    return jsonify({"message": "Users removed from store"}), 200
