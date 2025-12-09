"""
Pytest fixtures for testing the multi-tenant SaaS backend.

Provides:
- Flask app and test client
- Database setup/teardown
- User, tenant, store fixtures
- Authentication helpers
- RBAC fixtures (roles, permissions)
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.blueprints.users.models import User
from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
from app.blueprints.stores.models import Store, StoreUser
from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission
from app.core.utils import generate_token_pair


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def app():
    """Create application instance for testing."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """Provide database session for tests."""
    with app.app_context():
        yield db.session


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
def user_password():
    """Default password for test users."""
    return "TestPassword123!"


@pytest.fixture
def user(app, user_password):
    """Create a basic test user."""
    with app.app_context():
        user = User(
            email="testuser@example.com",
            full_name="Test User",
            is_active=True
        )
        user.set_password(user_password)
        db.session.add(user)
        db.session.commit()

        # Refresh to get ID
        db.session.refresh(user)
        yield user


@pytest.fixture
def inactive_user(app, user_password):
    """Create an inactive user."""
    with app.app_context():
        user = User(
            email="inactive@example.com",
            full_name="Inactive User",
            is_active=False
        )
        user.set_password(user_password)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


# =============================================================================
# Tenant Fixtures
# =============================================================================

@pytest.fixture
def tenant(app):
    """Create a basic test tenant."""
    with app.app_context():
        tenant = Tenant(
            name="Test Company",
            slug="test-company",
            status=TenantStatus.ACTIVE
        )
        db.session.add(tenant)
        db.session.commit()
        db.session.refresh(tenant)
        yield tenant


@pytest.fixture
def tenant_trial(app):
    """Create a tenant in trial status."""
    with app.app_context():
        tenant = Tenant(
            name="Trial Company",
            slug="trial-company",
            status=TenantStatus.TRIAL,
            trial_ends_at=datetime(2099, 12, 31)
        )
        db.session.add(tenant)
        db.session.commit()
        db.session.refresh(tenant)
        yield tenant


@pytest.fixture
def tenant_suspended(app):
    """Create a suspended tenant."""
    with app.app_context():
        tenant = Tenant(
            name="Suspended Company",
            slug="suspended-company",
            status=TenantStatus.SUSPENDED
        )
        db.session.add(tenant)
        db.session.commit()
        db.session.refresh(tenant)
        yield tenant


@pytest.fixture
def second_tenant(app):
    """Create a second tenant for isolation tests."""
    with app.app_context():
        tenant = Tenant(
            name="Other Company",
            slug="other-company",
            status=TenantStatus.ACTIVE
        )
        db.session.add(tenant)
        db.session.commit()
        db.session.refresh(tenant)
        yield tenant


# =============================================================================
# Tenant User (Membership) Fixtures
# =============================================================================

@pytest.fixture
def tenant_user(app, user, tenant):
    """Create tenant membership linking user to tenant."""
    with app.app_context():
        # Re-fetch objects in this context
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)

        tenant_user = TenantUser(
            user_id=user_obj.id,
            tenant_id=tenant_obj.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user)
        db.session.commit()
        db.session.refresh(tenant_user)
        yield tenant_user


# =============================================================================
# Store Fixtures
# =============================================================================

@pytest.fixture
def store(app, tenant):
    """Create a test store."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)

        store = Store(
            tenant_id=tenant_obj.id,
            name="Main Store",
            address="123 Main St",
            phone="555-1234",
            email="store@example.com",
            is_active=True
        )
        db.session.add(store)
        db.session.commit()
        db.session.refresh(store)
        yield store


@pytest.fixture
def second_store(app, tenant):
    """Create a second store for the same tenant."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)

        store = Store(
            tenant_id=tenant_obj.id,
            name="Branch Store",
            address="456 Branch Ave",
            is_active=True
        )
        db.session.add(store)
        db.session.commit()
        db.session.refresh(store)
        yield store


@pytest.fixture
def store_user(app, user, store, tenant):
    """Assign user to store."""
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        store_obj = db.session.get(Store, store.id)
        tenant_obj = db.session.get(Tenant, tenant.id)

        store_user = StoreUser(
            user_id=user_obj.id,
            store_id=store_obj.id,
            tenant_id=tenant_obj.id,
            assigned_at=datetime.utcnow()
        )
        db.session.add(store_user)
        db.session.commit()
        db.session.refresh(store_user)
        yield store_user


# =============================================================================
# Permission Fixtures
# =============================================================================

@pytest.fixture
def permissions(app):
    """Create all permissions needed for testing."""
    with app.app_context():
        permission_data = [
            # Users
            ("users.view", "users", "view", "View users"),
            ("users.create", "users", "create", "Create users"),
            ("users.edit", "users", "edit", "Edit users"),
            ("users.delete", "users", "delete", "Delete users"),
            ("users.manage_roles", "users", "manage_roles", "Manage user roles"),
            # Stores
            ("stores.view", "stores", "view", "View stores"),
            ("stores.create", "stores", "create", "Create stores"),
            ("stores.edit", "stores", "edit", "Edit stores"),
            ("stores.delete", "stores", "delete", "Delete stores"),
            ("stores.manage_users", "stores", "manage_users", "Manage store users"),
            # Roles
            ("roles.view", "roles", "view", "View roles"),
            ("roles.create", "roles", "create", "Create roles"),
            ("roles.edit", "roles", "edit", "Edit roles"),
            ("roles.delete", "roles", "delete", "Delete roles"),
            # Permissions
            ("permissions.view", "permissions", "view", "View permissions"),
            # Tenants
            ("tenants.view", "tenants", "view", "View tenants"),
            ("tenants.edit", "tenants", "edit", "Edit tenants"),
            ("tenants.manage", "tenants", "manage", "Manage tenants"),
        ]

        permissions = []
        for name, resource, action, description in permission_data:
            perm = Permission(
                name=name,
                resource=resource,
                action=action,
                description=description
            )
            db.session.add(perm)
            permissions.append(perm)

        db.session.commit()

        # Refresh all
        for p in permissions:
            db.session.refresh(p)

        yield permissions


# =============================================================================
# Role Fixtures
# =============================================================================

@pytest.fixture
def admin_role(app, tenant, permissions):
    """Create an admin role with all permissions."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)

        role = Role(
            tenant_id=tenant_obj.id,
            name="Admin",
            description="Administrator with full access",
            is_system_role=True
        )
        db.session.add(role)
        db.session.flush()

        # Assign all permissions
        for perm in permissions:
            perm_obj = db.session.get(Permission, perm.id)
            role_perm = RolePermission(
                role_id=role.id,
                permission_id=perm_obj.id
            )
            db.session.add(role_perm)

        db.session.commit()
        db.session.refresh(role)
        yield role


