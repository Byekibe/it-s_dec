# Core Architecture & Reuse Strategy

**Created**: 2025-12-12

This document outlines the architecture of the multi-tenant SaaS core and how it can be reused across different applications (POS, Property Management, etc.).

---

## What is the "Core"?

The core is a **complete, reusable multi-tenant SaaS foundation** that provides everything a B2B SaaS application needs except domain-specific business logic.

### Core Components (Implemented)

| Component | Status | Description |
|-----------|--------|-------------|
| Multi-tenancy | ✅ Done | Tenant isolation, middleware, scoped models |
| Authentication | ✅ Done | JWT, login, register, password reset, email verification |
| User Management | ✅ Done | CRUD, invitations, multi-tenant users |
| RBAC | ✅ Done | Roles, permissions, tenant & store-level |
| Store/Location | ✅ Done | Multi-store support within tenants |
| Subscriptions | ✅ Done | Plans, limits, usage tracking |
| Settings | ✅ Done | Tenant and store settings |

### Core Components (To Complete)

| Component | Priority | Description |
|-----------|----------|-------------|
| Audit Logging | High | Track who did what, when (compliance, debugging) |
| Notifications | High | In-app, email, push notifications |
| File Storage | Medium | Attachments, uploads, avatars |
| Webhooks | Medium | Event notifications to external systems |
| API Keys | Medium | Service-to-service authentication |
| Billing/Invoicing | Low | Generic invoicing (app-specific billing varies) |

---

## Directory Structure

```
backend/
├── app/
│   ├── core/                    # CORE: Framework utilities
│   │   ├── models.py            # Base models (TenantScoped, StoreScoped)
│   │   ├── middleware.py        # Tenant/Store context
│   │   ├── decorators.py        # Auth, permissions, limits
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── utils.py             # JWT, helpers
│   │   ├── constants.py         # Permissions, defaults
│   │   ├── celery.py            # Background tasks
│   │   ├── email.py             # Email service
│   │   └── tasks.py             # Celery tasks
│   │
│   ├── blueprints/
│   │   ├── # ===== CORE BLUEPRINTS (Reusable) =====
│   │   ├── auth/                # Authentication
│   │   ├── users/               # User management
│   │   ├── tenants/             # Tenant management
│   │   ├── stores/              # Store/location management
│   │   ├── rbac/                # Roles & permissions
│   │   ├── subscriptions/       # Plans & subscriptions
│   │   ├── audit/               # Audit logging (TODO)
│   │   ├── notifications/       # Notifications (TODO)
│   │   ├── files/               # File storage (TODO)
│   │   ├── webhooks/            # Webhook management (TODO)
│   │   ├── health/              # Health checks
│   │   │
│   │   ├── # ===== APP-SPECIFIC BLUEPRINTS =====
│   │   ├── # POS App:
│   │   ├── products/            # Product catalog
│   │   ├── inventory/           # Stock management
│   │   ├── sales/               # Transactions, receipts
│   │   ├── payments/            # M-Pesa, cash, etc.
│   │   │
│   │   ├── # Property Management App:
│   │   ├── properties/          # Buildings, complexes
│   │   ├── units/               # Apartments, rooms
│   │   ├── leases/              # Rental agreements
│   │   ├── maintenance/         # Work orders
```

---

## How to Create a New App from Core

### Step 1: Copy the Core

When starting a new SaaS app (e.g., Property Management):

```bash
# Create new project
mkdir property-saas && cd property-saas

# Copy core from template
cp -r /path/to/core-template/backend ./backend

# The core includes:
# - All core blueprints (auth, users, tenants, stores, rbac, subscriptions)
# - Core utilities (middleware, decorators, exceptions)
# - Database migrations for core tables
# - Test fixtures and base tests
```

### Step 2: Add App-Specific Blueprints

```bash
# Create app-specific blueprints
mkdir -p backend/app/blueprints/properties
mkdir -p backend/app/blueprints/units
mkdir -p backend/app/blueprints/leases
```

### Step 3: Define App-Specific Models

```python
# backend/app/blueprints/properties/models.py
from app.core.models import TenantScopedModel

class Property(TenantScopedModel):
    """Property belongs to a tenant."""
    __tablename__ = 'properties'

    name = Column(String(200), nullable=False)
    address = Column(Text)
    # ... property-specific fields
```

### Step 4: Add App-Specific Permissions

```python
# backend/app/core/constants.py (extend)

# Add to Permissions class:
PROPERTIES_VIEW = "properties.view"
PROPERTIES_CREATE = "properties.create"
UNITS_VIEW = "units.view"
LEASES_MANAGE = "leases.manage"
```

