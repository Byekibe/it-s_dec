"""
Tests for subscription endpoints and limit enforcement.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.extensions import db
from app.blueprints.subscriptions.models import Plan, Subscription, SubscriptionStatus
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.blueprints.users.models import User
from app.blueprints.stores.models import Store
from app.blueprints.rbac.models import Permission, Role
from app.core.utils import generate_token_pair


# =============================================================================
# Plan Fixtures
# =============================================================================

@pytest.fixture
def plans(app):
    """Get existing plans and add test-specific inactive plan."""
    with app.app_context():
        # Plans are created in conftest.py via _create_default_plans()
        free_plan = db.session.query(Plan).filter(Plan.slug == "free").first()
        basic_plan = db.session.query(Plan).filter(Plan.slug == "basic").first()
        pro_plan = db.session.query(Plan).filter(Plan.slug == "pro").first()

        # Add inactive plan for testing (this one doesn't exist in defaults)
        inactive_plan = Plan(
            name="Deprecated",
            slug="deprecated",
            description="Deprecated tier",
            price_monthly=500,
            price_yearly=5000,
            max_users=3,
            max_stores=2,
            max_products=200,
            trial_days=0,
            sort_order=99,
            is_active=False,
        )
        db.session.add(inactive_plan)
        db.session.commit()
        db.session.refresh(inactive_plan)

        yield {
            "free": free_plan,
            "basic": basic_plan,
            "pro": pro_plan,
            "inactive": inactive_plan,
        }


@pytest.fixture
def subscription_permissions(app, permissions, admin_role):
    """Add subscription permissions to existing permissions and admin role."""
    from app.blueprints.rbac.models import RolePermission
    with app.app_context():
        # Create subscription permissions
        view_perm = Permission(name="subscription.view", resource="subscription", action="view", description="View subscription")
        manage_perm = Permission(name="subscription.manage", resource="subscription", action="manage", description="Manage subscription")
        db.session.add_all([view_perm, manage_perm])
        db.session.flush()

        # Add to admin role
        role = db.session.get(Role, admin_role.id)
        for perm in [view_perm, manage_perm]:
            role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
            db.session.add(role_perm)

        db.session.commit()
        yield [view_perm, manage_perm]


@pytest.fixture
def subscription(app, tenant, plans):
    """Create a subscription for the tenant."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)
        free_plan = db.session.query(Plan).filter(Plan.slug == "free").first()

        sub = Subscription(
            tenant_id=tenant_obj.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(sub)
        db.session.commit()
        db.session.refresh(sub)
        yield sub


@pytest.fixture
def trial_subscription(app, tenant, plans):
    """Create a trialing subscription for the tenant."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)
        basic_plan = db.session.query(Plan).filter(Plan.slug == "basic").first()

        sub = Subscription(
            tenant_id=tenant_obj.id,
            plan_id=basic_plan.id,
            status=SubscriptionStatus.TRIALING.value,
            trial_ends_at=datetime.utcnow() + timedelta(days=10),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(sub)
        db.session.commit()
        db.session.refresh(sub)
        yield sub


# =============================================================================
# Plan Endpoint Tests
# =============================================================================

class TestPlanEndpoints:
    """Tests for /api/v1/subscriptions/plans endpoints."""

    def test_list_plans_returns_active_plans(self, client, auth_headers, plans):
        """Test that list plans returns only active plans by default."""
        response = client.get("/api/v1/subscriptions/plans", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "plans" in data
        assert len(data["plans"]) == 3  # free, basic, pro (not inactive)

        slugs = [p["slug"] for p in data["plans"]]
        assert "free" in slugs
        assert "basic" in slugs
        assert "pro" in slugs
        assert "deprecated" not in slugs

    def test_list_plans_with_inactive(self, client, auth_headers, plans):
        """Test that include_inactive=true returns all plans."""
        response = client.get(
            "/api/v1/subscriptions/plans?include_inactive=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["plans"]) == 4  # All plans including inactive

    def test_list_plans_unauthorized(self, client, plans):
        """Test that unauthenticated users cannot list plans."""
        response = client.get("/api/v1/subscriptions/plans")

        assert response.status_code == 401

    def test_get_plan_by_id(self, client, auth_headers, plans):
        """Test getting a specific plan by ID."""
        plan_id = str(plans["basic"].id)
        response = client.get(f"/api/v1/subscriptions/plans/{plan_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["slug"] == "basic"
        assert data["name"] == "Basic"
        assert data["max_users"] == 5

    def test_get_plan_not_found(self, client, auth_headers, plans):
        """Test getting a non-existent plan."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/subscriptions/plans/{fake_id}", headers=auth_headers)

        assert response.status_code == 404


