"""
Subscription schemas for request/response validation.
"""

from marshmallow import Schema, fields, validate

from app.blueprints.subscriptions.models import SubscriptionStatus, PaymentMethod


class PlanResponseSchema(Schema):
    """Schema for plan data in responses."""
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    description = fields.String(allow_none=True)
    price_monthly = fields.Float()
    price_yearly = fields.Float()
    max_users = fields.Integer(allow_none=True)
    max_stores = fields.Integer(allow_none=True)
    max_products = fields.Integer(allow_none=True)
    features = fields.Dict(allow_none=True)
    trial_days = fields.Integer()


class PlanListResponseSchema(Schema):
    """Schema for list of plans response."""
    plans = fields.List(fields.Nested(PlanResponseSchema))


class SubscriptionResponseSchema(Schema):
    """Schema for subscription data in responses."""
    id = fields.UUID()
    tenant_id = fields.UUID()
    plan_id = fields.UUID()
    status = fields.String()
    current_period_start = fields.DateTime(allow_none=True)
    current_period_end = fields.DateTime(allow_none=True)
    trial_ends_at = fields.DateTime(allow_none=True)
    canceled_at = fields.DateTime(allow_none=True)
    cancel_at_period_end = fields.Boolean()
    payment_method = fields.String()
    plan = fields.Nested(PlanResponseSchema)


class SubscriptionDetailResponseSchema(SubscriptionResponseSchema):
    """Schema for detailed subscription with usage info."""
    usage = fields.Dict(keys=fields.String(), values=fields.Dict())


class UsageResponseSchema(Schema):
    """Schema for subscription usage/limits."""
    users = fields.Dict(keys=fields.String(), values=fields.Raw())
    stores = fields.Dict(keys=fields.String(), values=fields.Raw())
    products = fields.Dict(keys=fields.String(), values=fields.Raw())


class ChangePlanSchema(Schema):
    """Schema for changing subscription plan."""
    plan_id = fields.UUID(required=True)


class UpdatePaymentMethodSchema(Schema):
    """Schema for updating payment method."""
    payment_method = fields.String(
        required=True,
        validate=validate.OneOf([pm.value for pm in PaymentMethod])
    )


class CancelSubscriptionSchema(Schema):
    """Schema for canceling subscription."""
    cancel_immediately = fields.Boolean(load_default=False)
    reason = fields.String(validate=validate.Length(max=500), allow_none=True)
