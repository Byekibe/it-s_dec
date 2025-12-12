"""
Store API endpoint tests.

Tests for:
- GET /api/v1/stores
- GET /api/v1/stores/:id
- POST /api/v1/stores
- PUT /api/v1/stores/:id
- DELETE /api/v1/stores/:id
- GET /api/v1/stores/:id/users
- POST /api/v1/stores/:id/users
- DELETE /api/v1/stores/:id/users
"""

import pytest
from uuid import uuid4

from app.extensions import db
from app.blueprints.stores.models import Store, StoreUser


class TestStoreList:
    """Tests for GET /api/v1/stores endpoint."""

    @pytest.mark.integration
    def test_list_stores(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test listing stores for current tenant."""
        response = client.get("/api/v1/stores", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        stores = data.get("items", data.get("stores", []))
        assert len(stores) >= 1

        store_names = [s["name"] for s in stores]
        assert store.name in store_names

    @pytest.mark.integration
    def test_list_stores_pagination(
        self, client, app, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test store list pagination."""
        # Create multiple stores
        with app.app_context():
            for i in range(5):
                s = Store(
                    tenant_id=tenant.id,
                    name=f"Store {i}",
                    is_active=True
                )
                db.session.add(s)
            db.session.commit()

        response = client.get("/api/v1/stores?page=1&per_page=3", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        stores = data.get("items", data.get("stores", []))
        assert len(stores) <= 3

    @pytest.mark.integration
    def test_list_stores_search(
        self, client, app, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test searching stores by name."""
        # Create store with specific name
        with app.app_context():
            s = Store(
                tenant_id=tenant.id,
                name="Searchable Store Location",
                is_active=True
            )
            db.session.add(s)
            db.session.commit()

        response = client.get(
            "/api/v1/stores?search=Searchable",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        stores = data.get("items", data.get("stores", []))
        names = [s["name"] for s in stores]
        assert "Searchable Store Location" in names

    @pytest.mark.integration
    def test_filter_active_stores(
        self, client, app, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test filtering active stores."""
        # Create inactive store
        with app.app_context():
            s = Store(
                tenant_id=tenant.id,
                name="Inactive Store",
                is_active=False
            )
            db.session.add(s)
            db.session.commit()

        response = client.get(
            "/api/v1/stores?is_active=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        stores = data.get("items", data.get("stores", []))
        for s in stores:
            assert s.get("is_active", True) is True


class TestStoreCRUD:
    """Tests for store CRUD operations."""

    @pytest.mark.integration
    def test_get_store_by_id(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting a specific store by ID."""
        response = client.get(
            f"/api/v1/stores/{store.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == str(store.id)
        assert data["name"] == store.name

    @pytest.mark.integration
    def test_get_nonexistent_store(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting a store that doesn't exist."""
        response = client.get(
            f"/api/v1/stores/{uuid4()}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_create_store(
        self, client, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a new store."""
        response = client.post("/api/v1/stores", headers=auth_headers, json={
            "name": "New Store",
            "address": "123 New St",
            "phone": "555-0000",
            "email": "newstore@example.com"
        })

        assert response.status_code == 201
        data = response.get_json()

        assert data["name"] == "New Store"
        assert data["address"] == "123 New St"
        assert data["is_active"] is True

    @pytest.mark.integration
    def test_create_store_minimal(
        self, client, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a store with only required fields."""
        response = client.post("/api/v1/stores", headers=auth_headers, json={
            "name": "Minimal Store"
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Minimal Store"

    @pytest.mark.integration
    def test_create_store_missing_name(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test creating a store without name fails."""
        response = client.post("/api/v1/stores", headers=auth_headers, json={
            "address": "123 Street"
            # Missing required name
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_store(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating a store."""
        response = client.put(
            f"/api/v1/stores/{store.id}",
            headers=auth_headers,
            json={
                "name": "Updated Store Name",
                "address": "456 Updated Ave"
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["name"] == "Updated Store Name"
        assert data["address"] == "456 Updated Ave"

    @pytest.mark.integration
    def test_update_store_partial(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test partial update of store (only phone)."""
        original_name = store.name

        response = client.put(
            f"/api/v1/stores/{store.id}",
            headers=auth_headers,
            json={"phone": "555-9999"}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["phone"] == "555-9999"
        # Name should remain unchanged
        assert data["name"] == original_name

    @pytest.mark.integration
    def test_delete_store(
        self, client, app, tenant, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test deleting a store."""
        # Create a store to delete
        with app.app_context():
            s = Store(
                tenant_id=tenant.id,
                name="Deletable Store",
                is_active=True
            )
            db.session.add(s)
            db.session.commit()
            store_id = s.id

        response = client.delete(
            f"/api/v1/stores/{store_id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204]

        # Verify store is deleted or deactivated
        get_response = client.get(
            f"/api/v1/stores/{store_id}",
            headers=auth_headers
        )

        # Either 404 (hard delete) or inactive (soft delete)
        if get_response.status_code == 200:
            data = get_response.get_json()
            assert data.get("is_active") is False or data.get("deleted_at") is not None
        else:
            assert get_response.status_code == 404

    @pytest.mark.integration
    def test_deactivate_store(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test deactivating a store."""
        response = client.put(
            f"/api/v1/stores/{store.id}",
            headers=auth_headers,
            json={"is_active": False}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_active"] is False


class TestStoreUserAssignment:
    """Tests for store user assignment endpoints."""

    @pytest.mark.integration
    def test_get_store_users(
        self, client, store, user, store_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test listing users assigned to a store."""
        response = client.get(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        users = data.get("items", data.get("users", []))
        user_ids = [u.get("id") or u.get("user_id") or u.get("user", {}).get("id") for u in users]
        assert str(user.id) in [str(uid) for uid in user_ids]

    @pytest.mark.integration
    def test_assign_user_to_store(
        self, client, app, store, tenant, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test assigning a user to a store."""
        # Create a user to assign
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import TenantUser
        from datetime import datetime

        with app.app_context():
            new_user = User(
                email="assignable@example.com",
                full_name="Assignable User",
                is_active=True
            )
            new_user.set_password(user_password)
            db.session.add(new_user)
            db.session.flush()

            # Add to tenant
            tu = TenantUser(
                user_id=new_user.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow()
            )
            db.session.add(tu)
            db.session.commit()
            new_user_id = new_user.id

        response = client.post(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers,
            json={"user_ids": [str(new_user_id)]}
        )

        assert response.status_code in [200, 201]

    @pytest.mark.integration
    def test_remove_user_from_store(
        self, client, store, user, store_user, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test removing a user from a store."""
        response = client.delete(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers,
            json={"user_ids": [str(user.id)]}
        )

        assert response.status_code in [200, 204]

        # Verify user is no longer assigned
        get_response = client.get(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers
        )

        if get_response.status_code == 200:
            data = get_response.get_json()
            users = data.get("items", data.get("users", []))
            user_ids = [u.get("id") or u.get("user_id") for u in users]
            assert str(user.id) not in [str(uid) for uid in user_ids]

    @pytest.mark.integration
    def test_assign_nonexistent_user_fails(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test assigning non-existent user to store fails."""
        response = client.post(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers,
            json={"user_ids": [str(uuid4())]}
        )

        assert response.status_code in [400, 404]

    @pytest.mark.integration
    def test_assign_multiple_users_to_store(
        self, client, app, store, tenant, permissions, admin_role, user_with_admin_role, auth_headers, user_password
    ):
        """Test assigning multiple users to a store at once."""
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import TenantUser
        from datetime import datetime

        user_ids = []

        with app.app_context():
            for i in range(3):
                new_user = User(
                    email=f"bulk{i}@example.com",
                    full_name=f"Bulk User {i}",
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
                user_ids.append(str(new_user.id))

            db.session.commit()

        response = client.post(
            f"/api/v1/stores/{store.id}/users",
            headers=auth_headers,
            json={"user_ids": user_ids}
        )

        assert response.status_code in [200, 201]


class TestStoreSettings:
    """Tests for /api/v1/stores/:id/settings endpoints."""

    @pytest.mark.integration
    def test_get_store_settings_default(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting store settings returns defaults when none exist."""
        response = client.get(f"/api/v1/stores/{store.id}/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Check default values
        assert data["print_receipt_by_default"] is True
        assert data["allow_negative_stock"] is False
        assert data["low_stock_threshold"] == 10
        assert data["operating_hours"] is None

    @pytest.mark.integration
    def test_update_store_settings_operating_hours(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating store operating hours."""
        operating_hours = {
            "monday": {"open": "08:00", "close": "18:00"},
            "tuesday": {"open": "08:00", "close": "18:00"},
            "wednesday": {"open": "08:00", "close": "18:00"},
            "thursday": {"open": "08:00", "close": "18:00"},
            "friday": {"open": "08:00", "close": "18:00"},
            "saturday": {"open": "09:00", "close": "14:00"},
            "sunday": {"open": "00:00", "close": "00:00", "closed": True}
        }

        response = client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "operating_hours": operating_hours
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["operating_hours"]["monday"]["open"] == "08:00"
        assert data["operating_hours"]["sunday"]["closed"] is True

    @pytest.mark.integration
    def test_update_store_settings_receipt(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating store receipt settings."""
        response = client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "receipt_header": "Welcome to our store!",
            "receipt_footer": "Thank you for shopping with us.",
            "print_receipt_by_default": False
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["receipt_header"] == "Welcome to our store!"
        assert data["receipt_footer"] == "Thank you for shopping with us."
        assert data["print_receipt_by_default"] is False

    @pytest.mark.integration
    def test_update_store_settings_inventory(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating store inventory settings."""
        response = client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "allow_negative_stock": True,
            "low_stock_threshold": 25
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["allow_negative_stock"] is True
        assert data["low_stock_threshold"] == 25

    @pytest.mark.integration
    def test_update_store_settings_contact(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating store contact info override."""
        response = client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "phone": "+254700123456",
            "email": "branch1@example.com",
            "address": "123 Main St, Nairobi"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["phone"] == "+254700123456"
        assert data["email"] == "branch1@example.com"
        assert data["address"] == "123 Main St, Nairobi"

    @pytest.mark.integration
    def test_get_store_settings_nonexistent_store(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test getting settings for non-existent store fails."""
        response = client.get(f"/api/v1/stores/{uuid4()}/settings", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.integration
    def test_update_store_settings_nonexistent_store(
        self, client, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test updating settings for non-existent store fails."""
        response = client.put(f"/api/v1/stores/{uuid4()}/settings", headers=auth_headers, json={
            "low_stock_threshold": 50
        })

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_store_settings_unauthenticated(self, client, store):
        """Test getting store settings without authentication."""
        response = client.get(f"/api/v1/stores/{store.id}/settings")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_update_store_settings_unauthenticated(self, client, store):
        """Test updating store settings without authentication."""
        response = client.put(f"/api/v1/stores/{store.id}/settings", json={
            "low_stock_threshold": 50
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_settings_persist_after_update(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that settings persist after update."""
        # Update settings
        client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "low_stock_threshold": 100,
            "allow_negative_stock": True
        })

        # Get settings again
        response = client.get(f"/api/v1/stores/{store.id}/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["low_stock_threshold"] == 100
        assert data["allow_negative_stock"] is True

    @pytest.mark.integration
    def test_update_store_settings_invalid_threshold(
        self, client, store, permissions, admin_role, user_with_admin_role, auth_headers
    ):
        """Test that invalid low stock threshold is rejected."""
        response = client.put(f"/api/v1/stores/{store.id}/settings", headers=auth_headers, json={
            "low_stock_threshold": -5
        })

        assert response.status_code == 400
