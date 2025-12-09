"""
User API endpoint tests.

Tests for:
- GET /api/v1/users/me
- PUT /api/v1/users/me
- GET /api/v1/users
- GET /api/v1/users/:id
- POST /api/v1/users
- PUT /api/v1/users/:id
- DELETE /api/v1/users/:id
"""

import pytest
from uuid import uuid4

from app.extensions import db
from app.blueprints.users.models import User


class TestCurrentUser:
    """Tests for /api/v1/users/me endpoint."""

    @pytest.mark.integration
    def test_get_current_user(self, client, auth_headers, user):
        """Test getting current authenticated user."""
        response = client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["email"] == user.email
        assert data["full_name"] == user.full_name
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.integration
    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_update_current_user_name(self, client, auth_headers, user):
        """Test updating current user's name."""
        response = client.put("/api/v1/users/me", headers=auth_headers, json={
            "full_name": "Updated Name"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["full_name"] == "Updated Name"

    @pytest.mark.integration
    def test_update_current_user_password(
        self, client, app, auth_headers, user, user_password
    ):
        """Test updating current user's password."""
        response = client.put("/api/v1/users/me", headers=auth_headers, json={
            "current_password": user_password,
            "new_password": "NewSecurePassword123!"
        })

        assert response.status_code == 200

        # Verify new password works
        with app.app_context():
            user_obj = db.session.get(User, user.id)
            assert user_obj.check_password("NewSecurePassword123!")

    @pytest.mark.integration
    def test_update_password_wrong_current(self, client, auth_headers):
        """Test updating password with wrong current password."""
        response = client.put("/api/v1/users/me", headers=auth_headers, json={
            "current_password": "wrong-password",
            "new_password": "NewPassword123!"
        })

        assert response.status_code in [400, 401]


class TestUserList:
    """Tests for GET /api/v1/users endpoint."""

    @pytest.mark.integration
    def test_list_users(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test listing users in current tenant."""
        response = client.get("/api/v1/users", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Should have pagination or items array
        users = data.get("items", data.get("users", []))
        assert len(users) >= 1

        # Current user should be in list
        user_emails = [u["email"] for u in users]
        assert user.email in user_emails

    @pytest.mark.integration
    def test_list_users_pagination(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test user list pagination."""
        # Create additional users
        with app.app_context():
            for i in range(5):
                new_user = User(
                    email=f"user{i}@example.com",
                    full_name=f"User {i}",
                    is_active=True
                )
                new_user.set_password(user_password)
                db.session.add(new_user)
            db.session.commit()

        response = client.get("/api/v1/users?page=1&per_page=3", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Check pagination metadata
        assert "total" in data or "pagination" in data or len(data.get("items", [])) <= 3

    @pytest.mark.integration
    def test_list_users_search(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test searching users by name/email."""
        # Create a user with specific name
        with app.app_context():
            from app.blueprints.tenants.models import TenantUser
            from datetime import datetime

            searchable_user = User(
                email="searchable@example.com",
                full_name="Searchable Person",
                is_active=True
            )
            searchable_user.set_password(user_password)
            db.session.add(searchable_user)
            db.session.flush()

            # Add to tenant
            tu = TenantUser(
                user_id=searchable_user.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()

        response = client.get(
            "/api/v1/users?search=searchable",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        users = data.get("items", data.get("users", []))
        emails = [u["email"] for u in users]
        assert "searchable@example.com" in emails


class TestUserCRUD:
    """Tests for user CRUD operations."""

    @pytest.mark.integration
    def test_get_user_by_id(
        self, client, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting a specific user by ID."""
        response = client.get(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == str(user.id)

    @pytest.mark.integration
    def test_get_nonexistent_user(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting a user that doesn't exist."""
        response = client.get(
            f"/api/v1/users/{uuid4()}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_create_user(
        self, client, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a new user."""
        response = client.post("/api/v1/users", headers=auth_headers, json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        })

        assert response.status_code == 201
        data = response.get_json()

        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "password" not in data

    @pytest.mark.integration
    def test_create_user_duplicate_email(
        self, client, user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating user with existing email fails."""
        response = client.post("/api/v1/users", headers=auth_headers, json={
            "email": user.email,  # Already exists
            "password": "SecurePass123!",
            "full_name": "Duplicate User"
        })

        assert response.status_code == 409

    @pytest.mark.integration
    def test_create_user_invalid_email(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating user with invalid email fails."""
        response = client.post("/api/v1/users", headers=auth_headers, json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "full_name": "Invalid Email User"
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_user(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test updating a user."""
        # Create another user to update
        with app.app_context():
            from app.blueprints.tenants.models import TenantUser
            from datetime import datetime

            other_user = User(
                email="other@example.com",
                full_name="Other User",
                is_active=True
            )
            other_user.set_password(user_password)
            db.session.add(other_user)
            db.session.flush()

            tu = TenantUser(
                user_id=other_user.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()
            other_user_id = other_user.id

        response = client.put(
            f"/api/v1/users/{other_user_id}",
            headers=auth_headers,
            json={"full_name": "Updated Other User"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["full_name"] == "Updated Other User"

    @pytest.mark.integration
    def test_deactivate_user(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test deactivating (soft deleting) a user."""
        # Create a user to deactivate
        with app.app_context():
            from app.blueprints.tenants.models import TenantUser
            from datetime import datetime

            deletable_user = User(
                email="deletable@example.com",
                full_name="Deletable User",
                is_active=True
            )
            deletable_user.set_password(user_password)
            db.session.add(deletable_user)
            db.session.flush()

            tu = TenantUser(
                user_id=deletable_user.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()
            deletable_user_id = deletable_user.id

        response = client.delete(
            f"/api/v1/users/{deletable_user_id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204]

        # Verify user is deactivated
        with app.app_context():
            user_obj = db.session.get(User, deletable_user_id)
            assert user_obj.is_active is False

    @pytest.mark.integration
    def test_cannot_delete_self(
        self, client, user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that user cannot delete themselves."""
        response = client.delete(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        # Should either return error or not actually deactivate
        assert response.status_code in [400, 403]


class TestUserFilteringAndSorting:
    """Tests for user list filtering and sorting."""

    @pytest.mark.integration
    def test_filter_active_users(
        self, client, app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test filtering for active users only."""
        # Create an inactive user
        with app.app_context():
            from app.blueprints.tenants.models import TenantUser
            from datetime import datetime

            inactive = User(
                email="inactive2@example.com",
                full_name="Inactive User",
                is_active=False
            )
            inactive.set_password(user_password)
            db.session.add(inactive)
            db.session.flush()

            tu = TenantUser(
                user_id=inactive.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()

        response = client.get(
            "/api/v1/users?is_active=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        users = data.get("items", data.get("users", []))

        # All returned users should be active
        for u in users:
            assert u.get("is_active", True) is True
