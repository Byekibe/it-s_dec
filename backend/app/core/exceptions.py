"""
Custom exceptions for the application.

These exceptions are used throughout the application and are handled
by Flask error handlers to return appropriate HTTP responses.
"""

from typing import Optional


class APIError(Exception):
    """
    Base exception for all API errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code for clients
    """
    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "message": self.message,
        }


# Authentication Errors (401)

class UnauthorizedError(APIError):
    """Raised when authentication is required but not provided or invalid."""
    status_code = 401
    error_code = "unauthorized"

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message)


class InvalidCredentialsError(APIError):
    """Raised when login credentials are invalid."""
    status_code = 401
    error_code = "invalid_credentials"

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)


class TokenExpiredError(APIError):
    """Raised when a JWT token has expired."""
    status_code = 401
    error_code = "token_expired"

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class InvalidTokenError(APIError):
    """Raised when a JWT token is invalid or malformed."""
    status_code = 401
    error_code = "invalid_token"

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


# Authorization Errors (403)

class ForbiddenError(APIError):
    """Raised when user is authenticated but not authorized for the action."""
    status_code = 403
    error_code = "forbidden"

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message)


class TenantAccessDeniedError(APIError):
    """Raised when user attempts to access a tenant they don't belong to."""
    status_code = 403
    error_code = "tenant_access_denied"

    def __init__(self, message: str = "You do not have access to this tenant"):
        super().__init__(message)


class StoreAccessDeniedError(APIError):
    """Raised when user attempts to access a store they don't have access to."""
    status_code = 403
    error_code = "store_access_denied"

    def __init__(self, message: str = "You do not have access to this store"):
        super().__init__(message)


class InsufficientPermissionsError(APIError):
    """Raised when user lacks required permissions for an action."""
    status_code = 403
    error_code = "insufficient_permissions"

    def __init__(self, message: str = "Insufficient permissions", required_permission: Optional[str] = None):
        if required_permission:
            message = f"Missing required permission: {required_permission}"
        super().__init__(message)
        self.required_permission = required_permission


# Not Found Errors (404)

class NotFoundError(APIError):
    """Base class for resource not found errors."""
    status_code = 404
    error_code = "not_found"

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found."""
    error_code = "user_not_found"

    def __init__(self, message: str = "User not found"):
        super().__init__(message)


class TenantNotFoundError(NotFoundError):
    """Raised when a tenant cannot be found."""
    error_code = "tenant_not_found"

    def __init__(self, message: str = "Tenant not found"):
        super().__init__(message)


class StoreNotFoundError(NotFoundError):
    """Raised when a store cannot be found."""
    error_code = "store_not_found"

    def __init__(self, message: str = "Store not found"):
        super().__init__(message)


class RoleNotFoundError(NotFoundError):
    """Raised when a role cannot be found."""
    error_code = "role_not_found"

    def __init__(self, message: str = "Role not found"):
        super().__init__(message)


# Validation Errors (400)

class ValidationError(APIError):
    """Raised when request data fails validation."""
    status_code = 400
    error_code = "validation_error"

    def __init__(self, message: str = "Validation failed", errors: Optional[dict] = None):
        super().__init__(message)
        self.errors = errors or {}

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.errors:
            result["errors"] = self.errors
        return result


class BadRequestError(APIError):
    """Raised for general bad request errors."""
    status_code = 400
    error_code = "bad_request"

    def __init__(self, message: str = "Bad request"):
        super().__init__(message)


# Conflict Errors (409)

class ConflictError(APIError):
    """Raised when an action conflicts with current state."""
    status_code = 409
    error_code = "conflict"

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message)


class DuplicateResourceError(ConflictError):
    """Raised when attempting to create a resource that already exists."""
    error_code = "duplicate_resource"

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


# Business Logic Errors

class TenantSuspendedError(APIError):
    """Raised when attempting actions on a suspended tenant."""
    status_code = 403
    error_code = "tenant_suspended"

    def __init__(self, message: str = "Tenant account is suspended"):
        super().__init__(message)


class UserInactiveError(APIError):
    """Raised when an inactive user attempts to perform actions."""
    status_code = 403
    error_code = "user_inactive"

    def __init__(self, message: str = "User account is inactive"):
        super().__init__(message)
