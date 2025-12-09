"""
Authentication tests.

Tests for:
- User login
- User registration
- Token refresh
- Bootstrap (first user creation)
- JWT token validation
"""

import pytest
from uuid import uuid4

from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.core.utils import decode_token, generate_token_pair


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    @pytest.mark.auth
    def test_login_success(self, client, user, tenant, tenant_user, user_password):
        """Test successful login with valid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": user_password,
            "tenant_id": str(tenant.id)
        })

        assert response.status_code == 200
        data = response.get_json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert "tenant" in data
        assert data["user"]["email"] == user.email
        assert data["tenant"]["id"] == str(tenant.id)

    @pytest.mark.auth
    def test_login_invalid_password(self, client, user, tenant, tenant_user):
        """Test login with wrong password."""
        response = client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": "wrong-password",
            "tenant_id": str(tenant.id)
        })

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data or "message" in data

    @pytest.mark.auth
    def test_login_invalid_email(self, client, tenant, user_password):
        """Test login with non-existent email."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": user_password,
            "tenant_id": str(tenant.id)
        })

        assert response.status_code == 401

    @pytest.mark.auth
    def test_login_inactive_user(self, client, inactive_user, tenant, user_password, app):
        """Test login with inactive user account."""
        # Create tenant membership for inactive user
        with app.app_context():
            tenant_user = TenantUser(
                user_id=inactive_user.id,
                tenant_id=tenant.id
            )
            db.session.add(tenant_user)
            db.session.commit()

        response = client.post("/api/v1/auth/login", json={
            "email": inactive_user.email,
            "password": user_password,
            "tenant_id": str(tenant.id)
        })

        assert response.status_code == 401

    @pytest.mark.auth
    def test_login_user_not_in_tenant(self, client, user, second_tenant, user_password):
        """Test login when user is not member of the specified tenant."""
        response = client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": user_password,
            "tenant_id": str(second_tenant.id)
        })

        # Should fail - user not in this tenant
        assert response.status_code == 403

    @pytest.mark.auth
    def test_login_nonexistent_tenant(self, client, user, tenant_user, user_password):
        """Test login with non-existent tenant ID."""
        response = client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": user_password,
            "tenant_id": str(uuid4())
        })

        assert response.status_code == 404

    @pytest.mark.auth
    def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
            # Missing password and tenant_id
        })

        assert response.status_code == 400

    @pytest.mark.auth
    def test_login_invalid_email_format(self, client, tenant):
        """Test login with invalid email format."""
        response = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123",
            "tenant_id": str(tenant.id)
        })

        assert response.status_code == 400


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    @pytest.mark.auth
    def test_register_success(self, client, app):
        """Test successful registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
            "tenant_name": "New Company",
            "tenant_slug": "new-company"
        })

        assert response.status_code == 201
        data = response.get_json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["tenant"]["slug"] == "new-company"

        # Verify database records created
        with app.app_context():
            user = User.query.filter_by(email="newuser@example.com").first()
            assert user is not None
            assert user.is_active is True

            tenant = Tenant.query.filter_by(slug="new-company").first()
            assert tenant is not None
            assert tenant.status == TenantStatus.TRIAL

    @pytest.mark.auth
    def test_register_duplicate_email(self, client, user):
        """Test registration with existing email."""
        response = client.post("/api/v1/auth/register", json={
            "email": user.email,  # Already exists
            "password": "SecurePass123!",
            "full_name": "Another User",
            "tenant_name": "Another Company",
            "tenant_slug": "another-company"
        })

        assert response.status_code == 409

    @pytest.mark.auth
    def test_register_duplicate_tenant_slug(self, client, tenant):
        """Test registration with existing tenant slug."""
        response = client.post("/api/v1/auth/register", json={
            "email": "unique@example.com",
            "password": "SecurePass123!",
            "full_name": "Unique User",
            "tenant_name": "Unique Company",
            "tenant_slug": tenant.slug  # Already exists
        })

        assert response.status_code == 409

    @pytest.mark.auth
    def test_register_short_password(self, client):
        """Test registration with too short password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "password": "short",  # Less than 8 chars
            "full_name": "Short Pass User",
            "tenant_name": "Short Pass Company",
            "tenant_slug": "short-pass"
        })

        assert response.status_code == 400

    @pytest.mark.auth
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post("/api/v1/auth/register", json={
            "email": "incomplete@example.com"
            # Missing all other fields
        })

        assert response.status_code == 400


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh"""

    @pytest.mark.auth
    def test_refresh_success(self, client, auth_tokens):
        """Test successful token refresh."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": auth_tokens["refresh_token"]
        })

        assert response.status_code == 200
        data = response.get_json()

        assert "access_token" in data
        assert "refresh_token" in data
        # Tokens are returned (may be same if generated in same second due to iat)

    @pytest.mark.auth
    def test_refresh_with_access_token(self, client, auth_tokens):
        """Test refresh using access token (should fail)."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": auth_tokens["access_token"]  # Wrong token type
        })

        assert response.status_code == 401

    @pytest.mark.auth
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })

        assert response.status_code == 401

    @pytest.mark.auth
    def test_refresh_missing_token(self, client):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 400

    @pytest.mark.auth
    def test_refresh_deactivated_user(self, client, app, user, tenant, tenant_user):
        """Test refresh when user has been deactivated."""
        with app.app_context():
            # Generate tokens while user is active
            tokens = generate_token_pair(user.id, tenant.id)

            # Deactivate user
            user_obj = db.session.get(User, user.id)
            user_obj.is_active = False
            db.session.commit()

        # Try to refresh
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"]
        })

        assert response.status_code == 401


class TestBootstrap:
    """Tests for POST /api/v1/auth/bootstrap"""

    @pytest.mark.auth
    def test_bootstrap_success(self, client, app):
        """Test successful bootstrap on empty database."""
        response = client.post("/api/v1/auth/bootstrap", json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
            "full_name": "Admin User",
            "tenant_name": "First Company",
            "tenant_slug": "first-company"
        })

        assert response.status_code == 201
        data = response.get_json()

        assert "access_token" in data
        assert data["user"]["email"] == "admin@example.com"

    @pytest.mark.auth
    def test_bootstrap_already_bootstrapped(self, client, user):
        """Test bootstrap when users already exist."""
        response = client.post("/api/v1/auth/bootstrap", json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
            "full_name": "Admin User",
            "tenant_name": "First Company",
            "tenant_slug": "first-company"
        })

        # Should fail - system already has users
        assert response.status_code == 400


class TestJWTTokens:
    """Tests for JWT token generation and validation."""

    @pytest.mark.auth
    @pytest.mark.unit
    def test_token_contains_required_claims(self, app, user, tenant, tenant_user):
        """Test that generated tokens contain required claims."""
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)

            # Decode access token
            payload = decode_token(tokens["access_token"])

            assert "user_id" in payload
            assert "tenant_id" in payload
            assert "type" in payload
            assert payload["type"] == "access"
            assert payload["user_id"] == str(user.id)
            assert payload["tenant_id"] == str(tenant.id)

    @pytest.mark.auth
    @pytest.mark.unit
    def test_refresh_token_type(self, app, user, tenant, tenant_user):
        """Test that refresh token has correct type claim."""
        with app.app_context():
            tokens = generate_token_pair(user.id, tenant.id)

            payload = decode_token(tokens["refresh_token"])
            assert payload["type"] == "refresh"

    @pytest.mark.auth
    def test_access_token_authenticates_request(self, client, auth_headers):
        """Test that access token allows authenticated requests."""
        # Try accessing a protected endpoint
        response = client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.auth
    def test_missing_auth_header_rejected(self, client):
        """Test that requests without auth header are rejected."""
        response = client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.auth
    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        headers = {
            "Authorization": "Bearer invalid.token.here",
            "Content-Type": "application/json"
        }
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    @pytest.mark.auth
    def test_malformed_auth_header_rejected(self, client):
        """Test that malformed auth headers are rejected."""
        headers = {
            "Authorization": "NotBearer token",
            "Content-Type": "application/json"
        }
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401
