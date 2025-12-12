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
from app.blueprints.rbac.models import Role, UserRole, Permission, RolePermission
from app.core.constants import DEFAULT_ROLES, ALL_PERMISSIONS
from app.core.utils import generate_token_pair, decode_token, get_token_payload, verify_token_type
from app.core.utils import InvalidTokenError as JWTInvalidTokenError, TokenExpiredError as JWTTokenExpiredError
from app.blueprints.auth.models import BlacklistedToken, UserTokenRevocation, PasswordResetToken, EmailVerificationToken, UserInvitation
from app.core.exceptions import (
    InvalidCredentialsError,
    DuplicateResourceError,
    TenantNotFoundError,
    TenantAccessDeniedError,
    InvalidTokenError,
    TokenExpiredError,
    BadRequestError,
    UserNotFoundError,
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
    def _seed_tenant_roles(tenant: Tenant, user: User):
        """Seeds a new tenant with default roles and assigns Owner role."""
        # Get all permissions from DB, map by name for quick lookup
        all_permissions_list = db.session.query(Permission).all()
        permissions_map = {p.name: p for p in all_permissions_list}

        owner_role = None

        for role_name, role_def in DEFAULT_ROLES.items():
            # Create the role for the tenant
            new_role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_def["description"],
                is_system_role=role_def["is_system_role"],
            )
            db.session.add(new_role)
            db.session.flush()

            # Assign permissions to the role
            for perm_name in role_def["permissions"]:
                perm_obj = permissions_map.get(perm_name)
                if perm_obj:
                    role_perm = RolePermission(
                        role_id=new_role.id,
                        permission_id=perm_obj.id,
                    )
                    db.session.add(role_perm)
            
            if role_name == "Owner":
                owner_role = new_role

        # Assign the 'Owner' role to the user who created the tenant
        if owner_role:
            user_role = UserRole(
                user_id=user.id,
                role_id=owner_role.id,
                tenant_id=tenant.id,
                assigned_by=user.id,  # Self-assigned
            )
            db.session.add(user_role)

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

        # Seed the new tenant with default roles and assign Owner
        AuthService._seed_tenant_roles(tenant, user)

        # Create subscription for the tenant (free plan with trial)
        from app.blueprints.subscriptions.services import SubscriptionService
        SubscriptionService.create_subscription(
            tenant_id=tenant.id,
            plan_slug="free",
            start_trial=True
        )

        # Create email verification token
        verification_token = EmailVerificationToken.create_token(user.id)

        db.session.commit()

        # Send verification email asynchronously
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        verify_url = f"{frontend_url}/verify-email?token={verification_token.token}"

        try:
            from app.core.tasks import send_verification_email_task
            send_verification_email_task.delay(
                to=user.email,
                verify_url=verify_url
            )
        except Exception:
            # If Celery is not available, send synchronously
            from app.core.email import send_email_verification
            send_email_verification(to=user.email, verify_url=verify_url)

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

    @staticmethod
    def logout(token: str) -> dict:
        """
        Logout by blacklisting the current access token.

        Args:
            token: The current access token to invalidate

        Returns:
            Dict with success message

        Raises:
            InvalidTokenError: If token is invalid
        """
        from datetime import datetime, timezone

        try:
            payload = get_token_payload(token)
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        jti = payload.get("jti")
        user_id = payload.get("user_id")
        token_type = payload.get("type", "access")
        exp = payload.get("exp")

        if not jti:
            # Token doesn't have jti claim (old token), can't blacklist
            # Just return success - token will expire naturally
            return {"message": "Logged out successfully"}

        if not user_id:
            raise InvalidTokenError("Token missing user_id claim")

        # Convert exp timestamp to datetime
        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        else:
            expires_at = exp or datetime.now(timezone.utc)

        # Blacklist the token
        BlacklistedToken.blacklist_token(
            jti=jti,
            user_id=UUID(user_id),
            token_type=token_type,
            expires_at=expires_at,
            reason="logout"
        )
        db.session.commit()

        return {"message": "Logged out successfully"}

    @staticmethod
    def logout_all(user_id: UUID) -> dict:
        """
        Logout from all sessions by revoking all tokens for the user.

        This sets a revocation timestamp - any token issued before this
        timestamp will be considered invalid.

        Args:
            user_id: The user's UUID

        Returns:
            Dict with success message
        """
        UserTokenRevocation.revoke_all_tokens(user_id)
        db.session.commit()

        return {"message": "All sessions have been logged out"}

    @staticmethod
    def forgot_password(email: str) -> dict:
        """
        Initiate password reset flow by generating a reset token and queuing email.

        For security, always returns success even if email doesn't exist.
        This prevents email enumeration attacks.

        Args:
            email: User's email address

        Returns:
            Dict with success message
        """
        email = email.lower()

        # Find user by email
        user = db.session.query(User).filter(
            User.email == email
        ).first()

        if user and user.is_active:
            # Invalidate any existing reset tokens for this user
            PasswordResetToken.invalidate_user_tokens(user.id)

            # Create new reset token
            reset_token = PasswordResetToken.create_token(user.id)
            db.session.commit()

            # Build reset URL
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?token={reset_token.token}"

            # Queue email sending task
            try:
                from app.core.tasks import send_password_reset_email_task
                send_password_reset_email_task.delay(
                    to=user.email,
                    reset_url=reset_url
                )
            except Exception:
                # If Celery is not available, send synchronously
                from app.core.email import send_password_reset_email
                send_password_reset_email(to=user.email, reset_url=reset_url)

        # Always return success to prevent email enumeration
        return {
            "message": "If an account with that email exists, a password reset link has been sent."
        }

    @staticmethod
    def reset_password(token: str, new_password: str) -> dict:
        """
        Reset user's password using a valid reset token.

        Args:
            token: The password reset token
            new_password: The new password to set

        Returns:
            Dict with success message

        Raises:
            InvalidTokenError: If token is invalid, expired, or already used
        """
        # Find and validate the token
        reset_token = PasswordResetToken.get_valid_token(token)

        if not reset_token:
            raise InvalidTokenError("Invalid or expired password reset token")

        # Get the user
        user = db.session.get(User, reset_token.user_id)

        if not user or not user.is_active:
            raise InvalidTokenError("Invalid or expired password reset token")

        # Update password
        user.set_password(new_password)

        # Mark token as used
        reset_token.mark_used()

        # Optionally revoke all existing sessions for security
        UserTokenRevocation.revoke_all_tokens(user.id)

        db.session.commit()

        return {"message": "Password has been reset successfully"}

    @staticmethod
    def send_verification_email(user_id: UUID) -> dict:
        """
        Generate a verification token and send verification email.

        Args:
            user_id: The user's UUID

        Returns:
            Dict with success message

        Raises:
            UserNotFoundError: If user doesn't exist
            BadRequestError: If email is already verified
        """
        user = db.session.get(User, user_id)

        if not user:
            raise UserNotFoundError()

        if user.email_verified:
            raise BadRequestError("Email is already verified")

        # Invalidate any existing verification tokens for this user
        EmailVerificationToken.invalidate_user_tokens(user.id)

        # Create new verification token
        verification_token = EmailVerificationToken.create_token(user.id)
        db.session.commit()

        # Build verification URL
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        verify_url = f"{frontend_url}/verify-email?token={verification_token.token}"

        # Queue email sending task
        try:
            from app.core.tasks import send_verification_email_task
            send_verification_email_task.delay(
                to=user.email,
                verify_url=verify_url
            )
        except Exception:
            # If Celery is not available, send synchronously
            from app.core.email import send_email_verification
            send_email_verification(to=user.email, verify_url=verify_url)

        return {"message": "Verification email sent"}

    @staticmethod
    def verify_email(token: str) -> dict:
        """
        Verify user's email using a valid verification token.

        Args:
            token: The email verification token

        Returns:
            Dict with success message

        Raises:
            InvalidTokenError: If token is invalid, expired, or already used
        """
        # Find and validate the token
        verification_token = EmailVerificationToken.get_valid_token(token)

        if not verification_token:
            raise InvalidTokenError("Invalid or expired verification token")

        # Get the user
        user = db.session.get(User, verification_token.user_id)

        if not user:
            raise InvalidTokenError("Invalid or expired verification token")

        if user.email_verified:
            # Already verified, just mark token as used and return success
            verification_token.mark_used()
            db.session.commit()
            return {"message": "Email already verified"}

        # Mark user as verified
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()

        # Mark token as used
        verification_token.mark_used()

        db.session.commit()

        return {"message": "Email verified successfully"}

    @staticmethod
    def resend_verification(user_id: UUID) -> dict:
        """
        Resend verification email to the current user.

        Args:
            user_id: The user's UUID

        Returns:
            Dict with success message

        Raises:
            UserNotFoundError: If user doesn't exist
            BadRequestError: If email is already verified
        """
        return AuthService.send_verification_email(user_id)

    @staticmethod
    def accept_invite(token: str, full_name: str, password: str) -> dict:
        """
        Accept an invitation and create/join account.

        If the user already exists (has an account), they are added to the tenant.
        If not, a new user is created.

        Args:
            token: The invitation token
            full_name: User's full name
            password: User's password

        Returns:
            Dict with tokens, user, and tenant data

        Raises:
            InvalidTokenError: If token is invalid, expired, or already accepted
            DuplicateResourceError: If user is already a member of the tenant
        """
        # Find and validate the invitation
        invitation = UserInvitation.get_valid_invitation(token)

        if not invitation:
            raise InvalidTokenError("Invalid or expired invitation")

        email = invitation.email
        tenant_id = invitation.tenant_id

        # Check if user already exists
        existing_user = db.session.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            # Check if already a member of this tenant
            existing_membership = db.session.query(TenantUser).filter(
                TenantUser.user_id == existing_user.id,
                TenantUser.tenant_id == tenant_id
            ).first()

            if existing_membership:
                raise DuplicateResourceError("You are already a member of this organization")

            user = existing_user
            # Update password if provided (they may want to use a different password for this tenant)
            user.set_password(password)
            if full_name:
                user.full_name = full_name
        else:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                is_active=True,
                email_verified=True,  # Email is verified because they received the invite
                email_verified_at=datetime.utcnow()
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

        # Get tenant
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise InvalidTokenError("Invalid or expired invitation")

        # Add user to tenant
        tenant_user = TenantUser(
            user_id=user.id,
            tenant_id=tenant_id,
            joined_at=datetime.utcnow(),
            invited_by=invitation.invited_by
        )
        db.session.add(tenant_user)

        # Assign role if specified in invitation
        if invitation.role_id:
            role = db.session.get(Role, invitation.role_id)
            if role and role.tenant_id == tenant_id:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=invitation.role_id,
                    tenant_id=tenant_id,
                    store_id=None,
                    assigned_at=datetime.utcnow(),
                    assigned_by=invitation.invited_by
                )
                db.session.add(user_role)

        # Mark invitation as accepted
        invitation.mark_accepted()

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
    def switch_tenant(user_id: UUID, target_tenant_id: UUID) -> dict:
        """
        Switch to a different tenant and generate new tokens.

        Args:
            user_id: The current user's UUID
            target_tenant_id: The tenant UUID to switch to

        Returns:
            Dict with new tokens, user, and tenant data

        Raises:
            TenantNotFoundError: If target tenant doesn't exist
            TenantAccessDeniedError: If user is not a member of target tenant
        """
        # Verify user exists and is active
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            raise TenantAccessDeniedError("User account is inactive")

        # Verify target tenant exists
        tenant = db.session.get(Tenant, target_tenant_id)
        if not tenant or tenant.is_deleted:
            raise TenantNotFoundError()

        # Check tenant status
        if tenant.status == TenantStatus.SUSPENDED:
            raise TenantAccessDeniedError("This organization is suspended")

        if tenant.status == TenantStatus.CANCELED:
            raise TenantAccessDeniedError("This organization has been canceled")

        # Verify user is a member of target tenant
        tenant_user = db.session.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == target_tenant_id
        ).first()

        if not tenant_user:
            raise TenantAccessDeniedError("You are not a member of this organization")

        # Generate new tokens for the target tenant
        tokens = generate_token_pair(user.id, tenant.id)

        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
            "tenant": tenant,
        }
