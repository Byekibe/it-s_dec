"""
Security middleware for multi-tenant access control.

This module implements the two-layer security middleware:
1. TenantMiddleware - Validates JWT and sets tenant context
2. StoreMiddleware - Validates store access when X-Store-ID header is present
"""

from functools import wraps
from typing import Optional, List
from uuid import UUID

from flask import g, request
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.extensions import db
from app.core.utils import decode_token, JWTError, TokenExpiredError as JWTTokenExpiredError, InvalidTokenError as JWTInvalidTokenError
from app.core.exceptions import (
    UnauthorizedError,
    TokenExpiredError,
    InvalidTokenError,
    TenantAccessDeniedError,
    StoreAccessDeniedError,
    TenantNotFoundError,
    StoreNotFoundError,
    UserNotFoundError,
    UserInactiveError,
    TenantSuspendedError,
)


def get_token_from_header() -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Expected format: "Bearer <token>"

    Returns:
        Token string if present and valid format, None otherwise
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def load_user_and_tenant(user_id: str, tenant_id: str):
    """
    Load user and tenant from database and validate membership.

    Args:
        user_id: User UUID string from token
        tenant_id: Tenant UUID string from token

    Returns:
        Tuple of (user, tenant, tenant_user)

    Raises:
        UserNotFoundError: If user doesn't exist
        UserInactiveError: If user is inactive
        TenantNotFoundError: If tenant doesn't exist
        TenantSuspendedError: If tenant is suspended
        TenantAccessDeniedError: If user is not a member of the tenant
    """
    # Import models here to avoid circular imports
    from app.blueprints.users.models import User
    from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus

    # Load user
    user = db.session.get(User, UUID(user_id))
    if not user:
        raise UserNotFoundError()

    if not user.is_active:
        raise UserInactiveError()

    # Load tenant
    tenant = db.session.get(Tenant, UUID(tenant_id))
    if not tenant:
        raise TenantNotFoundError()

    if tenant.is_deleted:
        raise TenantNotFoundError("Tenant has been deleted")

    if tenant.status == TenantStatus.SUSPENDED:
        raise TenantSuspendedError()

    # Verify user is a member of the tenant
    tenant_user = db.session.query(TenantUser).filter(
        TenantUser.user_id == user.id,
        TenantUser.tenant_id == tenant.id
    ).first()

    if not tenant_user:
        raise TenantAccessDeniedError()

    return user, tenant, tenant_user


def load_store(store_id: str, tenant_id: UUID, user_id: UUID):
    """
    Load store and validate user access.

    Args:
        store_id: Store UUID string from header
        tenant_id: Current tenant UUID
        user_id: Current user UUID

    Returns:
        Store object

    Raises:
        StoreNotFoundError: If store doesn't exist or doesn't belong to tenant
        StoreAccessDeniedError: If user doesn't have access to the store
    """
    from app.blueprints.stores.models import Store, StoreUser

    try:
        store_uuid = UUID(store_id)
    except ValueError:
        raise StoreNotFoundError("Invalid store ID format")

    # Load store and verify it belongs to the tenant
    store = db.session.query(Store).filter(
        Store.id == store_uuid,
        Store.tenant_id == tenant_id,
        Store.deleted_at.is_(None)
    ).first()

    if not store:
        raise StoreNotFoundError()

    if not store.is_active:
        raise StoreNotFoundError("Store is inactive")

    # Verify user has access to this store
    store_user = db.session.query(StoreUser).filter(
        StoreUser.user_id == user_id,
        StoreUser.store_id == store_uuid,
        StoreUser.tenant_id == tenant_id
    ).first()

    if not store_user:
        raise StoreAccessDeniedError()

    return store


