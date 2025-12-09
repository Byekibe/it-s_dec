"""
Authentication schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate, validates, ValidationError


class LoginSchema(Schema):
    """Schema for login requests."""
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    tenant_id = fields.UUID(required=True)


class RegisterSchema(Schema):
    """Schema for user registration with new tenant."""
    # User fields
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters")
    )
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )

    # Tenant fields
    tenant_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    tenant_slug = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=100),
            validate.Regexp(
                r'^[a-z0-9-]+$',
                error="Slug must contain only lowercase letters, numbers, and hyphens"
            )
        ]
    )


class BootstrapSchema(Schema):
    """Schema for bootstrapping the first user/tenant."""
    # User fields
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters")
    )
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )

    # Tenant fields
    tenant_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    tenant_slug = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=100),
            validate.Regexp(
                r'^[a-z0-9-]+$',
                error="Slug must contain only lowercase letters, numbers, and hyphens"
            )
        ]
    )


class RefreshTokenSchema(Schema):
    """Schema for token refresh requests."""
    refresh_token = fields.String(required=True, load_only=True)


class TokenResponseSchema(Schema):
    """Schema for token responses."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer")
    expires_in = fields.Integer()


class UserResponseSchema(Schema):
    """Schema for user data in responses."""
    id = fields.UUID()
    email = fields.Email()
    full_name = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()


class TenantResponseSchema(Schema):
    """Schema for tenant data in responses."""
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    status = fields.String()


class AuthResponseSchema(Schema):
    """Schema for full auth response (tokens + user + tenant)."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer")
    expires_in = fields.Integer()
    user = fields.Nested(UserResponseSchema)
    tenant = fields.Nested(TenantResponseSchema)
