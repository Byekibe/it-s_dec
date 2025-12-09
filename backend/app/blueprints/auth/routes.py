"""
Authentication routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.auth.services import AuthService
from app.blueprints.auth.schemas import (
    LoginSchema,
    RegisterSchema,
    BootstrapSchema,
    RefreshTokenSchema,
    AuthResponseSchema,
    TokenResponseSchema,
)
from app.core.exceptions import ValidationError as AppValidationError

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return tokens.

    Request body:
        email: User's email
        password: User's password
        tenant_id: UUID of tenant to authenticate against

    Returns:
        access_token, refresh_token, user, tenant
    """
    schema = LoginSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.login(
        email=data["email"],
        password=data["password"],
        tenant_id=data["tenant_id"]
    )

    response_schema = AuthResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register new user with new tenant.

    Request body:
        email: User's email
        password: User's password (min 8 chars)
        full_name: User's full name
        tenant_name: Name for the new tenant
        tenant_slug: URL-safe slug for tenant

    Returns:
        access_token, refresh_token, user, tenant
    """
    schema = RegisterSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.register(
        email=data["email"],
        password=data["password"],
        full_name=data["full_name"],
        tenant_name=data["tenant_name"],
        tenant_slug=data["tenant_slug"]
    )

    response_schema = AuthResponseSchema()
    return jsonify(response_schema.dump(result)), 201


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh access token using refresh token.

    Request body:
        refresh_token: Valid refresh token

    Returns:
        access_token, refresh_token
    """
    schema = RefreshTokenSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.refresh_token(refresh_token=data["refresh_token"])

    response_schema = TokenResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/bootstrap", methods=["POST"])
def bootstrap():
    """
    Bootstrap the first user and tenant.

    This endpoint only works when no users exist in the system.
    Use it to create the initial admin user and tenant.

    Request body:
        email: Admin user's email
        password: Admin user's password (min 8 chars)
        full_name: Admin user's full name
        tenant_name: Name for the first tenant
        tenant_slug: URL-safe slug for tenant

    Returns:
        access_token, refresh_token, user, tenant
    """
    schema = BootstrapSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.bootstrap(
        email=data["email"],
        password=data["password"],
        full_name=data["full_name"],
        tenant_name=data["tenant_name"],
        tenant_slug=data["tenant_slug"]
    )

    response_schema = AuthResponseSchema()
    return jsonify(response_schema.dump(result)), 201
