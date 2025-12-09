"""
Tenant schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate


class TenantResponseSchema(Schema):
    """Schema for tenant data in responses."""
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    status = fields.Method("get_status")
    trial_ends_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    def get_status(self, obj):
        """Get status value from enum."""
        if hasattr(obj, 'status'):
            return obj.status.value if obj.status else None
        return obj.get('status')


class TenantDetailResponseSchema(TenantResponseSchema):
    """Schema for detailed tenant data including stats."""
    user_count = fields.Integer()
    store_count = fields.Integer()


class UpdateTenantSchema(Schema):
    """Schema for updating tenant settings."""
    name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    slug = fields.String(
        validate=[
            validate.Length(min=3, max=100),
            validate.Regexp(
                r'^[a-z0-9-]+$',
                error="Slug must contain only lowercase letters, numbers, and hyphens"
            )
        ]
    )
