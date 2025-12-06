# Building the Core System: A Comprehensive Guide

This document outlines the architectural approach and step-by-step process for building the core foundation of a multi-tenant, multi-store SaaS application with Role-Based Access Control (RBAC).

## Introduction: The "Operating System" Analogy

Think of this core system as the **Operating System (OS)** for our application. It doesn't handle specific business features like "Inventory" or "Billing" itself. Instead, it provides the foundational services that all other feature modules will run on top of:
*   **Identity & Security:** Who is this user?
*   **Tenancy:** Which company do they belong to?
*   **Authorization:** What are they allowed to do?
*   **Data Isolation:** How do we guarantee tenants can never see each other's data?

By building this robust OS first, we can later add new features ("apps") quickly and securely, without having to reinvent the security and data isolation logic each time.

---

## Multi-Tenancy Pattern

This architecture uses **row-level multi-tenancy** (also called "shared database, shared schema"):
- All tenants share the same database and tables
- Data isolation is achieved via a `tenant_id` column on every tenant-scoped table
- This pattern offers the best balance of operational simplicity and cost efficiency for most SaaS applications

**Why this pattern?**
- ✅ Easier to manage (one database, one deployment)
- ✅ Cost-effective at scale
- ✅ Simpler backup/restore procedures
- ⚠️ Requires strict query filtering (which we enforce via middleware + ORM hooks)

**Alternatives not covered here:**
- Schema-per-tenant (better isolation, more complex operations)
- Database-per-tenant (maximum isolation, highest operational overhead)

---

## Entity Relationship Overview

```
User ←→ TenantUser ←→ Tenant
 ↓                       ↓
 ↓                    Store
 ↓                       ↓
 └→ UserRole ←→ Role ←→ RolePermission ←→ Permission
         ↓
      StoreUser
```

**Key Relationships:**
- A User can belong to multiple Tenants (via TenantUser)
- A Tenant can have multiple Stores
- A User can have different Roles in different Stores within the same Tenant
- Roles are tenant-specific; Permissions are globally defined

---

## The Step-by-Step Build Process

Building this core system follows a logical progression from the abstract data structure to the concrete application entry point.

### Step 1: Define the Core Data Models (The Blueprint)

This is the absolute first step. The models are the blueprint of our data world, defining the primary entities and their relationships.

#### Primary Entity Models

