"""
RBAC schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate


class PermissionResponseSchema(Schema):
    """Schema for permission data in responses."""
    id = fields.UUID()
    name = fields.String()
    resource = fields.String()
    action = fields.String()
    description = fields.String(allow_none=True)


class RoleResponseSchema(Schema):
    """Schema for role data in responses."""
    id = fields.UUID()
    name = fields.String()
    description = fields.String(allow_none=True)
    is_system_role = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class RoleDetailResponseSchema(RoleResponseSchema):
    """Schema for detailed role data including permissions."""
    permissions = fields.List(fields.Nested(PermissionResponseSchema))
    user_count = fields.Integer()


class CreateRoleSchema(Schema):
    """Schema for creating a new role."""
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    description = fields.String(
        validate=validate.Length(max=500),
        load_default=None
    )
    permission_ids = fields.List(fields.UUID(), load_default=[])


class UpdateRoleSchema(Schema):
    """Schema for updating a role."""
    name = fields.String(
        validate=validate.Length(min=1, max=100)
    )
    description = fields.String(
        validate=validate.Length(max=500),
        allow_none=True
    )
    permission_ids = fields.List(fields.UUID())


class RoleListResponseSchema(Schema):
    """Schema for role list response."""
    roles = fields.List(fields.Nested(RoleResponseSchema))
    total = fields.Integer()


class PermissionListResponseSchema(Schema):
    """Schema for permission list response."""
    permissions = fields.List(fields.Nested(PermissionResponseSchema))
    total = fields.Integer()


class AssignRoleSchema(Schema):
    """Schema for assigning a role to a user."""
    role_id = fields.UUID(required=True)
    store_id = fields.UUID(load_default=None)  # None = tenant-wide


class UserRoleResponseSchema(Schema):
    """Schema for user role assignment in responses."""
    id = fields.UUID()
    role_id = fields.UUID()
    role_name = fields.String()
    store_id = fields.UUID(allow_none=True)
    store_name = fields.String(allow_none=True)
    assigned_at = fields.DateTime()


class UserRolesResponseSchema(Schema):
    """Schema for list of user role assignments."""
    user_id = fields.UUID()
    roles = fields.List(fields.Nested(UserRoleResponseSchema))
