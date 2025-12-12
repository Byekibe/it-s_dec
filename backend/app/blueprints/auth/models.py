"""
Authentication models for token management.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class BlacklistedToken(db.Model):
    """
    Model for tracking blacklisted/invalidated JWT tokens.

    Used for:
    - Logout (invalidate current token)
    - Logout all sessions (invalidate all user tokens)
    - Token revocation on security events

    Tokens are stored by their JTI (JWT ID) claim for efficient lookup.
    Expired blacklisted tokens can be periodically cleaned up.
    """
    __tablename__ = 'blacklisted_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String(36), nullable=False, unique=True, index=True)  # JWT ID
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    expires_at = Column(DateTime, nullable=False)  # When the original token expires
    blacklisted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reason = Column(String(50), nullable=True)  # 'logout', 'logout_all', 'security', etc.

    # Index for efficient cleanup of expired tokens
    __table_args__ = (
        Index('ix_blacklisted_tokens_expires_at', 'expires_at'),
        Index('ix_blacklisted_tokens_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<BlacklistedToken {self.jti}>'

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        return db.session.query(
            db.session.query(cls).filter(cls.jti == jti).exists()
        ).scalar()

    @classmethod
    def blacklist_token(
        cls,
        jti: str,
        user_id: uuid.UUID,
        token_type: str,
        expires_at: datetime,
        reason: str = None
    ) -> 'BlacklistedToken':
        """Add a token to the blacklist."""
        blacklisted = cls(
            jti=jti,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
            reason=reason
        )
        db.session.add(blacklisted)
        return blacklisted

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Remove expired blacklisted tokens from the database.

        Returns the number of deleted records.
        """
        result = db.session.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        return result


class UserTokenRevocation(db.Model):
    """
    Model for tracking user-wide token revocations.

    Used for 'logout all' functionality - instead of blacklisting every token,
    we store a timestamp. Any token issued before this timestamp is considered invalid.
    """
    __tablename__ = 'user_token_revocations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    revoked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserTokenRevocation user_id={self.user_id}>'

    @classmethod
    def get_revocation_time(cls, user_id: uuid.UUID) -> datetime | None:
        """Get the revocation timestamp for a user, if any."""
        record = db.session.query(cls).filter(cls.user_id == user_id).first()
        return record.revoked_at if record else None

    @classmethod
    def revoke_all_tokens(cls, user_id: uuid.UUID) -> 'UserTokenRevocation':
        """
        Revoke all tokens for a user by setting/updating the revocation timestamp.

        Any token with an 'iat' before this timestamp will be considered invalid.
        """
        record = db.session.query(cls).filter(cls.user_id == user_id).first()

        if record:
            record.revoked_at = datetime.utcnow()
        else:
            record = cls(user_id=user_id)
            db.session.add(record)

        return record


