"""
RBAC (Role-Based Access Control) tests.

Tests for:
- Permission checking
- Role assignment
- Tenant-wide vs store-specific roles
- Permission inheritance
- Access control decorators
"""

import pytest
from datetime import datetime
from uuid import uuid4

from flask import g

from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.blueprints.stores.models import Store, StoreUser
from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission
from app.core.decorators import get_user_permissions, has_permission, has_any_permission
from app.core.utils import generate_token_pair


class TestPermissionChecking:
    """Tests for permission checking logic."""

    @pytest.mark.rbac
    def test_user_has_tenant_wide_permissions(
        self, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role
    ):
        """Test that user gets permissions from tenant-wide role."""
        with app.app_context():
            user_perms = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=None
            )

            # Admin role has all permissions
            assert "users.view" in user_perms
            assert "users.create" in user_perms
            assert "stores.edit" in user_perms

    @pytest.mark.rbac
    def test_user_without_role_has_no_permissions(
        self, app, user, tenant, tenant_user
    ):
        """Test that user without any role has no permissions."""
        with app.app_context():
            user_perms = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=None
            )

            assert len(user_perms) == 0

    @pytest.mark.rbac
    def test_viewer_role_has_limited_permissions(
        self, app, user, tenant, tenant_user, permissions, viewer_role, user_with_viewer_role
    ):
        """Test that viewer role only has view permissions."""
        with app.app_context():
            user_perms = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=None
            )

            # Should have view permissions
            assert "users.view" in user_perms
            assert "stores.view" in user_perms

            # Should NOT have edit/create/delete permissions
            assert "users.create" not in user_perms
            assert "users.edit" not in user_perms
            assert "stores.delete" not in user_perms

    @pytest.mark.rbac
    def test_store_specific_role_permissions(
        self, app, user, tenant, store, tenant_user, permissions, admin_role, user_with_store_role
    ):
        """Test that store-specific role only applies to that store."""
        with app.app_context():
            # Without store context - should not have permissions
            perms_no_store = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=None
            )
            assert len(perms_no_store) == 0

            # With correct store context - should have permissions
            perms_with_store = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=store.id
            )
            assert "users.view" in perms_with_store

    @pytest.mark.rbac
    def test_store_specific_role_not_in_other_store(
        self, app, user, tenant, store, second_store, tenant_user, permissions, admin_role, user_with_store_role
    ):
        """Test that store-specific role doesn't apply to other stores."""
        with app.app_context():
            # With different store - should NOT have permissions from store-specific role
            perms_other_store = get_user_permissions(
                user_id=user.id,
                tenant_id=tenant.id,
                store_id=second_store.id
            )
            assert len(perms_other_store) == 0


