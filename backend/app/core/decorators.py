"""
Route decorators for authentication and authorization.

These decorators provide protection for API endpoints:
- @jwt_required: Ensures valid JWT token (redundant with middleware, but explicit)
- @require_tenant: Ensures tenant context exists
- @require_store: Ensures store context exists (X-Store-ID header)
- @require_permission: Checks user has specific permission
"""

from functools import wraps
from typing import Union, List

from flask import g

from app.extensions import db
from app.core.exceptions import (
    UnauthorizedError,
    ForbiddenError,
    InsufficientPermissionsError,
)


def jwt_required(f):
    """
    Decorator that ensures the request has a valid JWT token.

    Since TenantMiddleware already handles JWT validation and sets g.user,
    this decorator mainly serves as explicit documentation that an endpoint
    requires authentication.

    Raises:
        UnauthorizedError: If no authenticated user in context
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or g.user is None:
            raise UnauthorizedError()
        return f(*args, **kwargs)
    return decorated_function


def require_tenant(f):
    """
    Decorator that ensures tenant context exists.

    Raises:
        UnauthorizedError: If no authenticated user
        ForbiddenError: If no tenant context
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or g.user is None:
            raise UnauthorizedError()
        if not hasattr(g, 'tenant') or g.tenant is None:
            raise ForbiddenError("Tenant context required")
        return f(*args, **kwargs)
    return decorated_function


def require_store(f):
    """
    Decorator that ensures store context exists (X-Store-ID header provided).

    Raises:
        UnauthorizedError: If no authenticated user
        ForbiddenError: If no store context
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or g.user is None:
            raise UnauthorizedError()
        if not hasattr(g, 'store') or g.store is None:
            raise ForbiddenError("Store context required. Provide X-Store-ID header.")
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission: Union[str, List[str]], require_all: bool = False):
    """
    Decorator factory that checks if user has required permission(s).

    Permissions are checked against the user's roles within the current tenant.
    If a store context exists, store-specific roles are also considered.

    Args:
        permission: Permission name (e.g., "products.create") or list of permissions
        require_all: If True, user must have ALL permissions. If False (default),
                    user needs at least ONE of the permissions.

    Usage:
        @require_permission("products.create")
        def create_product():
            ...

        @require_permission(["products.create", "products.edit"])
        def manage_product():
            ...

        @require_permission(["admin.access", "products.delete"], require_all=True)
        def admin_delete():
            ...

    Raises:
        UnauthorizedError: If no authenticated user
        InsufficientPermissionsError: If user lacks required permission(s)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or g.user is None:
                raise UnauthorizedError()

            if not hasattr(g, 'tenant') or g.tenant is None:
                raise ForbiddenError("Tenant context required")

            # Normalize to list
            permissions = [permission] if isinstance(permission, str) else permission

            # Get user's permissions
            user_permissions = get_user_permissions(
                user_id=g.user.id,
                tenant_id=g.tenant.id,
                store_id=g.store.id if hasattr(g, 'store') and g.store else None
            )

            if require_all:
                # User must have ALL permissions
                missing = [p for p in permissions if p not in user_permissions]
                if missing:
                    raise InsufficientPermissionsError(
                        f"Missing required permissions: {', '.join(missing)}"
                    )
            else:
                # User needs at least ONE permission
                if not any(p in user_permissions for p in permissions):
                    raise InsufficientPermissionsError(
                        required_permission=permissions[0] if len(permissions) == 1 else None
                    )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions(user_id, tenant_id, store_id=None) -> set:
    """
    Get all permission names for a user within a tenant (and optionally store).

    Collects permissions from:
    1. Tenant-wide roles (store_id is NULL)
    2. Store-specific roles (if store_id provided)

    Args:
        user_id: User UUID
        tenant_id: Tenant UUID
        store_id: Optional store UUID

    Returns:
        Set of permission names the user has
    """
    from app.blueprints.rbac.models import UserRole, RolePermission, Permission

    # Build query for user's roles in this tenant
    # Include tenant-wide roles (store_id is NULL)
    role_query = db.session.query(UserRole.role_id).filter(
        UserRole.user_id == user_id,
        UserRole.tenant_id == tenant_id,
        UserRole.store_id.is_(None)
    )

    # If store context exists, also include store-specific roles
    if store_id:
        store_role_query = db.session.query(UserRole.role_id).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            UserRole.store_id == store_id
        )
        role_query = role_query.union(store_role_query)

    # Get all role IDs
    role_ids = [r[0] for r in role_query.all()]

    if not role_ids:
        return set()

    # Get permissions for these roles
    permissions = db.session.query(Permission.name).join(
        RolePermission, RolePermission.permission_id == Permission.id
    ).filter(
        RolePermission.role_id.in_(role_ids)
    ).all()

    return {p[0] for p in permissions}


def has_permission(permission: str) -> bool:
    """
    Check if current user has a specific permission.

    Utility function for checking permissions in business logic.

    Args:
        permission: Permission name to check

    Returns:
        True if user has the permission, False otherwise
    """
    if not hasattr(g, 'user') or g.user is None:
        return False
    if not hasattr(g, 'tenant') or g.tenant is None:
        return False

    user_permissions = get_user_permissions(
        user_id=g.user.id,
        tenant_id=g.tenant.id,
        store_id=g.store.id if hasattr(g, 'store') and g.store else None
    )

    return permission in user_permissions


def has_any_permission(permissions: List[str]) -> bool:
    """
    Check if current user has any of the specified permissions.

    Args:
        permissions: List of permission names

    Returns:
        True if user has at least one permission, False otherwise
    """
    if not hasattr(g, 'user') or g.user is None:
        return False
    if not hasattr(g, 'tenant') or g.tenant is None:
        return False

    user_permissions = get_user_permissions(
        user_id=g.user.id,
        tenant_id=g.tenant.id,
        store_id=g.store.id if hasattr(g, 'store') and g.store else None
    )

    return any(p in user_permissions for p in permissions)


def require_subscription_active(f):
    """
    Decorator that ensures the tenant has an active subscription.

    Raises:
        ForbiddenError: If subscription is not active
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant') or g.tenant is None:
            raise ForbiddenError("Tenant context required")

        from app.blueprints.subscriptions.services import SubscriptionService
        SubscriptionService.check_subscription_active()

        return f(*args, **kwargs)
    return decorated_function


def require_can_add_user(f):
    """
    Decorator that checks if tenant can add more users based on plan limits.

    Use this decorator on user creation/invitation endpoints.

    Raises:
        ForbiddenError: If user limit reached
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant') or g.tenant is None:
            raise ForbiddenError("Tenant context required")

        from app.blueprints.subscriptions.services import SubscriptionService
        SubscriptionService.check_can_add_user()

        return f(*args, **kwargs)
    return decorated_function


def require_can_add_store(f):
    """
    Decorator that checks if tenant can add more stores based on plan limits.

    Use this decorator on store creation endpoints.

    Raises:
        ForbiddenError: If store limit reached
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant') or g.tenant is None:
            raise ForbiddenError("Tenant context required")

        from app.blueprints.subscriptions.services import SubscriptionService
        SubscriptionService.check_can_add_store()

        return f(*args, **kwargs)
    return decorated_function
