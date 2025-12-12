# Bug Fix and Refactoring Report

**Date**: 2025-12-09

This report details the resolution of four critical application bugs that were causing 8 tests to fail. The fixes involved correcting application logic, improving data queries, and aligning tests with the correct application behavior.

---

## 1. TenantStatus Enum JSON Serialization Error

- **File Affected**: `app/blueprints/tenants/schemas.py`
- **Symptom**: The `TenantStatus` enum (e.g., "trial", "active") was not being correctly converted to a string in API responses, causing a serialization error.

### Code Changes

**Old Code:**
The schema used a custom method to serialize the enum, which was unnecessarily complex.
```python
class TenantResponseSchema(Schema):
    # ...
    status = fields.Method("get_status")
    # ...
    def get_status(self, obj):
        """Get status value from enum."""
        if hasattr(obj, 'status'):
            return obj.status.value if obj.status else None
        return obj.get('status')
```

**New Code:**
The fix was to use Marshmallow's built-in `Enum` field for direct, reliable serialization.
```python
from app.blueprints.tenants.models import TenantStatus # Import added

class TenantResponseSchema(Schema):
    # ...
    status = fields.Enum(TenantStatus, by_value=True)
    # ...
    # (The get_status method was removed)
```

### Rationale

The original implementation was brittle. The new code leverages the `fields.Enum` type from Marshmallow, which is the idiomatic and robust way to handle enum serialization. It ensures the enum's string value is always used, simplifying the schema and removing the possibility of error.

---

## 2. Incorrect Validator Signature in `UpdateCurrentUserSchema`

- **File Affected**: `app/blueprints/users/schemas.py`
- **Symptom**: A validator intended to check for `current_password` when a `new_password` was supplied used the wrong decorator, meaning the validation logic was never correctly applied at the schema level.

### Code Changes

**Old Code:**
A single-field validator (`@validates`) was used for a cross-field validation task.
```python
class UpdateCurrentUserSchema(Schema):
    # ...
    @validates("new_password")
    def validate_new_password(self, value):
        """Ensure current_password is provided when changing password."""
        # Note: This validation happens at the service level since we need
        # access to both fields together
```

**New Code:**
The validator was replaced with `@validates_schema`, the correct decorator for schema-level, cross-field validation.
```python
from marshmallow import ..., validates_schema # Import added

class UpdateCurrentUserSchema(Schema):
    # ...
    @validates_schema
    def validate_password_change(self, data, **kwargs):
        if 'new_password' in data and not data.get('current_password'):
            raise ValidationError("Current password is required to change password.", field_name="current_password")
```

### Rationale

The fix moves the cross-field validation logic to the schema layer where it belongs, rather than relying on the service layer. Using `@validates_schema` allows the validator to access all fields in the payload, correctly enforcing the rule that `current_password` is required to set a `new_password`.

---

## 3. Tenant Endpoint Permission Failure (403 Forbidden)

- **Files Affected**: `app/blueprints/auth/services.py`, `tests/test_api_tenants.py`
- **Symptom**: The test `test_trial_tenant_can_operate` was failing with a `403 Forbidden` error. Investigation revealed a critical bug where the user registration process did not create any default roles (e.g., "Owner", "Admin") for the new tenant, leaving the first user with no permissions.

### Code Changes (Application)

**Old Code:**
The `AuthService.register` method created a user and tenant but did no role seeding.
```python
# In AuthService.register:
# ...
        db.session.add(tenant_user)

        db.session.commit()

        # Generate tokens
        tokens = generate_token_pair(user.id, tenant.id)
# ...
```

**New Code:**
The `register` method now calls a new helper function (`_seed_tenant_roles`) to bootstrap the tenant with default roles and assign the "Owner" role to the new user.
```python
# In AuthService.register:
# ...
        db.session.add(tenant_user)

        # Seed the new tenant with default roles and assign Owner
        AuthService._seed_tenant_roles(tenant, user)

        db.session.commit()

        # Generate tokens
        tokens = generate_token_pair(user.id, tenant.id)
# ...
```