##### `User` (Global Entity)
The global model for a person who can log in.
```python
- id: UUID
- email: String (unique)
- password_hash: String
- full_name: String
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

##### `Tenant` (Top-Level Isolation Boundary)
The top-level entity representing a company. This is the primary container for data segregation.
```python
- id: UUID
- name: String
- slug: String (unique, URL-friendly)
- status: Enum ['active', 'suspended', 'trial', 'canceled']
- trial_ends_at: DateTime (nullable)
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (nullable, for soft deletes)
```

**Status Field Explanation:**
- `trial`: New tenant in trial period
- `active`: Paying/active tenant
- `suspended`: Temporarily disabled (payment issue, admin action)
- `canceled`: Tenant has been canceled (soft delete alternative)

##### `Store` (Tenant-Scoped Entity)
A specific location or branch that **must** belong to a single `Tenant`.
```python
- id: UUID
- tenant_id: UUID (FK, indexed)
- name: String
- address: String
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (nullable)
```

##### `Role` (Tenant-Scoped Entity)
A named set of permissions (e.g., "Admin", "Store Manager") that is defined **within a `Tenant`**.
```python
- id: UUID
- tenant_id: UUID (FK, indexed)
- name: String
- description: String
- is_system_role: Boolean (e.g., "Owner" role created during tenant registration)
- created_at: DateTime
- updated_at: DateTime
```

##### `Permission` (Global Entity)
A single, granular action (e.g., `products.edit`). These are code-defined and seeded, not user-created.
```python
- id: UUID
- name: String (unique, e.g., "products.create")
- resource: String (e.g., "products")
- action: String (e.g., "create")
- description: String
```

**Permission Naming Convention:** Use `resource.action` format:
- `products.create`, `products.edit`, `products.view`, `products.delete`
- `stores.create`, `stores.edit`, `stores.view`
- `users.invite`, `users.edit`, `users.view`
- `invoices.create`, `invoices.edit`, `invoices.view`, `invoices.approve`

**Wildcard Support (Optional):** Consider supporting `products.*` to grant all product permissions.

#### Junction (Link) Models

These tables are the glue that connects the primary entities.

##### `TenantUser`
Links a `User` to a `Tenant`. Establishes tenant membership.
```python
- id: UUID
- user_id: UUID (FK)
- tenant_id: UUID (FK)
- joined_at: DateTime
- invited_by: UUID (FK to User, nullable)
- unique_constraint: (user_id, tenant_id)
```

##### `StoreUser`
Links a `User` to specific `Store`(s) they can access within a tenant.
```python
- id: UUID
- user_id: UUID (FK)
- store_id: UUID (FK)
- tenant_id: UUID (FK, denormalized for query performance)
- assigned_at: DateTime
- unique_constraint: (user_id, store_id)
```

**Design Note:** The `tenant_id` is denormalized here for easier querying, since it can be derived from `store_id`.

##### `UserRole`
Assigns a `Role` to a `User`, either globally within the tenant or scoped to a specific `Store`.
```python
- id: UUID
- user_id: UUID (FK)
- role_id: UUID (FK)
- tenant_id: UUID (FK, denormalized)
- store_id: UUID (FK, nullable) # If NULL, role applies to entire tenant
- assigned_at: DateTime
- assigned_by: UUID (FK to User)
- unique_constraint: (user_id, role_id, store_id)
```

**Role Scope Logic:**
- If `store_id` is NULL: User has this role across the entire tenant
- If `store_id` is set: User has this role only for that specific store

##### `RolePermission`
Links many `Permissions` to a `Role`.
```python
- id: UUID
- role_id: UUID (FK)
- permission_id: UUID (FK)
- unique_constraint: (role_id, permission_id)
```

#### Audit Trail Support

**Every tenant-scoped entity should include:**
```python
- created_by: UUID (FK to User, nullable)
- updated_by: UUID (FK to User, nullable)
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (nullable, for soft deletes)
```

**Why this matters:**
- Compliance requirements (who did what, when)
- Debugging and support (trace issue back to specific action)
- User accountability

---

### Step 2: Implement the Context & Security Middleware (The Gatekeeper)

Once the models define the *rules* of data separation, the middleware *enforces* those rules on every API request. It acts as a security checkpoint.

#### `TenantMiddleware` (Required for All Protected Routes)

**Execution Order:** Runs immediately after authentication middleware

**Responsibilities:**
1. Extract `tenant_id` from JWT token
2. Validate tenant exists and has `status = 'active'` (reject suspended/canceled tenants)
3. Verify current user is a member of this tenant (check `TenantUser` table)
4. Establish `TenantContext` for the request lifecycle

**Context Object:**
```python
class TenantContext:
    tenant_id: UUID
    tenant_slug: str
    user_id: UUID
    is_tenant_owner: bool
```

**Error Handling:**
- Missing/invalid tenant_id → `401 Unauthorized`
- Tenant not found → `404 Not Found`
- Tenant suspended → `403 Forbidden` with message "Account suspended"
- User not member of tenant → `403 Forbidden`

#### `StoreMiddleware` (Optional, Route-Specific)

**Execution Order:** Runs *after* `TenantMiddleware`

**Responsibilities:**
1. Extract `store_id` from request (e.g., `X-Store-ID` header or route parameter)
2. Validate store exists and belongs to current tenant
3. Verify user has access to this store (check `StoreUser` table)
4. Establish `StoreContext`

**Context Object:**
```python
class StoreContext:
    store_id: UUID
    store_name: str
    # Inherits from TenantContext
```

**When to use:**
- Apply to routes that operate on store-specific data
- Skip for tenant-level operations (e.g., creating new stores)

#### Automatic Query Filter (SQLAlchemy Hook)

This is the **ultimate safety net** - a defense-in-depth layer that automatically scopes database queries.

**Implementation (SQLAlchemy example):**
```python
from sqlalchemy import event
from sqlalchemy.orm import Session
from flask import g, has_request_context

