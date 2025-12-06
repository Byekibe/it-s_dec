# Building the Core System: A Step-by-Step Guide

This document outlines the architectural approach and step-by-step process for building the core foundation of a multi-tenant, multi-store SaaS application with Role-Based Access Control (RBAC).

## Introduction: The "Operating System" Analogy

Think of this core system as the **Operating System (OS)** for our application. It doesn't handle specific business features like "Inventory" or "Billing" itself. Instead, it provides the foundational services that all other feature modules will run on top of:
*   **Identity & Security:** Who is this user?
*   **Tenancy:** Which company do they belong to?
*   **Authorization:** What are they allowed to do?

By building this robust OS first, we can later add new features ("apps") quickly and securely, without having to reinvent the security and data isolation logic each time.

---

## The Step-by-Step Build Process

Building this core system follows a logical progression from the abstract data structure to the concrete application entry point.

### Step 1: Define the Core Data Models (The Blueprint)

This is the absolute first step. The models are the blueprint of our data world, defining the primary entities and their relationships.

#### Primary Entity Models
*   **`User`**: The global model for a person who can log in.
*   **`Tenant`**: The top-level entity representing a company. This is the primary container for data segregation.
*   **`Store`**: A specific location or branch that **must** belong to a single `Tenant`.
*   **`Role`**: A named set of permissions (e.g., "Admin", "Store Manager") that is defined **within a `Tenant`**.
*   **`Permission`**: A single, granular action (e.g., `products.edit`). These are usually defined globally by the system.

#### Junction (Link) Models
These tables are the glue that connects the primary entities.
*   **`TenantUser`**: Links a `User` to a `Tenant`.
*   **`StoreUser`**: Links a `User` to a `Store` they can access.
*   **`UserRole`**: Assigns a `Role` to a `User`, either for the entire tenant or for a specific `Store`.
*   **`RolePermission`**: Links many `Permissions` to a `Role`.

---

### Step 2: Implement the Context & Security Middleware (The Gatekeeper)

Once the models define the *rules* of data separation, the middleware *enforces* those rules on every API request. It acts as a security checkpoint.

*   **`TenantMiddleware`**: Its job is to identify the tenant for the current request (usually from a JWT token). It validates that the tenant exists and is active, then establishes a secure, request-wide `TenantContext`. If this check fails, the request is stopped immediately.

*   **`StoreMiddleware`**: This runs *after* the `TenantMiddleware`. If a specific store is requested (e.g., via an `X-Store-ID` header), it verifies that the current user has access to that store within the already-validated tenant. It then establishes the `StoreContext`.

### Advanced: Implementing an Automatic Query Filter (SQLAlchemy Hook)

To provide a final, non-bypassable layer of security, you can implement a SQLAlchemy event hook. This is a powerful pattern that automatically scopes all relevant database queries.

*   **Purpose:** To act as an ultimate safety net, ensuring no data can be accessed outside the current tenant's scope during a web request, even if a developer forgets a filter in their code.
*   **Mechanism:** Using SQLAlchemy's event system (`@event.listens_for(Session, 'do_orm_execute')`), you create a function that intercepts every query before it is sent to the database.
*   **Logic:**
    1.  The hook checks if it's running within a request context that has a valid `tenant_id`.
    2.  It inspects the query to see if it targets a tenant-scoped model (like `Store` or `Role`).
    3.  If both are true, it **automatically injects the `WHERE tenant_id = ...` clause** into the query.
*   **Benefit:** This makes your application logic cleaner (e.g., `Store.query.all()` is safe within a request) and adds a robust layer of defense against accidental data leaks.

---

### Step 3: Build the Application's Entry Point (Authentication)

With the data structure and security enforcement in place, you need a way for the first user to get into the system. This involves creating the first pieces of business logic.

1.  **Create an `AuthenticationService`**:
    *   This service contains the core logic for `register()` and `login()`.
    *   The `register` function is critical: it creates a `User`, their first `Tenant`, links them, and assigns them a default "Owner" `Role`.
    *   The `login` function validates credentials and generates a **JWT (JSON Web Token)** that contains the `user_id` and `tenant_id`.

2.  **Create API Routes:**
    *   `POST /api/v1/auth/register`
    *   `POST /api/v1/auth/login`

This step is vital because it closes the loop: a user logs in, receives a token, and that token is then used by the `TenantMiddleware` in all future requests to establish their identity and context.

### Critical Implementation Notes

