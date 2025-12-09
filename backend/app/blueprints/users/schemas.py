"""
User schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate, validates, ValidationError


class UserResponseSchema(Schema):
    """Schema for user data in responses."""
    id = fields.UUID()
    email = fields.Email()
    full_name = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class UserDetailResponseSchema(UserResponseSchema):
    """Schema for detailed user data including tenant membership info."""
    roles = fields.List(fields.Nested("RoleInfoSchema"))
    stores = fields.List(fields.Nested("StoreInfoSchema"))


class RoleInfoSchema(Schema):
    """Schema for role info in user responses."""
    id = fields.UUID()
    name = fields.String()
    store_id = fields.UUID(allow_none=True)
    store_name = fields.String(allow_none=True)


class StoreInfoSchema(Schema):
    """Schema for store info in user responses."""
    id = fields.UUID()
    name = fields.String()


class UpdateCurrentUserSchema(Schema):
    """Schema for updating current user's own profile."""
    full_name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    current_password = fields.String(load_only=True)
    new_password = fields.String(
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters")
    )

    @validates("new_password")
    def validate_new_password(self, value):
        """Ensure current_password is provided when changing password."""
        # Note: This validation happens at the service level since we need
        # access to both fields together


class CreateUserSchema(Schema):
    """Schema for creating/inviting a new user to the tenant."""
    email = fields.Email(required=True)
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    password = fields.String(
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters")
    )
    role_ids = fields.List(fields.UUID(), load_default=[])
    store_ids = fields.List(fields.UUID(), load_default=[])


class UpdateUserSchema(Schema):
    """Schema for admin updating a user's details."""
    full_name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    is_active = fields.Boolean()
    role_ids = fields.List(fields.UUID())
    store_ids = fields.List(fields.UUID())


class UserListResponseSchema(Schema):
    """Schema for paginated user list response."""
    users = fields.List(fields.Nested(UserResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class UserListQuerySchema(Schema):
    """Schema for user list query parameters."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)
    store_id = fields.UUID(load_default=None)