@event.listens_for(Session, 'do_orm_execute')
def receive_do_orm_execute(orm_execute_state):
    """
    Automatically filter queries by tenant_id within request context.
    This prevents accidental data leaks across tenant boundaries.
    """
    # Only apply during web requests with established tenant context
    if not has_request_context() or not hasattr(g, 'tenant_id'):
        return
    
    # Check if the query targets a tenant-scoped model
    if orm_execute_state.is_select:
        for entity in orm_execute_state.statement.column_descriptions:
            model = entity.get('entity')
            
            # Only filter models with a tenant_id column
            if model and hasattr(model, 'tenant_id'):
                # Inject WHERE tenant_id = ? automatically
                orm_execute_state.statement = orm_execute_state.statement.filter_by(
                    tenant_id=g.tenant_id
                )
```

**Benefits:**
- Developers can write `Store.query.all()` safely within a request
- Even if a developer forgets to filter by tenant, the hook catches it
- Reduces tenant-scoping boilerplate throughout the codebase

**Important:** This hook should NOT run for:
- Background jobs (use explicit filtering)
- System admin operations
- Database migrations
- Testing scaffolding

---

### Step 3: Build the Application's Entry Point (Authentication)

With the data structure and security enforcement in place, you need a way for the first user to get into the system.

#### Authentication Service

Create an `AuthenticationService` with these core methods:

##### `register(email, password, full_name, company_name) -> dict`

**Critical:** This is a special operation that creates multiple records atomically.

```python
# Pseudocode flow:
1. Validate email not already registered
2. Hash password
3. BEGIN TRANSACTION
4.   Create User
5.   Create Tenant (status='trial', trial_ends_at=now+14days)
6.   Create TenantUser link
7.   Create "Owner" Role for this Tenant
8.   Seed default permissions to Owner role
9.   Assign Owner role to User (UserRole with store_id=NULL)
10. COMMIT TRANSACTION
11. Generate JWT token
12. Return {user, tenant, token}
```

**Why atomic?** If any step fails, the entire registration should roll back to avoid orphaned records.

##### `login(email, password, tenant_slug=None) -> dict`

**Flow:**
```python
1. Find User by email
2. Verify password hash
3. If tenant_slug provided:
     Verify user is member of that tenant
   Else:
     If user belongs to only one tenant, use it
     If multiple tenants, return list and ask user to choose
4. Generate JWT containing {user_id, tenant_id}
5. Return {user, tenant, token}
```

**JWT Payload Structure:**
```json
{
  "user_id": "uuid-here",
  "tenant_id": "uuid-here",
  "exp": 1234567890
}
```

##### `refresh_token(refresh_token) -> dict`

**Flow:**
```python
1. Validate refresh token
2. Verify user and tenant still active
3. Generate new access token (short-lived, e.g., 15 min)
4. Return new access token
```

**Token Strategy:**
- Access tokens: Short-lived (15-60 minutes)
- Refresh tokens: Long-lived (7-30 days), stored in database for revocation
- On login, return both tokens
- Client uses refresh token to get new access tokens without re-authentication

##### `switch_tenant(user_id, target_tenant_id) -> dict`

**For users who belong to multiple tenants:**
```python
1. Verify user is member of target_tenant_id
2. Generate new JWT with target_tenant_id
3. Return {tenant, token}
```

#### API Routes

```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
POST /api/v1/auth/switch-tenant
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

#### Bootstrap Problem Solution

**The Challenge:** The first user/tenant can't be created through normal middleware because middleware requires a valid tenant context.

**Solution 1: Bootstrap Script (Recommended)**
```python
# scripts/bootstrap.py
# Run once during initial deployment
# Creates first super-admin user + tenant outside request context

def bootstrap_initial_tenant():
    user = User(email="admin@yourapp.com", ...)
    tenant = Tenant(name="System Admin", status='active', ...)
    # ... create without middleware
```

**Solution 2: Special Bootstrap Endpoint**
```python
POST /api/v1/auth/bootstrap
# Accept requests ONLY if database has zero tenants
# Disable after first use via environment variable
```

**Solution 3: Database Migration**
```python
# Include seed data in your initial migration
# Creates the first tenant + admin user automatically
```

---

### Step 4: Develop Core Resource Management APIs

Now that users can log in and have a secure context, you can build the APIs needed to manage the core entities.

#### RBAC Management APIs

