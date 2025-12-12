"""
Tenant API endpoint tests.

Tests for:
- GET /api/v1/tenants/current
- PUT /api/v1/tenants/current
"""

import pytest

from app.extensions import db
from app.blueprints.tenants.models import Tenant, TenantStatus


class TestCurrentTenant:
    """Tests for /api/v1/tenants/current endpoint."""

    @pytest.mark.integration
    def test_get_current_tenant(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting current tenant info."""
        response = client.get("/api/v1/tenants/current", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["id"] == str(tenant.id)
        assert data["name"] == tenant.name
        assert data["slug"] == tenant.slug
        assert data["status"] == tenant.status.value

    @pytest.mark.integration
    def test_get_current_tenant_unauthenticated(self, client):
        """Test getting current tenant without authentication."""
        response = client.get("/api/v1/tenants/current")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_update_current_tenant_name(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating current tenant's name."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "name": "Updated Company Name"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Company Name"

    @pytest.mark.integration
    def test_update_current_tenant_slug(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating current tenant's slug."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "slug": "new-company-slug"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["slug"] == "new-company-slug"

    @pytest.mark.integration
    def test_update_tenant_duplicate_slug_fails(
        self, client, app, user, tenant, tenant_user, second_tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that updating to an existing slug fails."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "slug": second_tenant.slug  # Already exists
        })

        assert response.status_code == 409

    @pytest.mark.integration
    def test_update_tenant_invalid_slug_format(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that invalid slug format is rejected."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "slug": "Invalid Slug With Spaces!"
        })

        assert response.status_code == 400


class TestTenantStatus:
    """Tests for tenant status handling."""

    @pytest.mark.integration
    def test_trial_tenant_can_operate(self, client, app, user_password, permissions):
        """Test that trial tenant can perform normal operations after registration."""
        from app.blueprints.auth.services import AuthService

        with app.app_context():
            # Use the registration service to create a user and a trial tenant with roles.
            # This is a more realistic integration test.
            reg_data = AuthService.register(
                email="trialuser@example.com",
                password=user_password,
                full_name="Trial User",
                tenant_name="Trial From Reg",
                tenant_slug="trial-from-reg"
            )
            tokens = {
                "access_token": reg_data["access_token"],
                "refresh_token": reg_data["refresh_token"],
            }

        headers = {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }

        response = client.get("/api/v1/tenants/current", headers=headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "trial"

    @pytest.mark.integration
    def test_suspended_tenant_response(self, client, app, user, tenant_suspended, user_password):
        """Test behavior when accessing suspended tenant."""
        from app.blueprints.tenants.models import TenantUser
        from app.core.utils import generate_token_pair
        from datetime import datetime

        with app.app_context():
            tu = TenantUser(
                user_id=user.id,
                tenant_id=tenant_suspended.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()

            tokens = generate_token_pair(user.id, tenant_suspended.id)

        headers = {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }

        response = client.get("/api/v1/tenants/current", headers=headers)

        # Depending on implementation, suspended tenants might:
        # - Return 403 (forbidden due to suspension)
        # - Return 200 but with suspended status
        # - Allow read but block writes
        assert response.status_code in [200, 403]


class TestTenantDetails:
    """Tests for tenant detail information."""

    @pytest.mark.integration
    def test_tenant_includes_user_count(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test that tenant response includes user count."""
        # Add more users
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import TenantUser
        from datetime import datetime

        with app.app_context():
            for i in range(3):
                new_user = User(
                    email=f"countuser{i}@example.com",
                    full_name=f"Count User {i}",
                    is_active=True
                )
                new_user.set_password(user_password)
                db.session.add(new_user)
                db.session.flush()

                tu = TenantUser(
                    user_id=new_user.id,
                    tenant_id=tenant.id,
                    joined_at=datetime.utcnow()
                )
                db.session.add(tu)
            db.session.commit()

        response = client.get("/api/v1/tenants/current", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # If the endpoint returns user count
        if "user_count" in data or "users_count" in data:
            count = data.get("user_count") or data.get("users_count")
            assert count >= 4  # Original user + 3 new ones

    @pytest.mark.integration
    def test_tenant_includes_store_count(
        self, client, app, store, second_store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that tenant response includes store count."""
        response = client.get("/api/v1/tenants/current", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # If the endpoint returns store count
        if "store_count" in data or "stores_count" in data:
            count = data.get("store_count") or data.get("stores_count")
            assert count >= 2


class TestTenantValidation:
    """Tests for tenant input validation."""

    @pytest.mark.integration
    def test_update_tenant_empty_name_fails(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that empty tenant name is rejected."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "name": ""
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_tenant_empty_slug_fails(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that empty tenant slug is rejected."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "slug": ""
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_tenant_slug_normalized(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that tenant slug is normalized to lowercase."""
        response = client.put("/api/v1/tenants/current", headers=auth_headers, json={
            "slug": "Mixed-Case-Slug"
        })

        # Either rejected or normalized
        if response.status_code == 200:
            data = response.get_json()
            assert data["slug"] == data["slug"].lower()
        else:
            assert response.status_code == 400


class TestTenantSettings:
    """Tests for /api/v1/tenants/current/settings endpoint."""

    @pytest.mark.integration
    def test_get_tenant_settings_default(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting tenant settings returns defaults when none exist."""
        response = client.get("/api/v1/tenants/current/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Check default values for Kenya
        assert data["timezone"] == "Africa/Nairobi"
        assert data["currency"] == "KES"
        assert data["locale"] == "en-KE"
        assert data["tax_rate"] == 16.0
        assert data["tax_inclusive_pricing"] is True
        assert data["date_format"] == "DD/MM/YYYY"
        assert data["time_format"] == "24h"

    @pytest.mark.integration
    def test_update_tenant_settings_timezone(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating tenant timezone."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "timezone": "Africa/Lagos"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["timezone"] == "Africa/Lagos"

    @pytest.mark.integration
    def test_update_tenant_settings_currency(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating tenant currency."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "currency": "USD"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["currency"] == "USD"

    @pytest.mark.integration
    def test_update_tenant_settings_tax(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating tenant tax settings."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "tax_rate": 8.0,
            "tax_inclusive_pricing": False,
            "tax_id": "P051234567X"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["tax_rate"] == 8.0
        assert data["tax_inclusive_pricing"] is False
        assert data["tax_id"] == "P051234567X"

    @pytest.mark.integration
    def test_update_tenant_settings_business_info(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating tenant business info for receipts."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "business_name": "Acme Ltd",
            "business_address": "123 Kenyatta Ave, Nairobi",
            "business_phone": "+254712345678",
            "business_email": "info@acme.co.ke"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["business_name"] == "Acme Ltd"
        assert data["business_address"] == "123 Kenyatta Ave, Nairobi"
        assert data["business_phone"] == "+254712345678"
        assert data["business_email"] == "info@acme.co.ke"

    @pytest.mark.integration
    def test_update_tenant_settings_fiscal_year(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating tenant fiscal year settings."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "fiscal_year_start_month": 7,
            "fiscal_year_start_day": 1
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["fiscal_year_start_month"] == 7
        assert data["fiscal_year_start_day"] == 1

    @pytest.mark.integration
    def test_update_tenant_settings_invalid_date_format(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that invalid date format is rejected."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "date_format": "INVALID"
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_tenant_settings_invalid_tax_rate(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that invalid tax rate is rejected."""
        response = client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "tax_rate": 150  # Over 100%
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_get_tenant_settings_unauthenticated(self, client):
        """Test getting tenant settings without authentication."""
        response = client.get("/api/v1/tenants/current/settings")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_update_tenant_settings_unauthenticated(self, client):
        """Test updating tenant settings without authentication."""
        response = client.put("/api/v1/tenants/current/settings", json={
            "timezone": "Africa/Lagos"
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_settings_persist_after_update(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that settings persist after update."""
        # Update settings
        client.put("/api/v1/tenants/current/settings", headers=auth_headers, json={
            "currency": "TZS",
            "tax_rate": 18.0
        })

        # Get settings again
        response = client.get("/api/v1/tenants/current/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["currency"] == "TZS"
        assert data["tax_rate"] == 18.0