### Rationale (Application)

This was a critical bug in the application's business logic. The fix ensures that every new tenant is created with a complete and secure permission system from the start, making the application usable immediately upon registration.

### Code Changes (Test)

**Old Code:**
The test manually created fixtures, which did not trigger the (missing) role-seeding logic.
```python
# In tests/test_api_tenants.py
def test_trial_tenant_can_operate(self, client, app, user, tenant_trial, user_password):
    # ... manual creation of TenantUser ...
    # ... generate token ...
    response = client.get("/api/v1/tenants/current", headers=headers)
    assert response.status_code == 200 # Fails with 403
```

**New Code:**
The test was refactored to use the `AuthService.register` method, making it a true integration test.
```python
# In tests/test_api_tenants.py
def test_trial_tenant_can_operate(self, client, app, user_password, permissions):
    from app.blueprints.auth.services import AuthService

    with app.app_context():
        reg_data = AuthService.register(...) # Creates user, tenant, and roles
        tokens = { "access_token": reg_data["access_token"], ... }

    headers = { "Authorization": f"Bearer {tokens['access_token']}", ... }
    response = client.get("/api/v1/tenants/current", headers=headers)
    assert response.status_code == 200 # Now passes
```

### Rationale (Test)

The original test was flawed because it didn't accurately simulate the user registration flow. By refactoring the test to use the `register` service, it now correctly validates the end-to-end process: a user registers, gets assigned the "Owner" role, and can immediately access permitted endpoints.

---

## 4. Incorrect User Roles Response Structure

- **Files Affected**: `app/blueprints/rbac/services.py`, `tests/test_rbac.py`
- **Symptom**: The test `test_get_user_roles` was failing with `AssertionError: assert 'Admin' in [None]`, indicating the role name was not present in the API response.

### Code Changes (Application Service)

**Old Code:**
The `RBACService.get_user_roles` method was inefficiently building a dictionary response manually and causing an "N+1" query problem by fetching each `Role` inside a loop.
```python
# In RBACService.get_user_roles:
role_assignments = db.session.query(UserRole).filter(...).all()

roles = []
for ra in role_assignments:
    role = db.session.get(Role, ra.role_id) # N+1 query
    if role and role.deleted_at is None:
        # ... manual dict creation ...
        roles.append({ "role_name": role.name, ... })

return { "user_id": user_id, "roles": roles }
```

**New Code:**
The service was refactored to eagerly load the related `role` and `store` objects using `joinedload` and return the raw model objects directly, letting the schema handle serialization.
```python
# In RBACService.get_user_roles:
role_assignments = db.session.query(UserRole).filter(...).options(
    joinedload(UserRole.role),
    joinedload(UserRole.store)
).all()

return {
    "user_id": user_id,
    "roles": role_assignments,  # Return model objects directly
}
```

### Rationale (Application Service)

This fix makes the data retrieval much more efficient by eliminating the N+1 query problem. It also correctly separates concerns by letting the service layer fetch data and the schema layer handle its presentation. This makes the code cleaner, more performant, and less prone to bugs when the data model changes.

### Code Changes (Test)

**Old Code:**
The test was asserting against an incorrect key in the response.
```python
# In tests/test_rbac.py -> test_get_user_roles:
role_names = [r.get("name") or r.get("role", {}).get("name") for r in roles]
assert "Admin" in role_names
```

**New Code:**
The test was updated to check for the correct key, `role_name`, which is what the schema actually produces.
```python
# In tests/test_rbac.py -> test_get_user_roles:
role_names = [r.get("role_name") for r in roles]
assert "Admin" in role_names
```

### Rationale (Test)

After fixing the application code, the test was still failing. The final fix was to correct the test itself, which was asserting against a field (`name`) that did not exist in the response. The updated test now correctly validates the `role_name` field, aligning it with the API's actual response structure.
