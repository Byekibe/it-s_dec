"""
Store schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate


class StoreResponseSchema(Schema):
    """Schema for store data in responses."""
    id = fields.UUID()
    name = fields.String()
    address = fields.String(allow_none=True)
    phone = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class StoreDetailResponseSchema(StoreResponseSchema):
    """Schema for detailed store data including user count."""
    user_count = fields.Integer()


class CreateStoreSchema(Schema):
    """Schema for creating a new store."""
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    address = fields.String(
        validate=validate.Length(max=1000),
        load_default=None
    )
    phone = fields.String(
        validate=validate.Length(max=50),
        load_default=None
    )
    email = fields.Email(load_default=None)


class UpdateStoreSchema(Schema):
    """Schema for updating a store."""
    name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    address = fields.String(
        validate=validate.Length(max=1000),
        allow_none=True
    )
    phone = fields.String(
        validate=validate.Length(max=50),
        allow_none=True
    )
    email = fields.Email(allow_none=True)
    is_active = fields.Boolean()


class StoreListResponseSchema(Schema):
    """Schema for paginated store list response."""
    stores = fields.List(fields.Nested(StoreResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class StoreListQuerySchema(Schema):
    """Schema for store list query parameters."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)


class StoreUserAssignmentSchema(Schema):
    """Schema for assigning/removing users from a store."""
    user_ids = fields.List(fields.UUID(), required=True)


class OperatingHoursSchema(Schema):
    """Schema for a single day's operating hours."""
    open = fields.String(validate=validate.Regexp(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'))
    close = fields.String(validate=validate.Regexp(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'))
    closed = fields.Boolean(load_default=False)


class StoreSettingsResponseSchema(Schema):
    """Schema for store settings response."""
    # Operating hours
    operating_hours = fields.Dict(keys=fields.String(), values=fields.Nested(OperatingHoursSchema), allow_none=True)

    # Receipt settings
    receipt_header = fields.String(allow_none=True)
    receipt_footer = fields.String(allow_none=True)
    print_receipt_by_default = fields.Boolean()

    # Store contact
    phone = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    address = fields.String(allow_none=True)

    # Inventory settings
    allow_negative_stock = fields.Boolean()
    low_stock_threshold = fields.Integer()


class UpdateStoreSettingsSchema(Schema):
    """Schema for updating store settings."""
    # Operating hours (JSON: {"monday": {"open": "08:00", "close": "18:00"}, ...})
    operating_hours = fields.Dict(
        keys=fields.String(validate=validate.OneOf([
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        ])),
        values=fields.Nested(OperatingHoursSchema),
        allow_none=True
    )

    # Receipt settings
    receipt_header = fields.String(validate=validate.Length(max=500), allow_none=True)
    receipt_footer = fields.String(validate=validate.Length(max=500), allow_none=True)
    print_receipt_by_default = fields.Boolean()

    # Store contact
    phone = fields.String(validate=validate.Length(max=50), allow_none=True)
    email = fields.Email(allow_none=True)
    address = fields.String(validate=validate.Length(max=1000), allow_none=True)

    # Inventory settings
    allow_negative_stock = fields.Boolean()
    low_stock_threshold = fields.Integer(validate=validate.Range(min=0, max=10000))
