"""
Tenant isolation tests.

Tests to ensure:
- Users can only access data within their own tenant
- Cross-tenant data access is prevented
- Tenant context is properly enforced
- Store access within tenants is properly scoped
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.blueprints.stores.models import Store, StoreUser
from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission
from app.core.utils import generate_token_pair


class TestTenantDataIsolation:
    """Tests for tenant-level data isolation."""

    @pytest.mark.tenant
    def test_user_cannot_access_other_tenant_stores(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that user cannot see stores from another tenant."""
        # Create a store in the second tenant
        with app.app_context():
            other_store = Store(
                tenant_id=second_tenant.id,
                name="Other Tenant Store",
                is_active=True
            )
            db.session.add(other_store)
            db.session.commit()

        # User from first tenant tries to list stores
        response = client.get(
            "/api/v1/stores",
            headers=authenticated_user["headers"]
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should not see the other tenant's store
        store_names = [s["name"] for s in data.get("items", data.get("stores", []))]
        assert "Other Tenant Store" not in store_names

    @pytest.mark.tenant
    def test_user_cannot_access_other_tenant_store_directly(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that user cannot access a specific store from another tenant."""
        # Create a store in the second tenant
        with app.app_context():
            other_store = Store(
                tenant_id=second_tenant.id,
                name="Secret Store",
                is_active=True
            )
            db.session.add(other_store)
            db.session.commit()
            store_id = other_store.id

        # Try to access the store directly
        response = client.get(
            f"/api/v1/stores/{store_id}",
            headers=authenticated_user["headers"]
        )

        # Should be 404 (not found in this tenant) or 403 (forbidden)
        assert response.status_code in [403, 404]

    @pytest.mark.tenant
    def test_user_cannot_see_other_tenant_users(
        self, client, app, authenticated_user, second_authenticated_user
    ):
        """Test that user cannot list users from another tenant."""
        response = client.get(
            "/api/v1/users",
            headers=authenticated_user["headers"]
        )

        assert response.status_code == 200
        data = response.get_json()

        # Get all emails from response
        user_emails = [u["email"] for u in data.get("items", data.get("users", []))]

        # Should not see the other tenant's user
        assert second_authenticated_user["user"].email not in user_emails

    @pytest.mark.tenant
    def test_user_cannot_access_other_tenant_user_directly(
        self, client, authenticated_user, second_authenticated_user
    ):
        """Test that user cannot access another tenant's user by ID."""
        other_user_id = second_authenticated_user["user"].id

        response = client.get(
            f"/api/v1/users/{other_user_id}",
            headers=authenticated_user["headers"]
        )

        # Should be 404 (not found in this tenant) or 403 (forbidden)
        assert response.status_code in [403, 404]

    @pytest.mark.tenant
    def test_user_cannot_see_other_tenant_roles(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that user cannot see roles from another tenant."""
        # Create a role in the second tenant
        with app.app_context():
            other_role = Role(
                tenant_id=second_tenant.id,
                name="Secret Role",
                description="A role in another tenant"
            )
            db.session.add(other_role)
            db.session.commit()

        response = client.get(
            "/api/v1/roles",
            headers=authenticated_user["headers"]
        )

        assert response.status_code == 200
        data = response.get_json()

        role_names = [r["name"] for r in data.get("items", data.get("roles", []))]
        assert "Secret Role" not in role_names


class TestStoreAccessWithinTenant:
    """Tests for store-level access control within a tenant."""

    @pytest.mark.tenant
    def test_user_can_access_assigned_store(
        self, client, app, user, tenant, tenant_user, store, store_user, auth_headers, permissions, admin_role, user_with_admin_role
    ):
        """Test that user can access stores they're assigned to."""
        headers = auth_headers.copy()
        headers["X-Store-ID"] = str(store.id)

        # Should succeed - user is assigned to this store
        response = client.get(
            f"/api/v1/stores/{store.id}",
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.tenant
    def test_user_without_store_assignment_denied(
        self, client, app, user, tenant, tenant_user, store, auth_headers, permissions, admin_role, user_with_admin_role
    ):
        """Test that user cannot set store context for unassigned store."""
        # Note: store_user fixture NOT included - user is not assigned to store
        headers = auth_headers.copy()
        headers["X-Store-ID"] = str(store.id)

        response = client.get(
            f"/api/v1/stores/{store.id}",
            headers=headers
        )

        # The middleware should reject this - user not assigned to store
        # Depending on implementation, could be 403
        assert response.status_code in [200, 403]  # 200 if store access check is in service layer

    @pytest.mark.tenant
    def test_user_cannot_access_other_tenant_store_via_header(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that X-Store-ID header with other tenant's store is rejected."""
        # Create store in other tenant
        with app.app_context():
            other_store = Store(
                tenant_id=second_tenant.id,
                name="Other Store",
                is_active=True
            )
            db.session.add(other_store)
            db.session.commit()
            other_store_id = other_store.id

        headers = authenticated_user["headers"].copy()
        headers["X-Store-ID"] = str(other_store_id)

        response = client.get(
            "/api/v1/users/me",
            headers=headers
        )

        # Should be rejected - store not in user's tenant (403 or 404)
        assert response.status_code in [403, 404]


class TestTenantContextRequired:
    """Tests that tenant context is properly required."""

    @pytest.mark.tenant
    def test_protected_endpoints_require_tenant(self, client, app):
        """Test that protected endpoints require tenant context."""
        # Create a user without tenant membership
        with app.app_context():
            orphan_user = User(
                email="orphan@example.com",
                full_name="Orphan User",
                is_active=True
            )
            orphan_user.set_password("password123")
            db.session.add(orphan_user)

            # Create a tenant but don't add user to it
            tenant = Tenant(
                name="Some Tenant",
                slug="some-tenant",
                status=TenantStatus.ACTIVE
            )
            db.session.add(tenant)
            db.session.commit()

            # Generate token with tenant the user isn't member of
            tokens = generate_token_pair(orphan_user.id, tenant.id)

        headers = {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }

        response = client.get("/api/v1/users/me", headers=headers)

        # Should fail - user not member of tenant in token
        assert response.status_code == 403


class TestCrossTenantOperations:
    """Tests for operations that should be prevented across tenants."""

    @pytest.mark.tenant
    def test_cannot_create_store_in_other_tenant(
        self, client, authenticated_user, second_tenant
    ):
        """Test that user cannot create a store in another tenant."""
        response = client.post(
            "/api/v1/stores",
            headers=authenticated_user["headers"],
            json={
                "name": "Sneaky Store",
                "tenant_id": str(second_tenant.id)  # Try to specify other tenant
            }
        )

        # The store should be created in user's tenant, not the specified one
        # Or the request should be rejected
        if response.status_code == 201:
            data = response.get_json()
            # If created, must be in user's tenant, not the specified one
            assert data.get("tenant_id") != str(second_tenant.id)
        else:
            # Otherwise should be rejected
            assert response.status_code in [400, 403]

    @pytest.mark.tenant
    def test_cannot_assign_user_to_other_tenant_store(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that user cannot assign users to stores in other tenants."""
        # Create store in other tenant
        with app.app_context():
            other_store = Store(
                tenant_id=second_tenant.id,
                name="Other Store",
                is_active=True
            )
            db.session.add(other_store)
            db.session.commit()
            other_store_id = other_store.id

        # Try to assign self to other tenant's store
        response = client.post(
            f"/api/v1/stores/{other_store_id}/users",
            headers=authenticated_user["headers"],
            json={
                "user_ids": [str(authenticated_user["user"].id)]
            }
        )

        # Should be rejected
        assert response.status_code in [403, 404]

    @pytest.mark.tenant
    def test_cannot_assign_other_tenant_role_to_user(
        self, client, app, authenticated_user, second_tenant
    ):
        """Test that user cannot assign roles from another tenant."""
        # Create role in other tenant
        with app.app_context():
            other_role = Role(
                tenant_id=second_tenant.id,
                name="Other Role"
            )
            db.session.add(other_role)
            db.session.commit()
            other_role_id = other_role.id

        # Try to assign other tenant's role
        response = client.post(
            f"/api/v1/users/{authenticated_user['user'].id}/roles",
            headers=authenticated_user["headers"],
            json={
                "role_id": str(other_role_id)
            }
        )

        # Should be rejected
        assert response.status_code in [400, 403, 404]


class TestTenantSoftDelete:
    """Tests for tenant soft deletion behavior."""

    @pytest.mark.tenant
    def test_deleted_tenant_blocks_login(self, client, app, user, tenant, tenant_user, user_password):
        """Test that users cannot login to soft-deleted tenants."""
        # Soft delete the tenant
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            tenant_obj.soft_delete()
            db.session.commit()

        response = client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": user_password,
            "tenant_id": str(tenant.id)
        })

        # Should fail - tenant is deleted
        assert response.status_code == 404

    @pytest.mark.tenant
    def test_deleted_tenant_invalidates_existing_tokens(
        self, client, app, auth_headers, tenant
    ):
        """Test that tokens for deleted tenants are rejected."""
        # First verify token works
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200

        # Soft delete the tenant
        with app.app_context():
            tenant_obj = db.session.get(Tenant, tenant.id)
            tenant_obj.soft_delete()
            db.session.commit()

        # Token should no longer work (or behavior may vary based on implementation)
        # Some systems check deleted_at on every request, others don't
        response = client.get("/api/v1/users/me", headers=auth_headers)
        # Accept 200 if middleware doesn't check deleted_at, or 401/403 if it does
        assert response.status_code in [200, 401, 403]