# =============================================================================
# Subscription Endpoint Tests
# =============================================================================

class TestSubscriptionEndpoints:
    """Tests for /api/v1/subscriptions/current endpoints."""

    def test_get_current_subscription(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test getting current subscription."""
        response = client.get("/api/v1/subscriptions/current", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["status"] == "active"
        assert "plan" in data
        assert data["plan"]["slug"] == "free"

    def test_get_subscription_details_with_usage(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test getting subscription with usage info."""
        response = client.get("/api/v1/subscriptions/current/details", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "subscription" in data
        assert "usage" in data
        assert "users" in data["usage"]
        assert "stores" in data["usage"]

    def test_get_usage(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test getting usage statistics."""
        response = client.get("/api/v1/subscriptions/current/usage", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "users" in data
        assert data["users"]["limit"] == 2  # Free plan limit
        assert data["users"]["current"] >= 1  # At least the test user

    def test_get_trial_status_active_trial(
        self, client, app, user, tenant, tenant_user, plans,
        permissions, admin_role, user_with_admin_role, subscription_permissions
    ):
        """Test trial status for trialing subscription."""
        # Create trial subscription
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            basic_plan = db.session.query(Plan).filter(Plan.slug == "basic").first()

            sub = Subscription(
                tenant_id=tenant_obj.id,
                plan_id=basic_plan.id,
                status=SubscriptionStatus.TRIALING.value,
                trial_ends_at=datetime.utcnow() + timedelta(days=10),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(sub)
            db.session.commit()

        # Generate tokens
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }

        response = client.get("/api/v1/subscriptions/current/trial", headers=headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["is_trial"] is True
        assert data["days_remaining"] >= 9  # At least 9 days remaining


# =============================================================================
# Plan Change Tests
# =============================================================================

class TestPlanChange:
    """Tests for plan change functionality."""

    def test_change_plan_upgrade(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test upgrading to a higher plan."""
        basic_plan_id = str(plans["basic"].id)

        response = client.post(
            "/api/v1/subscriptions/current/change-plan",
            headers=auth_headers,
            json={"plan_id": basic_plan_id}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["plan"]["slug"] == "basic"

    def test_change_plan_to_inactive_fails(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test that switching to inactive plan fails."""
        inactive_plan_id = str(plans["inactive"].id)

        response = client.post(
            "/api/v1/subscriptions/current/change-plan",
            headers=auth_headers,
            json={"plan_id": inactive_plan_id}
        )

        assert response.status_code == 400


# =============================================================================
# Limit Enforcement Tests
# =============================================================================

class TestLimitEnforcement:
    """Tests for subscription limit enforcement."""

    def test_user_limit_enforcement(
        self, client, app, user, tenant, tenant_user, plans, subscription,
        permissions, admin_role, user_with_admin_role, subscription_permissions
    ):
        """Test that user creation is blocked when limit reached."""
        # Free plan has max_users=2
        # Add another user to reach the limit
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)

            # Create second user to reach limit
            user2 = User(email="user2@test.com", full_name="User Two", is_active=True)
            user2.set_password("password123")
            db.session.add(user2)
            db.session.flush()

            tenant_user2 = TenantUser(
                user_id=user2.id,
                tenant_id=tenant_obj.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tenant_user2)
            db.session.commit()

        # Generate tokens
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }

        # Now try to create a third user - should fail
        response = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "user3@test.com",
                "full_name": "User Three",
                "password": "password123"
            }
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "limit" in data.get("error", "").lower() or "limit" in data.get("message", "").lower()

    def test_store_limit_enforcement(
        self, client, app, user, tenant, tenant_user, plans, subscription,
        permissions, admin_role, user_with_admin_role, subscription_permissions
    ):
        """Test that store creation is blocked when limit reached."""
        # Free plan has max_stores=1
        # Create a store to reach the limit
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            user_obj = db.session.get(User, user.id)

            store = Store(
                tenant_id=tenant_obj.id,
                name="First Store",
                is_active=True,
                created_by=user_obj.id
            )
            db.session.add(store)
            db.session.commit()

        # Generate tokens
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }

        # Now try to create a second store - should fail
        response = client.post(
            "/api/v1/stores",
            headers=headers,
            json={"name": "Second Store"}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "limit" in data.get("error", "").lower() or "limit" in data.get("message", "").lower()

    def test_unlimited_plan_allows_users(
        self, client, app, user, tenant, tenant_user, plans,
        permissions, admin_role, user_with_admin_role, subscription_permissions
    ):
        """Test that Pro plan (unlimited) allows user creation."""
        # Create subscription with Pro plan
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            pro_plan = db.session.query(Plan).filter(Plan.slug == "pro").first()

            sub = Subscription(
                tenant_id=tenant_obj.id,
                plan_id=pro_plan.id,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(sub)
            db.session.commit()

        # Generate tokens
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }

        # Create many users - should all succeed
        for i in range(5):
            response = client.post(
                "/api/v1/users",
                headers=headers,
                json={
                    "email": f"prouser{i}@test.com",
                    "full_name": f"Pro User {i}",
                    "password": "password123"
                }
            )
            assert response.status_code == 201


# =============================================================================
# Cancellation Tests
# =============================================================================

class TestCancellation:
    """Tests for subscription cancellation."""

    def test_cancel_subscription_at_period_end(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test canceling subscription at period end."""
        response = client.post(
            "/api/v1/subscriptions/current/cancel",
            headers=auth_headers,
            json={"cancel_immediately": False, "reason": "Testing"}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["cancel_at_period_end"] is True
        assert data["canceled_at"] is not None
        # Status should still be active until period ends
        assert data["status"] == "active"

    def test_cancel_subscription_immediately(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test immediate subscription cancellation."""
        response = client.post(
            "/api/v1/subscriptions/current/cancel",
            headers=auth_headers,
            json={"cancel_immediately": True}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["status"] == "canceled"

    def test_reactivate_canceled_subscription(
        self, client, app, user, tenant, tenant_user, plans,
        permissions, admin_role, user_with_admin_role, subscription_permissions
    ):
        """Test reactivating a canceled subscription."""
        # Create canceled subscription
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            free_plan = db.session.query(Plan).filter(Plan.slug == "free").first()

            sub = Subscription(
                tenant_id=tenant_obj.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.CANCELED.value,
                canceled_at=datetime.utcnow(),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(sub)
            db.session.commit()

        # Generate tokens
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }

        response = client.post(
            "/api/v1/subscriptions/current/reactivate",
            headers=headers
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["status"] == "active"
        assert data["canceled_at"] is None


# =============================================================================
# Payment Method Tests
# =============================================================================

class TestPaymentMethod:
    """Tests for payment method updates."""

    def test_update_payment_method(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test updating payment method."""
        response = client.put(
            "/api/v1/subscriptions/current/payment-method",
            headers=auth_headers,
            json={"payment_method": "mpesa"}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["payment_method"] == "mpesa"

    def test_update_payment_method_invalid(
        self, client, auth_headers, plans, subscription,
        user_with_admin_role, subscription_permissions
    ):
        """Test updating with invalid payment method."""
        response = client.put(
            "/api/v1/subscriptions/current/payment-method",
            headers=auth_headers,
            json={"payment_method": "invalid_method"}
        )

        assert response.status_code == 400


# =============================================================================
# Registration Subscription Creation Tests
# =============================================================================

class TestRegistrationSubscription:
    """Tests for automatic subscription creation on registration."""

    def test_registration_creates_subscription(self, client, app, plans):
        """Test that registering creates a subscription automatically."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "Password123!",
                "full_name": "New User",
                "tenant_name": "New Company",
                "tenant_slug": "new-company"
            }
        )

        assert response.status_code == 201
        data = response.get_json()

        tenant_id = data["tenant"]["id"]

        # Check subscription was created
        with app.app_context():
            from uuid import UUID
            sub = db.session.query(Subscription).filter(
                Subscription.tenant_id == UUID(tenant_id)
            ).first()

            assert sub is not None
            assert sub.status in [SubscriptionStatus.TRIALING.value, SubscriptionStatus.ACTIVE.value]