@pytest.fixture
def viewer_role(app, tenant, permissions):
    """Create a viewer role with view-only permissions."""
    with app.app_context():
        tenant_obj = db.session.get(Tenant, tenant.id)

        role = Role(
            tenant_id=tenant_obj.id,
            name="Viewer",
            description="Read-only access",
            is_system_role=False
        )
        db.session.add(role)
        db.session.flush()

        # Assign only view permissions
        view_perms = [p for p in permissions if p.action == "view"]
        for perm in view_perms:
            perm_obj = db.session.get(Permission, perm.id)
            role_perm = RolePermission(
                role_id=role.id,
                permission_id=perm_obj.id
            )
            db.session.add(role_perm)

        db.session.commit()
        db.session.refresh(role)
        yield role


# =============================================================================
# User Role Assignment Fixtures
# =============================================================================

@pytest.fixture
def user_with_admin_role(app, user, tenant, admin_role, tenant_user):
    """Assign admin role to user (tenant-wide)."""
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)
        role_obj = db.session.get(Role, admin_role.id)

        user_role = UserRole(
            user_id=user_obj.id,
            role_id=role_obj.id,
            tenant_id=tenant_obj.id,
            store_id=None,  # Tenant-wide
            assigned_at=datetime.utcnow()
        )
        db.session.add(user_role)
        db.session.commit()
        db.session.refresh(user_role)
        yield user_role


@pytest.fixture
def user_with_viewer_role(app, user, tenant, viewer_role, tenant_user):
    """Assign viewer role to user (tenant-wide)."""
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)
        role_obj = db.session.get(Role, viewer_role.id)

        user_role = UserRole(
            user_id=user_obj.id,
            role_id=role_obj.id,
            tenant_id=tenant_obj.id,
            store_id=None,
            assigned_at=datetime.utcnow()
        )
        db.session.add(user_role)
        db.session.commit()
        db.session.refresh(user_role)
        yield user_role


@pytest.fixture
def user_with_store_role(app, user, tenant, store, admin_role, tenant_user):
    """Assign admin role to user for a specific store only."""
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)
        store_obj = db.session.get(Store, store.id)
        role_obj = db.session.get(Role, admin_role.id)

        user_role = UserRole(
            user_id=user_obj.id,
            role_id=role_obj.id,
            tenant_id=tenant_obj.id,
            store_id=store_obj.id,
            assigned_at=datetime.utcnow()
        )
        db.session.add(user_role)
        db.session.commit()
        db.session.refresh(user_role)
        yield user_role


# =============================================================================
# Authentication Helpers
# =============================================================================

@pytest.fixture
def auth_tokens(app, user, tenant, tenant_user):
    """Generate authentication tokens for user."""
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)

        tokens = generate_token_pair(user_obj.id, tenant_obj.id)
        yield tokens


@pytest.fixture
def auth_headers(auth_tokens):
    """Generate Authorization header with access token."""
    return {
        "Authorization": f"Bearer {auth_tokens['access_token']}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def auth_headers_with_store(auth_headers, store):
    """Authorization headers including store context."""
    headers = auth_headers.copy()
    headers["X-Store-ID"] = str(store.id)
    return headers


# =============================================================================
# Complete Setup Fixtures (for convenience)
# =============================================================================

@pytest.fixture
def authenticated_user(app, user, tenant, tenant_user, permissions, admin_role, user_with_admin_role, auth_headers):
    """
    Complete authenticated user setup:
    - User exists
    - Tenant exists
    - User is member of tenant
    - Permissions created
    - Admin role created with permissions
    - User assigned admin role
    - Auth headers ready
    """
    with app.app_context():
        user_obj = db.session.get(User, user.id)
        tenant_obj = db.session.get(Tenant, tenant.id)

        yield {
            "user": user_obj,
            "tenant": tenant_obj,
            "headers": auth_headers
        }


@pytest.fixture
def second_authenticated_user(app, second_tenant, user_password):
    """
    Create a complete second user in a different tenant.
    Useful for tenant isolation tests.
    """
    with app.app_context():
        # Create user
        user2 = User(
            email="user2@other.com",
            full_name="Second User",
            is_active=True
        )
        user2.set_password(user_password)
        db.session.add(user2)
        db.session.flush()

        # Get tenant
        tenant2 = db.session.get(Tenant, second_tenant.id)

        # Create membership
        tenant_user2 = TenantUser(
            user_id=user2.id,
            tenant_id=tenant2.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user2)
        db.session.commit()

        # Generate tokens
        tokens = generate_token_pair(user2.id, tenant2.id)

        yield {
            "user": user2,
            "tenant": tenant2,
            "headers": {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }
        }