**Roles:**
```
GET    /api/v1/roles                    # List all roles in current tenant
POST   /api/v1/roles                    # Create new role
GET    /api/v1/roles/:id                # Get role details
PUT    /api/v1/roles/:id                # Update role
DELETE /api/v1/roles/:id                # Delete role (if not in use)
POST   /api/v1/roles/:id/permissions    # Assign permissions to role
DELETE /api/v1/roles/:id/permissions/:permission_id
```

**User Role Assignment:**
```
POST   /api/v1/users/:id/roles          # Assign role to user
DELETE /api/v1/users/:id/roles/:role_id # Remove role from user
```

**Permission Requirements:**
- Creating/editing roles: `roles.manage`
- Assigning roles to users: `users.manage_roles`

#### User Management APIs

```
GET    /api/v1/users                    # List users in current tenant
POST   /api/v1/users/invite             # Invite new user to tenant
GET    /api/v1/users/:id                # Get user details
PUT    /api/v1/users/:id                # Update user
DELETE /api/v1/users/:id                # Remove user from tenant (soft delete)
POST   /api/v1/users/:id/stores         # Assign user to stores
DELETE /api/v1/users/:id/stores/:store_id
```

**Invitation Flow:**
```python
1. Admin sends invite with email + role
2. System creates User (if new) with random password or inactive status
3. Send email with invitation link containing token
4. User clicks link, sets password, account becomes active
5. User can now log in
```

#### Store Management APIs

```
GET    /api/v1/stores                   # List all stores in tenant
POST   /api/v1/stores                   # Create new store
GET    /api/v1/stores/:id               # Get store details
PUT    /api/v1/stores/:id               # Update store
DELETE /api/v1/stores/:id               # Soft delete store
POST   /api/v1/stores/:id/users         # Assign users to store
DELETE /api/v1/stores/:id/users/:user_id
```

**Permission Requirements:**
- Managing stores: `stores.manage`
- Viewing stores: `stores.view`

---

## Permission Seeding Strategy

Permissions should be **code-defined** and version-controlled, not created by users.

**Why?**
- Your application code checks for specific permission names
- Permissions are tied to features in your codebase
- Changing permissions requires code changes anyway

**Implementation:**

1. **Define Permissions in Code:**
```python
# config/permissions.py
PERMISSIONS = [
    # User Management
    ("users.invite", "users", "invite", "Invite new users to tenant"),
    ("users.view", "users", "view", "View user list and details"),
    ("users.edit", "users", "edit", "Edit user information"),
    ("users.remove", "users", "remove", "Remove users from tenant"),
    ("users.manage_roles", "users", "manage_roles", "Assign roles to users"),
    
    # Store Management
    ("stores.create", "stores", "create", "Create new stores"),
    ("stores.view", "stores", "view", "View store list and details"),
    ("stores.edit", "stores", "edit", "Edit store information"),
    ("stores.delete", "stores", "delete", "Delete stores"),
    
    # Role Management
    ("roles.create", "roles", "create", "Create new roles"),
    ("roles.view", "roles", "view", "View roles"),
    ("roles.edit", "roles", "edit", "Edit role permissions"),
    ("roles.delete", "roles", "delete", "Delete roles"),
    
    # Add more as features are built
]
```

2. **Create Migration/Seed Script:**
```python
# migrations/seed_permissions.py
def seed_permissions():
    for name, resource, action, description in PERMISSIONS:
        Permission.get_or_create(
            name=name,
            defaults={
                "resource": resource,
                "action": action,
                "description": description
            }
        )
```

3. **Run on Deployment:**
```bash
# Part of your deployment pipeline
python manage.py seed_permissions
```

**Adding New Permissions:**
1. Add to `PERMISSIONS` list in code
2. Deploy + run seed script
3. Admins can now assign new permission to roles

---

## Database Migration Strategy

**Multi-Tenant Considerations:**

Since we're using row-level multi-tenancy (shared schema), migrations are straightforward:
- Run migrations normally - schema changes apply to all tenants simultaneously
- Add `tenant_id` to new tables as early as possible
- Include indexes on `tenant_id` columns for performance

