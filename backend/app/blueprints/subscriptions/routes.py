"""
Subscription management routes.
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.blueprints.subscriptions.services import SubscriptionService
from app.blueprints.subscriptions.schemas import (
    PlanResponseSchema,
    PlanListResponseSchema,
    SubscriptionResponseSchema,
    SubscriptionDetailResponseSchema,
    UsageResponseSchema,
    ChangePlanSchema,
    UpdatePaymentMethodSchema,
    CancelSubscriptionSchema,
)
from app.core.decorators import require_permission, jwt_required
from app.core.constants import Permissions
from app.core.exceptions import ValidationError as AppValidationError

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


# -------------------------
# Plan Routes (Public for listing)
# -------------------------

@subscriptions_bp.route("/plans", methods=["GET"])
@jwt_required
def list_plans():
    """
    Get all available subscription plans.

    Query params:
        include_inactive: Include inactive plans (admin only)

    Returns:
        List of available plans
    """
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    plans = SubscriptionService.get_all_plans(include_inactive=include_inactive)

    schema = PlanResponseSchema(many=True)
    return jsonify({"plans": schema.dump(plans)}), 200


@subscriptions_bp.route("/plans/<uuid:plan_id>", methods=["GET"])
@jwt_required
def get_plan(plan_id):
    """
    Get a specific plan by ID.

    Args:
        plan_id: Plan UUID

    Returns:
        Plan details
    """
    plan = SubscriptionService.get_plan_by_id(plan_id)

    schema = PlanResponseSchema()
    return jsonify(schema.dump(plan)), 200


# -------------------------
# Subscription Routes
# -------------------------

@subscriptions_bp.route("/current", methods=["GET"])
@require_permission(Permissions.SUBSCRIPTION_VIEW)
def get_current_subscription():
    """
    Get current tenant's subscription.

    Returns:
        Subscription with plan details
    """
    subscription = SubscriptionService.get_current_subscription()

    schema = SubscriptionResponseSchema()
    return jsonify(schema.dump(subscription)), 200


@subscriptions_bp.route("/current/details", methods=["GET"])
@require_permission(Permissions.SUBSCRIPTION_VIEW)
def get_subscription_details():
    """
    Get current subscription with usage statistics.

    Returns:
        Subscription with plan and usage info
    """
    result = SubscriptionService.get_subscription_with_usage()

    subscription_schema = SubscriptionResponseSchema()
    usage_schema = UsageResponseSchema()

    return jsonify({
        "subscription": subscription_schema.dump(result["subscription"]),
        "usage": usage_schema.dump(result["usage"]),
    }), 200


@subscriptions_bp.route("/current/usage", methods=["GET"])
@require_permission(Permissions.SUBSCRIPTION_VIEW)
def get_usage():
    """
    Get current usage against plan limits.

    Returns:
        Usage statistics for users, stores, products
    """
    usage = SubscriptionService.get_usage()

    schema = UsageResponseSchema()
    return jsonify(schema.dump(usage)), 200


@subscriptions_bp.route("/current/trial", methods=["GET"])
@require_permission(Permissions.SUBSCRIPTION_VIEW)
def get_trial_status():
    """
    Get trial status for current subscription.

    Returns:
        Trial info including days remaining
    """
    trial_info = SubscriptionService.check_trial_status()
    return jsonify(trial_info), 200


@subscriptions_bp.route("/current/change-plan", methods=["POST"])
@require_permission(Permissions.SUBSCRIPTION_MANAGE)
def change_plan():
    """
    Change the current subscription plan.

    Request body:
        plan_id: New plan UUID

    Returns:
        Updated subscription
    """
    schema = ChangePlanSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    subscription = SubscriptionService.change_plan(plan_id=data["plan_id"])

    response_schema = SubscriptionResponseSchema()
    return jsonify(response_schema.dump(subscription)), 200


@subscriptions_bp.route("/current/cancel", methods=["POST"])
@require_permission(Permissions.SUBSCRIPTION_MANAGE)
def cancel_subscription():
    """
    Cancel the current subscription.

    Request body:
        cancel_immediately: Cancel now vs at period end (default: false)
        reason: Optional cancellation reason

    Returns:
        Updated subscription
    """
    schema = CancelSubscriptionSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    subscription = SubscriptionService.cancel_subscription(
        cancel_immediately=data.get("cancel_immediately", False),
        reason=data.get("reason"),
    )

    response_schema = SubscriptionResponseSchema()
    return jsonify(response_schema.dump(subscription)), 200


@subscriptions_bp.route("/current/reactivate", methods=["POST"])
@require_permission(Permissions.SUBSCRIPTION_MANAGE)
def reactivate_subscription():
    """
    Reactivate a canceled subscription.

    Returns:
        Updated subscription
    """
    subscription = SubscriptionService.reactivate_subscription()

    response_schema = SubscriptionResponseSchema()
    return jsonify(response_schema.dump(subscription)), 200


@subscriptions_bp.route("/current/payment-method", methods=["PUT"])
@require_permission(Permissions.SUBSCRIPTION_MANAGE)
def update_payment_method():
    """
    Update payment method for current subscription.

    Request body:
        payment_method: Payment method (none, mpesa, manual)

    Returns:
        Updated subscription
    """
    schema = UpdatePaymentMethodSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    subscription = SubscriptionService.update_payment_method(
        payment_method=data["payment_method"]
    )

    response_schema = SubscriptionResponseSchema()
    return jsonify(response_schema.dump(subscription)), 200