### Step 5: Create Migration

```bash
flask db migrate -m "Add property management tables"
flask db upgrade
```

---

## Reuse Patterns

### Pattern 1: Tenant-Scoped Entities

All business entities should inherit from `TenantScopedModel`:

```python
from app.core.models import TenantScopedModel

class Product(TenantScopedModel):  # POS
    __tablename__ = 'products'
    # Automatically has: tenant_id, created_by, updated_by, deleted_at

class Property(TenantScopedModel):  # Property Management
    __tablename__ = 'properties'
    # Same automatic fields
```

### Pattern 2: Store-Scoped Entities

For entities that belong to a specific store/location:

```python
from app.core.models import StoreScopedModel

class InventoryItem(StoreScopedModel):  # POS
    __tablename__ = 'inventory'
    # Has: tenant_id, store_id, created_by, updated_by, deleted_at

class Unit(StoreScopedModel):  # Property Management
    __tablename__ = 'units'
    # (if stores represent properties)
```

### Pattern 3: Permission-Protected Routes

```python
from app.core.decorators import require_permission
from app.core.constants import Permissions

@bp.route("/products", methods=["POST"])
@require_permission(Permissions.PRODUCTS_CREATE)
def create_product():
    # Only users with products.create permission can access
    pass
```

### Pattern 4: Subscription Limits

```python
from app.core.decorators import require_can_add_store

@bp.route("/stores", methods=["POST"])
@require_permission(Permissions.STORES_CREATE)
@require_can_add_store  # Checks plan limits
def create_store():
    pass
```

---

## Database Strategy

### Current Approach: Shared Database with tenant_id

All tenants share the same database. Data isolation is enforced by:

1. **Middleware**: Sets `g.tenant` from JWT token
2. **TenantScopedModel**: All models have `tenant_id` column
3. **Query Filtering**: Services filter by `tenant_id`

**Pros:**
- Simple to implement and maintain
- Easy cross-tenant reporting (for super admin)
- Single database to backup/manage

**Cons:**
- Large tenants can impact performance
- No true data isolation (depends on code correctness)

### Future Options (If Needed)

**Schema-per-tenant**: Each tenant gets their own PostgreSQL schema
- Better isolation
- More complex migrations

**Database-per-tenant**: Each tenant gets their own database
- Complete isolation
- Most complex, highest operational overhead

For most Kenyan SME SaaS applications, the **shared database approach is sufficient** and recommended until you have 1000+ tenants or specific compliance requirements.

---

## Core vs App-Specific: Decision Guide

**Include in Core if:**
- Every multi-tenant SaaS app needs it
- It's generic (not domain-specific)
- It relates to users, access, or infrastructure

**Keep App-Specific if:**
- It's domain logic (products, properties, leases)
- It varies significantly between apps
- It's business workflow (POS checkout flow vs lease signing)

### Examples

| Feature | Core or App-Specific? | Reason |
|---------|----------------------|--------|
| User authentication | Core | Every app needs it |
| Role-based permissions | Core | Every app needs access control |
| Audit logging | Core | Compliance/debugging universal |
| Product catalog | App (POS) | Domain-specific |
| Lease management | App (Property) | Domain-specific |
| M-Pesa payments | Could be Core | Common in Kenya, reusable |
| Inventory tracking | App (POS) | Domain-specific logic |

---

## Testing Strategy for Core

The core should have comprehensive tests that any app inherits:

```
tests/
├── # CORE TESTS (run for all apps)
├── test_auth.py              # Authentication flows
├── test_tenant_isolation.py  # Multi-tenancy security
├── test_rbac.py              # Permission system
├── test_subscriptions.py     # Plan limits
├── conftest.py               # Shared fixtures
│
├── # APP-SPECIFIC TESTS (added per app)
├── test_products.py          # POS-specific
├── test_inventory.py         # POS-specific
```

---

## Versioning the Core

As the core evolves, maintain compatibility:

1. **Semantic versioning**: MAJOR.MINOR.PATCH
   - MAJOR: Breaking changes to core APIs
   - MINOR: New core features (backward compatible)
   - PATCH: Bug fixes

2. **Migration compatibility**: New migrations should not break existing apps

3. **Deprecation policy**: Mark features as deprecated before removing

---

## Next Steps to Complete Core

See `todo.md` for detailed tasks. High-level:

1. **Audit Logging** - Track all data changes
2. **Notifications System** - In-app + email notifications
3. **File Storage** - Generic file upload/download
4. **Webhooks** - Event notifications
5. **API Keys** - Machine-to-machine auth
6. **Documentation** - OpenAPI/Swagger docs