**Initial Bootstrap Problem**: The very first user/tenant must be created outside the normal middleware flow. Create a separate `bootstrap.py` script or a special `POST /api/v1/auth/bootstrap` endpoint that bypasses tenant middleware for the initial setup only. Disable this after first use.

**Permission Seeding**: Permissions should be code-defined (not user-created) and seeded via migration scripts. Use a naming convention like `resource.action` (e.g., `products.create`, `stores.edit`, `invoices.view`).

---

### Step 4: Develop Core Resource Management APIs

Now that users can log in and have a secure context, you can build the APIs needed to manage the core entities.

*   **RBAC Management:** Endpoints to create `Roles`, assign `Permissions` to them, and assign `Roles` to users.
*   **User Management:** Endpoints to invite new users to the current tenant.
*   **Store Management:** Endpoints for a tenant admin to create, view, and update the `Stores` within their tenant.

---

## The Result: A Secure Foundation

By following these steps, you create a solid foundation. Adding a new feature module like `Billing` or `Inventory` becomes simple:

1.  Create the feature-specific models (e.g., `Invoice`, `Product`) and ensure they are linked to a `Tenant` (and `Store`, if applicable).
2.  Create the feature-specific services and routes.
3.  The core middleware automatically handles all the security and data isolation, because your new services can simply trust the context to get the correct `tenant_id`.

---

## 📁 Project Structure

## 📁 Updated Complete Project Structure