**Migration Checklist:**
- [ ] Does this table need a `tenant_id`? (Most do, except User, Permission, global config)
- [ ] Is `tenant_id` indexed?
- [ ] Are audit fields included (created_at, updated_at, deleted_at)?
- [ ] Are created_by/updated_by fields included?
- [ ] Is soft delete supported if needed?

**Version Numbering:**
Use semantic versioning for your API and correlate with migrations:
```
v1.0.0 -> Initial schema (Users, Tenants, Stores, RBAC)
v1.1.0 -> Add Products feature
v1.2.0 -> Add Invoicing feature
```

---

## Testing Strategy for Tenant Isolation

**Golden Rule:** Always create multiple tenants in your tests to verify queries don't leak data.

**Test Structure:**
```python
def test_stores_are_isolated_by_tenant():
    # Arrange: Create two separate tenants with stores
    tenant_a = create_tenant("Company A")
    tenant_b = create_tenant("Company B")
    
    store_a1 = create_store(tenant_a, "Store A1")
    store_b1 = create_store(tenant_b, "Store B1")
    
    # Act: Query as user from Tenant A
    with tenant_context(tenant_a):
        stores = Store.query.all()
    
    # Assert: Only see Tenant A's stores
    assert len(stores) == 1
    assert stores[0].id == store_a1.id
```

**Critical Test Cases:**
- [ ] User can only see their tenant's data
- [ ] User cannot access another tenant's data by guessing IDs
- [ ] Middleware rejects requests with invalid tenant_id
- [ ] Middleware rejects requests to suspended tenants
- [ ] Role assignments are scoped correctly (tenant-wide vs store-specific)
- [ ] Permission checks work correctly at both tenant and store level

**Integration Tests:**
```python
def test_cannot_access_another_tenants_store_via_api():
    tenant_a = create_tenant()
    tenant_b = create_tenant()
    store_b = create_store(tenant_b)
    
    # Try to access Tenant B's store while authenticated as Tenant A user
    response = client.get(
        f'/api/v1/stores/{store_b.id}',
        headers={'Authorization': f'Bearer {tenant_a_token}'}
    )
    
    assert response.status_code == 404  # Or 403, depending on your design
```

---

## Error Handling & Security

### Tenant-Aware Error Responses

**Never leak cross-tenant information in errors.**

**Bad:**
```json
{
  "error": "Store abc-123 belongs to tenant XYZ Corp, not your tenant"
}
```

**Good:**
```json
{
  "error": "Store not found"
}
```

**Error Response Standards:**
```python
# Resource doesn't exist OR doesn't belong to current tenant
# Both cases return the same error
404 Not Found: {"error": "Resource not found"}

# User lacks permission
403 Forbidden: {"error": "Insufficient permissions"}

# Tenant suspended/canceled
403 Forbidden: {"error": "Account suspended. Contact support."}

# Authentication failed
401 Unauthorized: {"error": "Invalid credentials"}
```

### Token Revocation

**Problem:** JWTs are stateless - you can't "revoke" them without additional infrastructure.

**Solutions:**

**Option 1: Short-lived tokens + Refresh tokens**
- Access tokens expire in 15 minutes
- Refresh tokens stored in database (can be revoked)
- Revoke refresh token → user must re-authenticate after current access token expires

**Option 2: Token blacklist**
- Store revoked token IDs in Redis with TTL matching token expiration
- Check blacklist on every request (adds latency)

**Option 3: Version-based invalidation**
- Add `token_version` to User model
- Include in JWT payload
- Increment `token_version` when you need to revoke all user's tokens
- Reject tokens with old version number

**Recommended:** Combination of Option 1 (refresh tokens) + Option 3 (version field for emergency revocation).

---

## What's NOT Included in This Core System

This foundation intentionally excludes business features. You'll add these later as feature modules:

**Not Included:**
- ❌ Billing/Payments (Stripe integration, subscription management)
- ❌ Inventory Management
- ❌ Invoicing
- ❌ Reporting/Analytics
- ❌ Email notifications (except auth-related)
- ❌ File uploads/storage
- ❌ Webhooks
- ❌ API rate limiting
- ❌ Advanced audit logging
- ❌ Multi-factor authentication (add later as enhancement)

