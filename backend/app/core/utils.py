"""
JWT Utilities for token generation and validation.

Uses PyJWT for encoding/decoding JWT tokens with support for
access tokens and refresh tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import jwt
from flask import current_app


class JWTError(Exception):
    """Base exception for JWT-related errors."""
    pass


class TokenExpiredError(JWTError):
    """Raised when a token has expired."""
    pass


class InvalidTokenError(JWTError):
    """Raised when a token is invalid or malformed."""
    pass


def generate_access_token(user_id: UUID, tenant_id: UUID, extra_claims: Optional[dict] = None) -> str:
    """
    Generate a JWT access token.

    Args:
        user_id: The user's UUID
        tenant_id: The tenant's UUID
        extra_claims: Optional additional claims to include in the token

    Returns:
        Encoded JWT access token string
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"])

    payload = {
        "jti": str(uuid4()),  # Unique token ID for blacklisting
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def generate_refresh_token(user_id: UUID, tenant_id: UUID) -> str:
    """
    Generate a JWT refresh token.

    Refresh tokens have a longer expiration and are used to obtain new access tokens.

    Args:
        user_id: The user's UUID
        tenant_id: The tenant's UUID

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(seconds=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])

    payload = {
        "jti": str(uuid4()),  # Unique token ID for blacklisting
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary containing the token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid or malformed
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def get_token_payload(token: str) -> dict:
    """
    Extract payload from token without full validation.

    Useful for getting claims from an expired token (e.g., for refresh flow).
    Does NOT verify signature or expiration.

    Args:
        token: The JWT token string

    Returns:
        Dictionary containing the token payload

    Raises:
        InvalidTokenError: If the token is malformed
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
            options={"verify_exp": False},
        )
        return payload
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def generate_token_pair(user_id: UUID, tenant_id: UUID, extra_claims: Optional[dict] = None) -> dict:
    """
    Generate both access and refresh tokens.

    Args:
        user_id: The user's UUID
        tenant_id: The tenant's UUID
        extra_claims: Optional additional claims for the access token

    Returns:
        Dictionary with 'access_token' and 'refresh_token' keys
    """
    return {
        "access_token": generate_access_token(user_id, tenant_id, extra_claims),
        "refresh_token": generate_refresh_token(user_id, tenant_id),
    }


def verify_token_type(token: str, expected_type: str) -> dict:
    """
    Decode token and verify it matches the expected type.

    Args:
        token: The JWT token string
        expected_type: Expected token type ('access' or 'refresh')

    Returns:
        Dictionary containing the token payload

    Raises:
        InvalidTokenError: If token type doesn't match expected type
        TokenExpiredError: If the token has expired
    """
    payload = decode_token(token)

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected {expected_type} token, got {payload.get('type')}")

    return payload