class TenantMiddleware:
    """
    First security checkpoint - validates JWT and establishes tenant context.

    This middleware:
    1. Extracts JWT from Authorization header
    2. Validates the token
    3. Loads user and tenant from database
    4. Validates user is active and member of the tenant
    5. Sets g.user and g.tenant for request context
    """

    # Paths that don't require authentication
    EXEMPT_PATHS: List[str] = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/bootstrap",
    ]

    # Path prefixes that don't require authentication
    EXEMPT_PREFIXES: List[str] = [
        "/static/",
        "/health",  # Health check endpoints
    ]

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Register middleware with Flask app."""
        app.before_request(self.before_request)

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        # Check exact matches
        if path in self.EXEMPT_PATHS:
            return True

        # Check prefixes
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    def before_request(self):
        """
        Process request before route handler.

        Sets g.user, g.tenant, and g.tenant_user if authenticated.
        """
        # Initialize context variables
        g.user = None
        g.tenant = None
        g.tenant_user = None
        g.store = None

        # Skip authentication for exempt paths
        if self.is_exempt(request.path):
            return None

        # Extract token
        token = get_token_from_header()
        if not token:
            raise UnauthorizedError("Missing authorization header")

        # Decode and validate token
        try:
            payload = decode_token(token)
        except JWTTokenExpiredError:
            raise TokenExpiredError()
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        # Validate token type
        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        # Extract required claims
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            raise InvalidTokenError("Token missing required claims")

        # Load and validate user/tenant
        user, tenant, tenant_user = load_user_and_tenant(user_id, tenant_id)

        # Set request context
        g.user = user
        g.tenant = tenant
        g.tenant_user = tenant_user

        return None


class StoreMiddleware:
    """
    Second security checkpoint - validates store access when X-Store-ID header is present.

    This middleware:
    1. Checks for X-Store-ID header
    2. Validates store exists and belongs to current tenant
    3. Validates user has access to the store
    4. Sets g.store for request context
    """

    STORE_HEADER = "X-Store-ID"

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Register middleware with Flask app."""
        app.before_request(self.before_request)

    def before_request(self):
        """
        Process request before route handler.

        Sets g.store if X-Store-ID header is present and valid.
        """
        # Skip if no tenant context (exempt route or not authenticated)
        if not hasattr(g, 'tenant') or g.tenant is None:
            return None

        # Check for store header
        store_id = request.headers.get(self.STORE_HEADER)
        if not store_id:
            return None

        # Load and validate store access
        store = load_store(store_id, g.tenant.id, g.user.id)
        g.store = store

        return None


def setup_tenant_query_filter():
    """
    Set up SQLAlchemy event listener for automatic tenant filtering.

    This hooks into SQLAlchemy's query execution to automatically
    add tenant_id filter to all queries on tenant-scoped models.
    """
    from app.core.models import TenantScopedModel

    @event.listens_for(Session, "do_orm_execute")
    def add_tenant_filter(execute_state):
        """
        Automatically filter queries by tenant_id.

        Only applies when:
        1. g.tenant exists (authenticated request)
        2. Query is a SELECT statement
        3. Model inherits from TenantScopedModel
        """
        # Only filter SELECT queries
        if not execute_state.is_select:
            return

        # Check if we have a tenant context
        if not hasattr(g, 'tenant') or g.tenant is None:
            return

        # Get the mapper entities being queried
        # This is a simplified implementation - may need enhancement for complex queries
        try:
            for mapper_entity in execute_state.bind_mapper.iterate_to_root():
                model_class = mapper_entity.class_

                # Check if this is a tenant-scoped model
                if isinstance(model_class, type) and issubclass(model_class, TenantScopedModel):
                    # Add tenant filter using query options
                    execute_state.statement = execute_state.statement.filter(
                        model_class.tenant_id == g.tenant.id
                    )
        except AttributeError:
            # No mapper or not a model query
            pass


def register_error_handlers(app):
    """
    Register error handlers for API exceptions.

    Converts exceptions to JSON responses with appropriate status codes.
    """
    from app.core.exceptions import APIError

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle all APIError subclasses."""
        from flask import jsonify
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors."""
        from flask import jsonify
        return jsonify({
            "error": "not_found",
            "message": "The requested resource was not found"
        }), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors."""
        from flask import jsonify
        return jsonify({
            "error": "internal_error",
            "message": "An internal server error occurred"
        }), 500


def init_middleware(app):
    """
    Initialize all middleware and error handlers.

    Call this function from create_app() to set up security.
    """
    # Register error handlers first
    register_error_handlers(app)

    # Initialize middleware (order matters!)
    TenantMiddleware(app)
    StoreMiddleware(app)

    # Set up query filter (do this within app context)
    with app.app_context():
        setup_tenant_query_filter()
