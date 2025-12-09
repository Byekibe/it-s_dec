"""
Authentication service with business logic.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from flask import current_app

from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.core.utils import generate_token_pair, decode_token, get_token_payload, verify_token_type
from app.core.utils import InvalidTokenError as JWTInvalidTokenError, TokenExpiredError as JWTTokenExpiredError
from app.core.exceptions import (
    InvalidCredentialsError,
    DuplicateResourceError,
    TenantNotFoundError,
    TenantAccessDeniedError,
    InvalidTokenError,
    TokenExpiredError,
    BadRequestError,
)


class AuthService:
    """Service handling authentication operations."""

    @staticmethod
    def login(email: str, password: str, tenant_id: UUID) -> dict:
        """
        Authenticate user and return tokens.

        Args:
            email: User's email
            password: User's password
            tenant_id: Tenant UUID to authenticate against

        Returns:
            Dict with tokens, user, and tenant data

        Raises:
            InvalidCredentialsError: If email/password invalid
            TenantNotFoundError: If tenant doesn't exist
            TenantAccessDeniedError: If user not a member of tenant
        """
        # Find user by email
        user = db.session.query(User).filter(
            User.email == email.lower()
        ).first()

        if not user or not user.check_password(password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")

        # Verify tenant exists
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant or tenant.is_deleted:
            raise TenantNotFoundError()

        # Verify user is member of tenant
        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == tenant.id
        ).first()

        if not tenant_user:
            raise TenantAccessDeniedError()

        # Generate tokens
        tokens = generate_token_pair(user.id, tenant.id)

        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
            "tenant": tenant,
        }

    @staticmethod
    def register(
        email: str,
        password: str,
        full_name: str,
        tenant_name: str,
        tenant_slug: str
    ) -> dict:
        """
        Register a new user with a new tenant.

        Args:
            email: User's email
            password: User's password
            full_name: User's full name
            tenant_name: Name for the new tenant
            tenant_slug: URL slug for the tenant

        Returns:
            Dict with tokens, user, and tenant data

        Raises:
            DuplicateResourceError: If email or tenant slug already exists
        """
        email = email.lower()

        # Check if email already exists
        existing_user = db.session.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            raise DuplicateResourceError("Email already registered")

        # Check if tenant slug already exists
        existing_tenant = db.session.query(Tenant).filter(
            Tenant.slug == tenant_slug.lower()
        ).first()

        if existing_tenant:
            raise DuplicateResourceError("Tenant slug already taken")

        # Create user
        user = User(
            email=email,
            full_name=full_name,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id

        # Create tenant
        tenant = Tenant(
            name=tenant_name,
            slug=tenant_slug.lower(),
            status=TenantStatus.TRIAL
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant.id

        # Create tenant membership
        tenant_user = TenantUser(
            user_id=user.id,
            tenant_id=tenant.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user)

        db.session.commit()

        # Generate tokens
        tokens = generate_token_pair(user.id, tenant.id)

        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
            "tenant": tenant,
        }

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new tokens

        Raises:
            TokenExpiredError: If refresh token expired
            InvalidTokenError: If refresh token invalid
        """
        try:
            payload = verify_token_type(refresh_token, "refresh")
        except JWTTokenExpiredError:
            raise TokenExpiredError("Refresh token has expired")
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            raise InvalidTokenError("Token missing required claims")

        # Verify user and tenant still exist and are valid
        user = db.session.get(User, UUID(user_id))
        if not user or not user.is_active:
            raise InvalidTokenError("User no longer valid")

        tenant = db.session.get(Tenant, UUID(tenant_id))
        if not tenant or tenant.is_deleted:
            raise InvalidTokenError("Tenant no longer valid")

        # Verify membership still exists
        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == tenant.id
        ).first()

        if not tenant_user:
            raise InvalidTokenError("User no longer member of tenant")

        # Generate new tokens
        tokens = generate_token_pair(user.id, tenant.id)

        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
        }

    @staticmethod
    def bootstrap(
        email: str,
        password: str,
        full_name: str,
        tenant_name: str,
        tenant_slug: str
    ) -> dict:
        """
        Bootstrap the first user and tenant.

        This should only work when no users exist in the system.

        Args:
            email: Admin user's email
            password: Admin user's password
            full_name: Admin user's full name
            tenant_name: Name for the first tenant
            tenant_slug: URL slug for the tenant

        Returns:
            Dict with tokens, user, and tenant data

        Raises:
            BadRequestError: If system already has users
            DuplicateResourceError: If email or slug exists
        """
        # Check if any users exist
        user_count = db.session.query(User).count()
        if user_count > 0:
            raise BadRequestError("System already bootstrapped")

        # Use register logic (same flow)
        return AuthService.register(
            email=email,
            password=password,
            full_name=full_name,
            tenant_name=tenant_name,
            tenant_slug=tenant_slug
        )
