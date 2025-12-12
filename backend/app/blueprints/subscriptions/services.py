"""
Subscription service with business logic for plans and subscriptions.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from flask import g
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.blueprints.subscriptions.models import Plan, Subscription, SubscriptionStatus, PaymentMethod
from app.blueprints.tenants.models import TenantUser
from app.blueprints.stores.models import Store
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError


class SubscriptionService:
    """Service handling subscription and plan operations."""

    # -------------------------
    # Plan Methods
    # -------------------------

    @staticmethod
    def get_all_plans(include_inactive: bool = False) -> List[Plan]:
        """
        Get all available plans.

        Args:
            include_inactive: Whether to include inactive plans

        Returns:
            List of Plan objects ordered by sort_order
        """
        query = db.session.query(Plan)

        if not include_inactive:
            query = query.filter(Plan.is_active == True)

        return query.order_by(Plan.sort_order.asc()).all()

    @staticmethod
    def get_plan_by_id(plan_id: UUID) -> Plan:
        """
        Get a plan by ID.

        Args:
            plan_id: Plan UUID

        Returns:
            Plan object

        Raises:
            NotFoundError: If plan not found
        """
        plan = db.session.query(Plan).filter(Plan.id == plan_id).first()

        if not plan:
            raise NotFoundError("Plan not found")

        return plan

    @staticmethod
    def get_plan_by_slug(slug: str) -> Plan:
        """
        Get a plan by slug.

        Args:
            slug: Plan slug (e.g., 'free', 'basic', 'pro')

        Returns:
            Plan object

        Raises:
            NotFoundError: If plan not found
        """
        plan = db.session.query(Plan).filter(Plan.slug == slug).first()

        if not plan:
            raise NotFoundError("Plan not found")

        return plan

    # -------------------------
    # Subscription Methods
    # -------------------------

    @staticmethod
    def get_current_subscription() -> Subscription:
        """
        Get the subscription for the current tenant.

        Returns:
            Subscription object with plan loaded

        Raises:
            NotFoundError: If no subscription found
        """
        tenant = g.tenant

        subscription = db.session.query(Subscription).options(
            joinedload(Subscription.plan)
        ).filter(
            Subscription.tenant_id == tenant.id
        ).first()

        if not subscription:
            raise NotFoundError("No subscription found for this tenant")

        return subscription

    @staticmethod
    def get_subscription_with_usage() -> dict:
        """
        Get current subscription with usage statistics.

        Returns:
            Dict with subscription and usage info
        """
        subscription = SubscriptionService.get_current_subscription()
        usage = SubscriptionService.get_usage()

        return {
            "subscription": subscription,
            "usage": usage,
        }

    @staticmethod
    def create_subscription(
        tenant_id: UUID,
        plan_slug: str = "free",
        start_trial: bool = True
    ) -> Subscription:
        """
        Create a new subscription for a tenant.

        Args:
            tenant_id: Tenant UUID
            plan_slug: Plan slug (defaults to 'free')
            start_trial: Whether to start a trial period

        Returns:
            New Subscription object
        """
        plan = SubscriptionService.get_plan_by_slug(plan_slug)

        now = datetime.utcnow()

        # Determine initial status and trial period
        if start_trial and plan.trial_days > 0:
            status = SubscriptionStatus.TRIALING.value
            trial_ends_at = now + timedelta(days=plan.trial_days)
        else:
            status = SubscriptionStatus.ACTIVE.value
            trial_ends_at = None

        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=status,
            trial_ends_at=trial_ends_at,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),  # Default to monthly
        )

        db.session.add(subscription)
        db.session.flush()  # Flush to get ID, let caller commit

        return subscription

    @staticmethod
    def change_plan(plan_id: UUID) -> Subscription:
        """
        Change the current tenant's subscription plan.

        Args:
            plan_id: New plan UUID

        Returns:
            Updated Subscription object

        Raises:
            NotFoundError: If plan not found
            ValidationError: If plan change not allowed
        """
        subscription = SubscriptionService.get_current_subscription()
        new_plan = SubscriptionService.get_plan_by_id(plan_id)

        if not new_plan.is_active:
            raise ValidationError("Cannot switch to inactive plan")

        # Check if new plan limits can accommodate current usage
        usage = SubscriptionService.get_usage()

        if new_plan.max_users and usage["users"]["current"] > new_plan.max_users:
            raise ValidationError(
                f"Cannot downgrade: current user count ({usage['users']['current']}) "
                f"exceeds new plan limit ({new_plan.max_users})"
            )

        if new_plan.max_stores and usage["stores"]["current"] > new_plan.max_stores:
            raise ValidationError(
                f"Cannot downgrade: current store count ({usage['stores']['current']}) "
                f"exceeds new plan limit ({new_plan.max_stores})"
            )

        # Update subscription
        subscription.plan_id = new_plan.id
        subscription.updated_at = datetime.utcnow()

        # If switching from free plan to paid, handle trial
        if subscription.status == SubscriptionStatus.TRIALING.value:
            # Stay in trial for the new plan if trial days remain
            pass
        elif subscription.plan.slug == "free" and new_plan.slug != "free":
            # Switching from free to paid - might start trial
            if new_plan.trial_days > 0 and not subscription.trial_ends_at:
                subscription.status = SubscriptionStatus.TRIALING.value
                subscription.trial_ends_at = datetime.utcnow() + timedelta(days=new_plan.trial_days)

        db.session.commit()
        db.session.refresh(subscription)

        return subscription

    @staticmethod
    def cancel_subscription(cancel_immediately: bool = False, reason: Optional[str] = None) -> Subscription:
        """
        Cancel the current tenant's subscription.

        Args:
            cancel_immediately: If True, cancel now; if False, cancel at period end
            reason: Optional cancellation reason

        Returns:
            Updated Subscription object
        """
        subscription = SubscriptionService.get_current_subscription()

        now = datetime.utcnow()
        subscription.canceled_at = now

        if cancel_immediately:
            subscription.status = SubscriptionStatus.CANCELED.value
        else:
            subscription.cancel_at_period_end = True

        subscription.updated_at = now
        db.session.commit()

        return subscription

    @staticmethod
    def reactivate_subscription() -> Subscription:
        """
        Reactivate a canceled subscription.

        Returns:
            Updated Subscription object

        Raises:
            ValidationError: If subscription cannot be reactivated
        """
        subscription = SubscriptionService.get_current_subscription()

        if subscription.status == SubscriptionStatus.EXPIRED.value:
            raise ValidationError("Cannot reactivate expired subscription. Please start a new subscription.")

        if subscription.status == SubscriptionStatus.CANCELED.value:
            subscription.status = SubscriptionStatus.ACTIVE.value

        subscription.canceled_at = None
        subscription.cancel_at_period_end = False
        subscription.updated_at = datetime.utcnow()

        db.session.commit()

        return subscription

    @staticmethod
    def update_payment_method(payment_method: str) -> Subscription:
        """
        Update the payment method for current subscription.

        Args:
            payment_method: Payment method value (from PaymentMethod enum)

        Returns:
            Updated Subscription object
        """
        subscription = SubscriptionService.get_current_subscription()

        subscription.payment_method = payment_method
        subscription.updated_at = datetime.utcnow()

        db.session.commit()

        return subscription

    # -------------------------
    # Usage & Limits
    # -------------------------

    @staticmethod
    def get_usage() -> dict:
        """
        Get current usage statistics for the tenant.

        Returns:
            Dict with usage info for users, stores, products
        """
        tenant = g.tenant

        # Get user count
        user_count = db.session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant.id
        ).count()

        # Get active store count
        store_count = db.session.query(Store).filter(
            Store.tenant_id == tenant.id,
            Store.is_active == True,
            Store.deleted_at.is_(None)
        ).count()

        # Get subscription for limits
        try:
            subscription = SubscriptionService.get_current_subscription()
            plan = subscription.plan
        except NotFoundError:
            # No subscription - use free plan limits as default
            plan = SubscriptionService.get_plan_by_slug("free")

        return {
            "users": {
                "current": user_count,
                "limit": plan.max_users,
                "remaining": (plan.max_users - user_count) if plan.max_users else None,
            },
            "stores": {
                "current": store_count,
                "limit": plan.max_stores,
                "remaining": (plan.max_stores - store_count) if plan.max_stores else None,
            },
            "products": {
                "current": 0,  # TODO: Implement when products are added
                "limit": plan.max_products,
                "remaining": plan.max_products,  # TODO: Calculate properly
            },
        }

    @staticmethod
    def check_can_add_user() -> bool:
        """
        Check if current tenant can add another user.

        Returns:
            True if user can be added

        Raises:
            ForbiddenError: If user limit reached
        """
        usage = SubscriptionService.get_usage()

        if usage["users"]["limit"] is not None:
            if usage["users"]["current"] >= usage["users"]["limit"]:
                raise ForbiddenError(
                    f"User limit reached ({usage['users']['limit']}). "
                    "Please upgrade your plan to add more users."
                )

        return True

    @staticmethod
    def check_can_add_store() -> bool:
        """
        Check if current tenant can add another store.

        Returns:
            True if store can be added

        Raises:
            ForbiddenError: If store limit reached
        """
        usage = SubscriptionService.get_usage()

        if usage["stores"]["limit"] is not None:
            if usage["stores"]["current"] >= usage["stores"]["limit"]:
                raise ForbiddenError(
                    f"Store limit reached ({usage['stores']['limit']}). "
                    "Please upgrade your plan to add more stores."
                )

        return True

    @staticmethod
    def check_subscription_active() -> bool:
        """
        Check if current subscription is active.

        Returns:
            True if subscription allows access

        Raises:
            ForbiddenError: If subscription not active
        """
        try:
            subscription = SubscriptionService.get_current_subscription()
        except NotFoundError:
            raise ForbiddenError("No active subscription. Please subscribe to continue.")

        if not subscription.is_active:
            if subscription.status == SubscriptionStatus.PAST_DUE.value:
                raise ForbiddenError("Subscription past due. Please update your payment method.")
            elif subscription.status == SubscriptionStatus.CANCELED.value:
                raise ForbiddenError("Subscription canceled. Please reactivate to continue.")
            elif subscription.status == SubscriptionStatus.EXPIRED.value:
                raise ForbiddenError("Subscription expired. Please renew to continue.")
            else:
                raise ForbiddenError("Subscription inactive. Please contact support.")

        return True

    @staticmethod
    def check_trial_status() -> dict:
        """
        Check trial status for current subscription.

        Returns:
            Dict with trial info
        """
        try:
            subscription = SubscriptionService.get_current_subscription()
        except NotFoundError:
            return {"is_trial": False, "days_remaining": 0}

        if not subscription.is_trialing or not subscription.trial_ends_at:
            return {"is_trial": False, "days_remaining": 0}

        now = datetime.utcnow()
        days_remaining = (subscription.trial_ends_at - now).days

        return {
            "is_trial": True,
            "trial_ends_at": subscription.trial_ends_at,
            "days_remaining": max(0, days_remaining),
        }