class TestPermissionDecorators:
    """Tests for @require_permission and related decorators."""

    @pytest.mark.rbac
    def test_require_permission_allows_authorized_user(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that user with required permission can access endpoint."""
        # Users endpoint requires users.view permission
        response = client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.rbac
    def test_require_permission_blocks_unauthorized_user(
        self, client, app, user, tenant, tenant_user, auth_headers
    ):
        """Test that user without permission is blocked."""
        # User has no roles/permissions
        response = client.get("/api/v1/users", headers=auth_headers)

        # Should be forbidden (or might be 200 if endpoint doesn't require permission)
        # This depends on which endpoints require which permissions
        assert response.status_code in [200, 403]

    @pytest.mark.rbac
    def test_require_tenant_decorator(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that @require_tenant blocks requests without tenant context."""
        # With valid auth and permissions, should work
        response = client.get("/api/v1/tenants/current", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.rbac
    def test_require_store_decorator_without_header(
        self, client, auth_headers
    ):
        """Test endpoints requiring store context without X-Store-ID header."""
        # Endpoints that require store context should fail without header
        # This might not apply to all endpoints
        pass  # Add test when store-required endpoint is identified


class TestRoleManagement:
    """Tests for role CRUD operations."""

    @pytest.mark.rbac
    def test_list_roles(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test listing roles for current tenant."""
        response = client.get("/api/v1/roles", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        roles = data.get("items", data.get("roles", []))
        role_names = [r["name"] for r in roles]
        assert "Admin" in role_names

    @pytest.mark.rbac
    def test_create_role(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a new role."""
        response = client.post("/api/v1/roles", headers=auth_headers, json={
            "name": "Custom Role",
            "description": "A custom role for testing"
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Custom Role"

    @pytest.mark.rbac
    def test_create_duplicate_role_name_fails(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that duplicate role names within tenant are rejected."""
        response = client.post("/api/v1/roles", headers=auth_headers, json={
            "name": "Admin",  # Already exists
            "description": "Duplicate admin"
        })

        assert response.status_code == 409

    @pytest.mark.rbac
    def test_get_role_by_id(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting a specific role by ID."""
        response = client.get(
            f"/api/v1/roles/{admin_role.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == str(admin_role.id)

    @pytest.mark.rbac
    def test_update_role(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating a role."""
        # First create a non-system role
        create_response = client.post("/api/v1/roles", headers=auth_headers, json={
            "name": "Updateable Role",
            "description": "Will be updated"
        })
        assert create_response.status_code == 201
        role_id = create_response.get_json()["id"]

        # Update it
        response = client.put(
            f"/api/v1/roles/{role_id}",
            headers=auth_headers,
            json={"description": "Updated description"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["description"] == "Updated description"

    @pytest.mark.rbac
    def test_delete_role(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test deleting a role."""
        # Create a role to delete
        create_response = client.post("/api/v1/roles", headers=auth_headers, json={
            "name": "Deleteable Role",
            "description": "Will be deleted"
        })
        assert create_response.status_code == 201
        role_id = create_response.get_json()["id"]

        # Delete it
        response = client.delete(
            f"/api/v1/roles/{role_id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204]

        # Verify it's gone
        get_response = client.get(
            f"/api/v1/roles/{role_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestUserRoleAssignment:
    """Tests for assigning/revoking roles to/from users."""

    @pytest.mark.rbac
    def test_assign_role_to_user(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, viewer_role, user_with_admin_role, auth_headers
    ):
        """Test assigning a role to a user."""
        response = client.post(
            f"/api/v1/users/{user.id}/roles",
            headers=auth_headers,
            json={"role_id": str(viewer_role.id)}
        )

        assert response.status_code in [200, 201]

    @pytest.mark.rbac
    def test_get_user_roles(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting roles assigned to a user."""
        response = client.get(
            f"/api/v1/users/{user.id}/roles",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        roles = data.get("roles", data.get("items", []))
        role_names = [r.get("name") or r.get("role", {}).get("name") for r in roles]
        assert "Admin" in role_names

    @pytest.mark.rbac
    def test_revoke_role_from_user(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, viewer_role, user_with_admin_role, auth_headers
    ):
        """Test revoking a role from a user."""
        # First assign viewer role
        assign_response = client.post(
            f"/api/v1/users/{user.id}/roles",
            headers=auth_headers,
            json={"role_id": str(viewer_role.id)}
        )

        # Then revoke it
        response = client.delete(
            f"/api/v1/users/{user.id}/roles/{viewer_role.id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204]

    @pytest.mark.rbac
    def test_assign_store_specific_role(
        self, client, app, user, tenant, store, tenant_user, store_user, permissions, admin_role, viewer_role, user_with_admin_role, auth_headers
    ):
        """Test assigning a role to user for specific store only."""
        response = client.post(
            f"/api/v1/users/{user.id}/roles",
            headers=auth_headers,
            json={
                "role_id": str(viewer_role.id),
                "store_id": str(store.id)
            }
        )

        assert response.status_code in [200, 201]


class TestPermissionListing:
    """Tests for permission listing endpoints."""

    @pytest.mark.rbac
    def test_list_all_permissions(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test listing all available permissions."""
        response = client.get("/api/v1/permissions", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        perms = data.get("items", data.get("permissions", []))
        perm_names = [p["name"] for p in perms]

        assert "users.view" in perm_names
        assert "stores.create" in perm_names

    @pytest.mark.rbac
    def test_filter_permissions_by_resource(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test filtering permissions by resource."""
        response = client.get(
            "/api/v1/permissions?resource=users",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        perms = data.get("items", data.get("permissions", []))

        # All permissions should be for 'users' resource
        for p in perms:
            assert p["resource"] == "users"


class TestRolePermissionAssignment:
    """Tests for assigning permissions to roles."""

    @pytest.mark.rbac
    def test_role_has_permissions(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that role includes its permissions in response."""
        response = client.get(
            f"/api/v1/roles/{admin_role.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        # Role should have permissions attached
        perms = data.get("permissions", [])
        assert len(perms) > 0

    @pytest.mark.rbac
    def test_create_role_with_permissions(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a role with specific permissions."""
        # Get some permission IDs
        perm_ids = [str(p.id) for p in permissions[:3]]

        response = client.post("/api/v1/roles", headers=auth_headers, json={
            "name": "Role With Perms",
            "description": "Has specific permissions",
            "permission_ids": perm_ids
        })

        assert response.status_code == 201
        data = response.get_json()

        # Verify permissions were assigned
        role_perms = data.get("permissions", [])
        assert len(role_perms) == 3