class PasswordResetToken(db.Model):
    """
    Model for password reset tokens.

    Tokens are single-use and expire after 1 hour.
    """
    __tablename__ = 'password_reset_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)  # Set when token is used
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_password_reset_tokens_user_id', 'user_id'),
        Index('ix_password_reset_tokens_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id}>'

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_used(self):
        """Mark the token as used."""
        self.used_at = datetime.utcnow()

    @classmethod
    def create_token(cls, user_id: uuid.UUID, expires_in_hours: int = 1) -> 'PasswordResetToken':
        """
        Create a new password reset token for a user.

        Args:
            user_id: The user's UUID
            expires_in_hours: Hours until token expires (default 1)

        Returns:
            PasswordResetToken instance
        """
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(48)  # 64 characters
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        reset_token = cls(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.session.add(reset_token)
        return reset_token

    @classmethod
    def get_valid_token(cls, token: str) -> 'PasswordResetToken | None':
        """
        Get a valid (not expired, not used) token by its value.

        Args:
            token: The token string

        Returns:
            PasswordResetToken if valid, None otherwise
        """
        reset_token = db.session.query(cls).filter(
            cls.token == token
        ).first()

        if reset_token and reset_token.is_valid:
            return reset_token
        return None

    @classmethod
    def invalidate_user_tokens(cls, user_id: uuid.UUID) -> int:
        """
        Invalidate all unused tokens for a user.

        Called when a new reset request is made to prevent multiple valid tokens.

        Returns:
            Number of tokens invalidated
        """
        result = db.session.query(cls).filter(
            cls.user_id == user_id,
            cls.used_at.is_(None)
        ).update({'used_at': datetime.utcnow()})
        return result

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Remove expired tokens from the database.

        Returns:
            Number of deleted records
        """
        result = db.session.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        return result


class UserInvitation(db.Model):
    """
    Model for user invitations to join a tenant.

    Tokens expire after 7 days and are single-use.
    """
    __tablename__ = 'user_invitations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)  # Email of the invitee
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=True)  # Optional role to assign
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)  # Set when invitation is accepted
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_user_invitations_email', 'email'),
        Index('ix_user_invitations_tenant_id', 'tenant_id'),
        Index('ix_user_invitations_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f'<UserInvitation email={self.email} tenant_id={self.tenant_id}>'

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if the invitation has been accepted."""
        return self.accepted_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is valid (not expired and not accepted)."""
        return not self.is_expired and not self.is_accepted

    def mark_accepted(self):
        """Mark the invitation as accepted."""
        self.accepted_at = datetime.utcnow()

    @classmethod
    def create_invitation(
        cls,
        email: str,
        tenant_id: uuid.UUID,
        invited_by: uuid.UUID,
        role_id: uuid.UUID = None,
        expires_in_days: int = 7
    ) -> 'UserInvitation':
        """
        Create a new invitation.

        Args:
            email: Invitee's email address
            tenant_id: Tenant UUID
            invited_by: User UUID of the inviter
            role_id: Optional role UUID to assign on acceptance
            expires_in_days: Days until invitation expires (default 7)

        Returns:
            UserInvitation instance
        """
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(48)  # 64 characters
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        invitation = cls(
            token=token,
            email=email.lower(),
            tenant_id=tenant_id,
            role_id=role_id,
            invited_by=invited_by,
            expires_at=expires_at
        )
        db.session.add(invitation)
        return invitation

    @classmethod
    def get_valid_invitation(cls, token: str) -> 'UserInvitation | None':
        """
        Get a valid (not expired, not accepted) invitation by its token.

        Args:
            token: The invitation token

        Returns:
            UserInvitation if valid, None otherwise
        """
        invitation = db.session.query(cls).filter(
            cls.token == token
        ).first()

        if invitation and invitation.is_valid:
            return invitation
        return None

    @classmethod
    def get_pending_invitation(cls, email: str, tenant_id: uuid.UUID) -> 'UserInvitation | None':
        """
        Get a pending invitation for an email/tenant combination.

        Args:
            email: Invitee's email
            tenant_id: Tenant UUID

        Returns:
            UserInvitation if exists and valid, None otherwise
        """
        invitation = db.session.query(cls).filter(
            cls.email == email.lower(),
            cls.tenant_id == tenant_id,
            cls.accepted_at.is_(None),
            cls.expires_at > datetime.utcnow()
        ).first()

        return invitation

    @classmethod
    def invalidate_pending_invitations(cls, email: str, tenant_id: uuid.UUID) -> int:
        """
        Invalidate all pending invitations for an email/tenant.

        Called when a new invitation is sent to prevent multiple valid invitations.

        Returns:
            Number of invitations invalidated
        """
        result = db.session.query(cls).filter(
            cls.email == email.lower(),
            cls.tenant_id == tenant_id,
            cls.accepted_at.is_(None)
        ).update({'accepted_at': datetime.utcnow()})
        return result

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Remove expired invitations from the database.

        Returns:
            Number of deleted records
        """
        result = db.session.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        return result


class EmailVerificationToken(db.Model):
    """
    Model for email verification tokens.

    Tokens are single-use and expire after 24 hours.
    """
    __tablename__ = 'email_verification_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)  # Set when token is used
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_email_verification_tokens_user_id', 'user_id'),
        Index('ix_email_verification_tokens_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f'<EmailVerificationToken user_id={self.user_id}>'

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_used(self):
        """Mark the token as used."""
        self.used_at = datetime.utcnow()

    @classmethod
    def create_token(cls, user_id: uuid.UUID, expires_in_hours: int = 24) -> 'EmailVerificationToken':
        """
        Create a new email verification token for a user.

        Args:
            user_id: The user's UUID
            expires_in_hours: Hours until token expires (default 24)

        Returns:
            EmailVerificationToken instance
        """
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(48)  # 64 characters
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        verification_token = cls(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.session.add(verification_token)
        return verification_token

    @classmethod
    def get_valid_token(cls, token: str) -> 'EmailVerificationToken | None':
        """
        Get a valid (not expired, not used) token by its value.

        Args:
            token: The token string

        Returns:
            EmailVerificationToken if valid, None otherwise
        """
        verification_token = db.session.query(cls).filter(
            cls.token == token
        ).first()

        if verification_token and verification_token.is_valid:
            return verification_token
        return None

    @classmethod
    def invalidate_user_tokens(cls, user_id: uuid.UUID) -> int:
        """
        Invalidate all unused tokens for a user.

        Called when a new verification request is made to prevent multiple valid tokens.

        Returns:
            Number of tokens invalidated
        """
        result = db.session.query(cls).filter(
            cls.user_id == user_id,
            cls.used_at.is_(None)
        ).update({'used_at': datetime.utcnow()})
        return result

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Remove expired tokens from the database.

        Returns:
            Number of deleted records
        """
        result = db.session.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        return result
