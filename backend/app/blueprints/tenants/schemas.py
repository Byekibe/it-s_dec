"""
Tenant schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate
from app.blueprints.tenants.models import TenantStatus


class TenantResponseSchema(Schema):
    """Schema for tenant data in responses."""
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    status = fields.Enum(TenantStatus, by_value=True)
    trial_ends_at = fields.DateTime(allow_none=True)


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


class TenantSettingsResponseSchema(Schema):
    """Schema for tenant settings response."""
    # Regional
    timezone = fields.String()
    currency = fields.String()
    locale = fields.String()

    # Display formats
    date_format = fields.String()
    time_format = fields.String()

    # Tax settings
    tax_rate = fields.Float()
    tax_inclusive_pricing = fields.Boolean()
    tax_id = fields.String(allow_none=True)

    # Fiscal/Accounting
    fiscal_year_start_month = fields.Integer()
    fiscal_year_start_day = fields.Integer()

    # Business info
    business_name = fields.String(allow_none=True)
    business_address = fields.String(allow_none=True)
    business_phone = fields.String(allow_none=True)
    business_email = fields.String(allow_none=True)


class UpdateTenantSettingsSchema(Schema):
    """Schema for updating tenant settings."""
    # Regional
    timezone = fields.String(validate=validate.Length(max=50))
    currency = fields.String(validate=validate.Length(min=3, max=3))
    locale = fields.String(validate=validate.Length(max=10))

    # Display formats
    date_format = fields.String(
        validate=validate.OneOf(['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'])
    )
    time_format = fields.String(
        validate=validate.OneOf(['12h', '24h'])
    )

    # Tax settings
    tax_rate = fields.Float(validate=validate.Range(min=0, max=100))
    tax_inclusive_pricing = fields.Boolean()
    tax_id = fields.String(validate=validate.Length(max=50), allow_none=True)

    # Fiscal/Accounting
    fiscal_year_start_month = fields.Integer(validate=validate.Range(min=1, max=12))
    fiscal_year_start_day = fields.Integer(validate=validate.Range(min=1, max=31))

    # Business info
    business_name = fields.String(validate=validate.Length(max=255), allow_none=True)
    business_address = fields.String(validate=validate.Length(max=500), allow_none=True)
    business_phone = fields.String(validate=validate.Length(max=50), allow_none=True)
    business_email = fields.Email(allow_none=True)