**The Power of This Approach:**
Once this core is solid, adding a "Products" module means:
1. Create `Product` model with `tenant_id` and `store_id`
2. Create `ProductService` and routes
3. The middleware automatically handles all security

No need to rewrite authentication, authorization, or tenant isolation logic.

---

## Common Pitfalls & Troubleshooting

### Pitfall 1: Forgetting to Index `tenant_id`

**Symptom:** Queries become slow as data grows

**Solution:** 
```sql
CREATE INDEX idx_stores_tenant_id ON stores(tenant_id);
CREATE INDEX idx_roles_tenant_id ON roles(tenant_id);
-- Add to ALL tenant-scoped tables
```

### Pitfall 2: N+1 Query Problems

**Symptom:** Loading users with their roles causes dozens of queries

**Solution:** Use eager loading
```python
# Bad
users = User.query.all()
for user in users:
    print(user.roles)  # Triggers separate query for each user

# Good
users = User.query.options(joinedload('roles')).all()
```

### Pitfall 3: Circular Dependencies in Middleware

**Symptom:** Importing models in middleware causes import errors

**Solution:** Import models inside functions, not at module level
```python
def tenant_middleware():
    from app.models import Tenant  # Import here, not at top
    # ...
```

### Pitfall 4: Not Handling Multi-Tenant Users

**Symptom:** User belongs to multiple tenants, app assumes they're in one

**Solution:** Always require explicit tenant selection during login, or let user switch tenants via API.

### Pitfall 5: Hardcoding Tenant IDs

**Symptom:** Test data or config contains specific tenant UUIDs

**Solution:** Always use context from middleware. Never reference specific tenant IDs in application code.

---

## Deployment Checklist

Before going to production:

- [ ] All tenant-scoped tables have `tenant_id` indexed
- [ ] SQLAlchemy query filter hook is active
- [ ] Bootstrap endpoint is disabled (or protected)
- [ ] Permissions are seeded
- [ ] Default "Owner" role is created during tenant registration
- [ ] JWT secret is strong and environment-specific
- [ ] Token expiration times are configured
- [ ] HTTPS is enforced
- [ ] CORS is properly configured
- [ ] Rate limiting is in place for auth endpoints
- [ ] Database backups are configured
- [ ] Monitoring for failed login attempts
- [ ] Logging for tenant switching events
- [ ] Error messages don't leak tenant information

---

## Next Steps: Adding Your First Feature Module

Let's say you want to add a "Products" feature:

### Step 1: Create the Model
```python
class Product(BaseModel):
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey('tenants.id'), nullable=False, index=True)
    store_id = Column(UUID, ForeignKey('stores.id'), nullable=False, index=True)
    name = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    # ... audit fields
```

### Step 2: Define Permissions
```python
# Add to config/permissions.py
("products.create", "products", "create", "Create products"),
("products.view", "products", "view", "View products"),
("products.edit", "products", "edit", "Edit products"),
("products.delete", "products", "delete", "Delete products"),
```

### Step 3: Create Service
```python
class ProductService:
    @require_permission('products.create')
    def create_product(name, sku, price, store_id):
        # tenant_id comes from context automatically
        product = Product(
            tenant_id=g.tenant_id,  # From middleware
            store_id=store_id,
            name=name,
            sku=sku,
            price=price
        )
        # Save, return
```

### Step 4: Create Routes
```python
@app.route('/api/v1/products', methods=['POST'])
@require_auth  # Runs TenantMiddleware
@require_store  # Runs StoreMiddleware if X-Store-ID header present
def create_product():
    data = request.json
    product = ProductService.create_product(**data)
    return jsonify(product), 201
```

**That's it.** The core system handles:
- ✅ Authentication
- ✅ Tenant context
- ✅ Store context
- ✅ Permission checking
- ✅ Automatic query filtering

You only wrote feature-specific code.

---

## Conclusion

This core system is your SaaS application's foundation. It provides:
- **Security:** Multi-layered tenant isolation
- **Flexibility:** Fine-grained RBAC
- **Scalability:** Clean separation between infrastructure and features
- **Maintainability:** Centralized security logic

Build this once, build it well, and you'll be able to iterate on features rapidly without compromising on security or architecture.

**Remember:** This is infrastructure. It should be boring, predictable, and bulletproof. Save the innovation for your business features.