"""
Authentication routes.
"""

from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from app.blueprints.auth.services import AuthService
from app.blueprints.auth.schemas import (
    LoginSchema,
    RegisterSchema,
    BootstrapSchema,
    RefreshTokenSchema,
    AuthResponseSchema,
    TokenResponseSchema,
    MessageResponseSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    VerifyEmailSchema,
    AcceptInviteSchema,
    SwitchTenantSchema,
)
from app.core.exceptions import ValidationError as AppValidationError
from app.core.decorators import jwt_required
from app.core.middleware import get_token_from_header

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


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    """
    Logout and invalidate the current access token.

    Requires authentication. The current token will be blacklisted
    and cannot be used again.

    Returns:
        Success message
    """
    token = get_token_from_header()
    result = AuthService.logout(token=token)

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/logout-all", methods=["POST"])
@jwt_required
def logout_all():
    """
    Logout from all sessions.

    Requires authentication. All tokens issued before this point
    will be invalidated for the current user.

    Returns:
        Success message
    """
    result = AuthService.logout_all(user_id=g.user.id)

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Request a password reset email.

    Request body:
        email: User's email address

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    schema = ForgotPasswordSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.forgot_password(email=data["email"])

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Reset password using a valid reset token.

    Request body:
        token: Password reset token from email
        password: New password (min 8 chars)

    Returns:
        Success message
    """
    schema = ResetPasswordSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.reset_password(
        token=data["token"],
        new_password=data["password"]
    )

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """
    Verify email using a verification token.

    Request body:
        token: Email verification token from email

    Returns:
        Success message
    """
    schema = VerifyEmailSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.verify_email(token=data["token"])

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/resend-verification", methods=["POST"])
@jwt_required
def resend_verification():
    """
    Resend verification email to the current user.

    Requires authentication. Only sends if email is not yet verified.

    Returns:
        Success message
    """
    result = AuthService.resend_verification(user_id=g.user.id)

    response_schema = MessageResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@auth_bp.route("/accept-invite", methods=["POST"])
def accept_invite():
    """
    Accept an invitation and join a tenant.

    Request body:
        token: Invitation token from email
        full_name: User's full name
        password: User's password (min 8 chars)

    Returns:
        access_token, refresh_token, user, tenant
    """
    schema = AcceptInviteSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.accept_invite(
        token=data["token"],
        full_name=data["full_name"],
        password=data["password"]
    )

    response_schema = AuthResponseSchema()
    return jsonify(response_schema.dump(result)), 201


@auth_bp.route("/switch-tenant", methods=["POST"])
@jwt_required
def switch_tenant():
    """
    Switch to a different tenant.

    Requires authentication. User must be a member of the target tenant.

    Request body:
        tenant_id: UUID of the tenant to switch to

    Returns:
        access_token, refresh_token, user, tenant
    """
    schema = SwitchTenantSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.switch_tenant(
        user_id=g.user.id,
        target_tenant_id=data["tenant_id"]
    )

    response_schema = AuthResponseSchema()
    return jsonify(response_schema.dump(result)), 200