```
backend/
├── app/
│   ├── __init__.py                      # Application factory with all blueprint registrations
│   ├── config.py                        # Environment-based configuration classes
│   ├── extensions.py                    # Flask extensions initialization (db, mail, etc.)
│   ├── error_handlers.py                # Global error handlers (404, 500, custom exceptions)
│   ├── container.py                     # Dependency injection container setup
│   │
│   ├── core/                            # Core application logic
│   │   ├── __init__.py
│   │   ├── models.py                    # BaseModel, TenantMixin, TimestampMixin
│   │   ├── exceptions.py                # Custom exceptions (NotFoundError, ForbiddenError, etc.)
│   │   ├── validators.py                # Custom validators (email, password strength, etc.)
│   │   ├── decorators.py                # @jwt_required, @require_permission, @require_feature
│   │   ├── middleware.py                # Tenant context extraction, request logging
│   │   ├── constants.py                 # Application constants (roles, permissions, statuses)
│   │   └── utils.py                     # JWT utilities, password hashing, helpers
│   │
│   ├── cli/                             # CLI commands for management
│   │   ├── __init__.py
│   │   ├── db_commands.py               # flask db-init, flask seed-db, flask db-reset
│   │   ├── user_commands.py             # flask user create, flask user assign-role
│   │   └── tenant_commands.py           # flask tenant create, flask tenant seed-roles
│   │
│   ├── tasks/                           # Background tasks (Celery/async)
│   │   ├── __init__.py
│   │   ├── celery_app.py                # Celery configuration and app
│   │   ├── email_tasks.py               # Send emails (verification, password reset)
│   │   ├── billing_tasks.py             # Process renewals, generate invoices
│   │   └── usage_tasks.py               # Aggregate usage metrics
│   │
│   ├── blueprints/                      # Feature modules (business logic)
│   │   │
│   │   ├── api/                         # API versioning wrapper
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       └── __init__.py          # Registers all v1 blueprints
│   │   │
│   │   ├── health/                      # Health check endpoints
│   │   │   ├── __init__.py
│   │   │   └── routes.py                # GET /health, GET /health/db
│   │   │
│   │   ├── auth/                        # Authentication
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # register, login, refresh, forgot-password, reset-password
│   │   │   ├── services.py              # AuthService (login, register, token generation)
│   │   │   ├── schemas.py               # LoginSchema, RegisterSchema, PasswordResetSchema
│   │   │   └── models.py                # PasswordResetToken model
│   │   │
│   │   ├── users/                       # User management
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # GET /me, PUT /me, GET /users (admin)
│   │   │   ├── services.py              # UserService (CRUD operations)
│   │   │   ├── repositories.py          # UserRepository (data access with tenant filtering)
│   │   │   ├── schemas.py               # UserSchema, UpdateProfileSchema
│   │   │   └── models.py                # User model (in core/models or here)
│   │   │
│   │   ├── tenants/                     # Tenant management
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # POST /tenants, GET /tenants/current, PUT /tenants/current
│   │   │   ├── services.py              # TenantService (create, update, deactivate)
│   │   │   ├── repositories.py          # TenantRepository
│   │   │   ├── schemas.py               # TenantSchema, CreateTenantSchema
│   │   │   └── models.py                # Tenant model
│   │   │
│   │   ├── stores/                      # Store management
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # POST /stores, GET /stores, PUT /stores/:id
│   │   │   ├── services.py              # StoreService (CRUD operations)
│   │   │   ├── repositories.py          # StoreRepository
│   │   │   ├── schemas.py               # StoreSchema, CreateStoreSchema
│   │   │   └── models.py                # Store model
│   │   │
│   │   ├── rbac/                        # Role-based access control
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # GET /roles, POST /roles, POST /users/:id/roles
│   │   │   ├── services.py              # RBACService (check permissions, assign roles)
│   │   │   ├── repositories.py          # RoleRepository, PermissionRepository
│   │   │   ├── schemas.py               # RoleSchema, PermissionSchema
│   │   │   └── models.py                # Role, Permission, UserRole, RolePermission
│   │   │
│   │   ├── subscriptions/               # Subscription management
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # GET /subscriptions/current, PUT /subscriptions/current
│   │   │   ├── services.py              # SubscriptionService (create, update, cancel, check_feature)
│   │   │   ├── repositories.py          # SubscriptionRepository, PlanRepository
│   │   │   ├── schemas.py               # SubscriptionSchema, PlanSchema
│   │   │   └── models.py                # Subscription, Plan, Feature, PlanFeature
│   │   │
│   │   ├── billing/                     # Billing and invoicing
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # GET /billing/history, GET /billing/invoices
│   │   │   ├── services.py              # BillingService (generate invoices, calculate charges)
│   │   │   ├── repositories.py          # PaymentTransactionRepository
│   │   │   ├── schemas.py               # InvoiceSchema, TransactionSchema
│   │   │   └── models.py                # PaymentTransaction, Invoice
│   │   │
│   │   ├── payments/                    # Payment processing
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # POST /payments/mpesa/initiate, POST /payments/mpesa-callback
│   │   │   ├── services.py              # PaymentService (initiate payment, handle callback)
│   │   │   ├── mpesa.py                 # M-Pesa Daraja API integration
│   │   │   └── schemas.py               # PaymentRequestSchema
│   │   │
│   │   ├── onboarding/                  # SaaS onboarding flow
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # POST /onboarding/register
│   │   │   ├── services.py              # OnboardingService (create tenant + user + subscription)
│   │   │   └── schemas.py               # OnboardingSchema
│   │   │
│   │   ├── usage/                       # Usage tracking and metering
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # GET /usage/current, GET /usage/history
│   │   │   ├── services.py              # UsageTrackingService (track events, check limits)
│   │   │   ├── repositories.py          # UsageMetricRepository, UsageEventRepository
│   │   │   ├── schemas.py               # UsageMetricSchema
│   │   │   └── models.py                # UsageMetric, UsageEvent
│   │   │
│   │   └── notifications/               # Notification system
│   │       ├── __init__.py
│   │       ├── routes.py                # GET /notifications, PUT /notifications/:id/read
│   │       ├── services.py              # NotificationService (send, mark_read)
│   │       ├── repositories.py          # NotificationRepository
│   │       ├── schemas.py               # NotificationSchema
│   │       └── models.py                # Notification, NotificationTemplate
│   │
│   └── docs/                            # API documentation
│       └── swagger.py                   # OpenAPI/Swagger specs
│
├── tests/                               # Test suites
│   ├── conftest.py                      # Pytest fixtures (test client, db, tenants)
│   ├── test_auth.py                     # Authentication tests
│   ├── test_users.py                    # User management tests
│   ├── test_tenants.py                  # Tenant isolation tests
│   ├── test_rbac.py                     # RBAC tests
│   ├── test_subscriptions.py            # Subscription tests
│   └── test_payments.py                 # Payment integration tests
│
├── migrations/                          # Alembic migrations
│   ├── versions/                        # Migration files
│   ├── env.py                           # Migration environment
│   └── alembic.ini                      # Alembic configuration
│
├── logs/                                # Application logs
│   ├── app.log
│   └── error.log
│
├── config/                              # Configuration files
│   ├── development.py
│   ├── testing.py
│   └── production.py
│
├── .env.example                         # Environment variables template
├── .env                                 # Environment variables (gitignored)
├── .gitignore
├── requirements.txt                     # Production dependencies
├── requirements-dev.txt                 # Development dependencies
├── Dockerfile                           # Docker configuration
├── docker-compose.yml                   # Docker Compose for local development
├── pytest.ini                           # Pytest configuration
└── run.py                               # Development server entry point
```
---