# Flask Multi-Tenant REST API Template

> A production-ready, multi-tenant Flask REST API template using Factory Pattern, Repository Pattern, and comprehensive RBAC with tenant isolation.

## 📋 Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Multi-Tenancy Approach](#multi-tenancy-approach)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Configuration](#configuration)
- [Database Models](#database-models)
- [API Endpoints](#api-endpoints)
- [Authentication Flow](#authentication-flow)
- [RBAC System](#rbac-system)
- [Tenant Management](#tenant-management)
- [Usage Examples](#usage-examples)
- [CLI Commands](#cli-commands)
- [Development Guide](#development-guide)

---

## ✨ Features

- **Multi-Tenant Architecture** - Discriminator pattern with tenant_id isolation
- **Multi-Store Support** - Allow a single tenant to manage multiple stores
- **SaaS Subscription & Billing** - Plan management, feature gating, and payment integration.
- **Flask Factory Pattern** - Scalable application architecture
- **JWT Authentication** - Secure token-based auth with PyJWT
- **RBAC System** - Role-Based Access Control with tenant-scoped permissions
- **Repository Pattern** - Clean separation of data access logic
- **Service Layer** - Business logic isolation
- **Email Integration** - Password reset & verification flows
- **Database Migrations** - Alembic-powered schema management
- **Health Checks** - Application monitoring endpoints
- **CLI Tools** - Database, user, and tenant management commands
- **Comprehensive Error Handling** - Structured error responses
- **Environment-based Configuration** - Development, Testing, Production
- **API Versioning** - `/api/v1/` endpoint structure
- **Tenant Isolation** - Automatic tenant filtering on all queries

---

## 🏗️ Architecture

### Design Patterns

#### 1. **Factory Pattern**
The application uses Flask's factory pattern for flexible initialization:
```
create_app(config_name) → Flask Application Instance
```

#### 2. **Repository Pattern**
Data access is abstracted through repositories with automatic tenant and store filtering:
```
Controller → Service → Repository → Database (filtered by tenant_id and store_id)
```

## 📦 Updated Repository Pattern

### Base Repository with Store Context

```python
# app/core/repositories.py
from flask import g
from app.extensions import db
from app.core.exceptions import BadRequestError

class BaseRepository:
    """Base repository with automatic tenant and store filtering"""
    
    def __init__(self, model):
        self.model = model
    
    def get_all(self, store_scoped=True):
        """Get all records with tenant (and optionally store) filtering"""
        query = self.model.query.filter_by(
            tenant_id=g.current_tenant_id,
            deleted_at=None
        )
        
        # Apply store filtering if model has store_id
        if store_scoped and hasattr(self.model, 'store_id'):
            if not g.current_store_id:
                raise BadRequestError(
                    f"{self.model.__name__} requires store context. "
                    "Please provide X-Store-ID header."
                )
            query = query.filter_by(store_id=g.current_store_id)
        
        return query.all()
    
    def get_by_id(self, id, store_scoped=True):
        """Get record by ID with tenant and store validation"""
        filters = {
            'id': id,
            'tenant_id': g.current_tenant_id,
            'deleted_at': None
        }
        
        if store_scoped and hasattr(self.model, 'store_id'):
            if not g.current_store_id:
                raise BadRequestError("Store context required")
            filters['store_id'] = g.current_store_id
        
        return self.model.query.filter_by(**filters).first()
    
    def create(self, data, store_scoped=True):
        """Create record with automatic tenant and store injection"""
        data['tenant_id'] = g.current_tenant_id
        
        if store_scoped and hasattr(self.model, 'store_id'):
            if not g.current_store_id:
                raise BadRequestError("Store context required for creation")
            data['store_id'] = g.current_store_id
        
        instance = self.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    def update(self, id, data, store_scoped=True):
        """Update record with store validation"""
        instance = self.get_by_id(id, store_scoped=store_scoped)
        if not instance:
            return None
        
        for key, value in data.items():
            if hasattr(instance, key) and key not in ['id', 'tenant_id', 'store_id']:
                setattr(instance, key, value)
        
        db.session.commit()
        return instance
```

#### 3. **Dependency Injection**
Services and repositories are injected through the DI container.

### Request Flow
```
HTTP Request
    ↓
Tenant Context Middleware (extract tenant_id from token/header)
    ↓
Store Context Middleware (extract store_id from X-Store-ID header, validate access)
    ↓
Route (Blueprint)
    ↓
Service Layer (Business Logic + Tenant/Store Validation)
    ↓
Repository Layer (Data Access + Automatic Tenant & Store Filtering)
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL Database
```

---

## 🏢 Multi-Tenancy Approach

### Discriminator Pattern (Shared Database, Shared Schema)

All tenant data is stored in the same database and tables, isolated by a `tenant_id` column.

#### Advantages
- **Cost-effective** - Single database to maintain
- **Easy to scale horizontally** - No schema management per tenant
- **Simple backups** - One database backup strategy
- **Cross-tenant analytics** - Easy to aggregate data

#### Implementation Strategy

1. **Tenant ID Column**: Every tenant-scoped table includes a `tenant_id` foreign key
2. **Automatic Filtering**: Repository layer automatically filters by tenant_id
3. **Middleware**: Tenant context extracted from JWT token
4. **Row-Level Security**: Database constraints prevent cross-tenant data access

#### Tenant Context Flow
```python
# 1. User authenticates
POST /api/v1/auth/login
→ JWT token includes: {user_id, tenant_id, roles}

# 2. Subsequent requests include token
GET /api/v1/users/me
Authorization: Bearer <token>

# 3. Middleware extracts tenant_id from token
g.current_tenant_id = decoded_token['tenant_id']

# 4. Repository automatically filters queries
SELECT * FROM users WHERE tenant_id = g.current_tenant_id
```

---

## 🛡️ Updated Middleware

### Complete Middleware Implementation

```python
# app/core/middleware.py
from flask import g, request, jsonify
from app.core.exceptions import ForbiddenError, BadRequestError
from app.blueprints.stores.models import Store
from app.blueprints.users.models import UserStore

def extract_tenant_context():
    """Extract tenant_id from JWT token"""
    # This is set by @jwt_required decorator
    # g.current_tenant_id and g.current_user_id are already set
    pass

def extract_store_context():
    """Extract and validate store_id from request header"""
    # Skip if not authenticated
    if not hasattr(g, 'current_user_id'):
        return
    
    store_id = request.headers.get('X-Store-ID')
    
    if store_id:
        try:
            store_id = int(store_id)
        except ValueError:
            return jsonify({"error": "Invalid store ID format"}), 400
        
        # Verify store exists and belongs to tenant
        store = Store.query.filter_by(
            id=store_id,
            tenant_id=g.current_tenant_id,
            is_active=True,
            deleted_at=None
        ).first()
        
        if not store:
            return jsonify({"error": "Store not found or inactive"}), 404
        
        # Verify user has access to this store
        user_store = UserStore.query.filter_by(
            user_id=g.current_user_id,
            store_id=store_id
        ).first()
        
        if not user_store:
            return jsonify({"error": "Access denied to this store"}), 403
        
        g.current_store_id = store_id
        g.current_store = store
    else:
        g.current_store_id = None
        g.current_store = None

# Register middleware in app factory
def create_app(config_name='development'):
    app = Flask(__name__)
    # ... other setup ...
    
    app.before_request(extract_store_context)
    
    return app
```

---

## 🏢 Multi-Store Approach

While the system is multi-tenant, it also supports a multi-store architecture, allowing a single tenant to manage multiple storefronts or business units.

### Store-Level Resource Isolation

- **Tenant as the Umbrella**: A `Tenant` represents a single business or organization.
- **Store as a Business Unit**: Each `Tenant` can own multiple `Store` entities. Each store has its own domain, settings, and isolated resources.
- **Store-Scoped Resources**: Models like `Product`, `Order`, `Category`, and `Customer` are linked to a `Store` (and by extension, a `Tenant`).
- **User-Store Access Control**: Users are explicitly granted access to specific stores via the `UserStore` model.

### Store Context Flow

The application identifies the current store through the `X-Store-ID` header, NOT from the JWT token.

```python
# 1. User authenticates for a tenant
POST /api/v1/auth/login
→ JWT token includes: {user_id, tenant_id, roles}
→ Response includes: accessible stores list

# 2. Client selects a store and sends store_id in header
GET /api/v1/products
Authorization: Bearer <token>
X-Store-ID: <store_id>

# 3. Middleware extracts and validates store_id
@app.before_request
def extract_store_context():
    store_id = request.headers.get('X-Store-ID')
    if store_id:
        # Verify user has access via UserStore table
        has_access = UserStore.query.filter_by(
            user_id=g.current_user_id,
            store_id=int(store_id)
        ).first()
        
        if not has_access:
            raise ForbiddenError("Access denied to this store")
        
        g.current_store_id = int(store_id)
    else:
        g.current_store_id = None

# 4. Repository automatically filters by store_id (if required)
SELECT * FROM products 
WHERE tenant_id = g.current_tenant_id 
  AND store_id = g.current_store_id
```

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

## 🚀 Setup Instructions

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Virtual environment tool (venv/virtualenv)

### Installation

1. **Clone and Navigate**
```bash
cd backend
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configurations
```

5. **Database Setup**
```bash
# Create PostgreSQL database
createdb flask_template_dev

# Run migrations
flask db upgrade

# Seed initial data (optional)
flask seed-db
```

6. **Run Development Server**
```bash
python run.py
# Or using Flask CLI
flask run
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `development` |
| `SECRET_KEY` | Flask secret key | `your-secret-key` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@localhost/dbname` |
| `JWT_SECRET_KEY` | JWT signing key | `your-jwt-secret` |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token lifetime | `3600` (seconds) |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token lifetime | `2592000` (30 days) |
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USERNAME` | Email username | `your-email@gmail.com` |
| `MAIL_PASSWORD` | Email password | `your-app-password` |
| `MAIL_USE_TLS` | Use TLS | `True` |
| `MAIL_DEFAULT_SENDER` | Default sender | `noreply@yourapp.com` |

### Technology Stack

- **Authentication**: PyJWT (not Flask-JWT-Extended)
- **Password Hashing**: Werkzeug (not bcrypt)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Email**: Flask-Mail
- **Validation**: Marshmallow

### Configuration Classes

- **DevelopmentConfig** - Debug enabled, verbose logging
- **TestingConfig** - Testing database, disabled CSRF
- **ProductionConfig** - Secure settings, error logging

---

## 💾 Database Models

### Core Models

#### **Tenant Model**
```python
- id: Integer (PK)
- name: String (Unique)
- slug: String (Unique, Indexed)
- domain: String (Nullable)
- is_active: Boolean
- settings: JSON (Tenant-specific configurations)
- subscription_id: Integer (FK -> subscriptions.id, Nullable)
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (Soft delete)
# Relationship
- stores: One-to-Many -> Store Model
```

#### **Store Model** (Tenant-Scoped)
```python
class Store(BaseModel, TenantMixin):
    __tablename__ = 'stores'
    
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    settings = db.Column(db.JSON, default={})
    
    # Relationships
    tenant = db.relationship('Tenant', backref='stores')
    
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'slug', 
                          name='stores_tenant_slug_unique'),
    )
```

#### **UserStore Model** (User-Store Access Control)
```python
class UserStore(BaseModel):
    """Defines which stores a user can access within their tenant"""
    __tablename__ = 'user_stores'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    is_default = db.Column(db.Boolean, default=False)  # User's default store
    
    # Relationships
    user = db.relationship('User', backref='store_assignments')
    store = db.relationship('Store', backref='user_assignments')
    role = db.relationship('Role')  # Store-specific role (optional)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'store_id', 
                          name='user_stores_user_store_unique'),
    )
```

#### **User Model** (Tenant-Scoped)
```python
- id: Integer (PK)
- tenant_id: Integer (FK → tenants.id, Indexed)
- email: String (Indexed)
- username: String (Indexed)
- password_hash: String (hashed with werkzeug.security)
- first_name: String
- last_name: String
- is_active: Boolean
- is_verified: Boolean
- email_verified_at: DateTime
- last_login: DateTime
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (Soft delete)

# Unique constraint: (tenant_id, email)
# Unique constraint: (tenant_id, username)
```

#### **Role Model** (Tenant-Scoped)
```python
- id: Integer (PK)
- tenant_id: Integer (FK → tenants.id, Indexed)
- name: String
- description: String
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime

# Unique constraint: (tenant_id, name)
```

#### **Permission Model** (Global or Tenant-Scoped)
```python
- id: Integer (PK)
- name: String (Unique)
- resource: String
- action: String
- description: String
- created_at: DateTime
- updated_at: DateTime
```

### Subscription and Billing Models

#### **Plan Model**
```python
- id: Integer (PK)
- name: String (Unique)
- slug: String (Unique, Indexed)
- price: Decimal
- currency: String (e.g., "KES", "USD")
- billing_cycle: String (e.g., "monthly", "yearly")
- description: Text
- is_public: Boolean (Visible to customers)
- trial_period_days: Integer (e.g., 14)
- created_at: DateTime
- updated_at: DateTime
```

#### **Feature Model**
```python
- id: Integer (PK)
- name: String (e.g., "Advanced Reporting")
- slug: String (Unique, Indexed, e.g., "advanced_reporting")
- description: Text
```

#### **PlanFeature Model** (Association Table)
```python
- id: Integer (PK)
- plan_id: Integer (FK -> plans.id)
- feature_id: Integer (FK -> features.id)
- limit: Integer (Nullable, e.g., max number of users)
```

#### **Subscription Model**
```python
- id: Integer (PK)
- tenant_id: Integer (FK -> tenants.id, Unique)
- plan_id: Integer (FK -> plans.id)
- status: String (e.g., "trialing", "active", "past_due", "canceled")
- trial_ends_at: DateTime (Nullable)
- starts_at: DateTime
- ends_at: DateTime (Nullable, for fixed-term)
- canceled_at: DateTime (Nullable)
- created_at: DateTime
- updated_at: DateTime
```

#### **PaymentTransaction Model**
```python
- id: Integer (PK)
- tenant_id: Integer (FK -> tenants.id)
- subscription_id: Integer (FK -> subscriptions.id)
- amount: Decimal
- currency: String
- provider: String (e.g., "mpesa")
- provider_transaction_id: String (e.g., M-Pesa Transaction ID)
- status: String (e.g., "pending", "completed", "failed")
- created_at: DateTime
- updated_at: DateTime
```

#### **UserRole Model** (Association Table)
```python
class UserRole(BaseModel):
    """Association between users and roles, optionally scoped to a store"""
    __tablename__ = 'user_roles'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    # If store_id is NULL: role applies tenant-wide
    # If store_id is set: role only applies to that specific store
    
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', 'store_id',
                          name='user_roles_unique'),
    )
```

#### **RolePermission Model** (Association Table)
```python
- id: Integer (PK)
- role_id: Integer (FK → roles.id)
- permission_id: Integer (FK → permissions.id)
- granted_by: Integer (FK → users.id, Nullable)
- granted_at: DateTime
- conditions: JSON (Nullable - for conditional permissions)
- created_at: DateTime
- updated_at: DateTime

# Unique constraint: (role_id, permission_id)
```

### Store-Scoped Models

#### **Product Model** (Tenant & Store-Scoped)
```python
class Product(BaseModel, TenantMixin):
    __tablename__ = 'products'
    
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), 
                         nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    store = db.relationship('Store', backref='products')
    
    __table_args__ = (
        db.UniqueConstraint('store_id', 'sku', 
                          name='products_store_sku_unique'),
    )
```

### Mixins

#### **TenantMixin**
All tenant-scoped models inherit from `TenantMixin`:

```python
class TenantMixin:
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), 
                          nullable=False, index=True)
```

#### **StoreMixin**
All store-scoped models inherit from `StoreMixin`:

```python
class StoreMixin:
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), 
                         nullable=False, index=True)
    store = db.relationship('Store')
```

### Relationships

- **Tenant** ↔ **User**: One-to-Many
- **Tenant** ↔ **Role**: One-to-Many
- **Tenant** ↔ **Store**: One-to-Many
- **Tenant** ↔ **Subscription**: One-to-One
- **Tenant** ↔ **PaymentTransaction**: One-to-Many
- **Store** ↔ **Product**: One-to-Many (Example)
- **Subscription** ↔ **Plan**: Many-to-One
- **Plan** ↔ **PlanFeature**: One-to-Many
- **Feature** ↔ **PlanFeature**: One-to-Many
- **User** ↔ **UserRole**: One-to-Many
- **Role** ↔ **UserRole**: One-to-Many
- **Role** ↔ **RolePermission**: One-to-Many
- **Permission** ↔ **RolePermission**: One-to-Many
```

---

## 🚀 SaaS Onboarding Flow

The following flow outlines how a new customer can sign up, create a tenant, and subscribe to a plan.

1.  **Select a Plan**: The user chooses a subscription plan (e.g., Free, Pro, Enterprise) from a pricing page.
2.  **Create Account**: The user provides their email and password, along with a name for their new organization (which becomes the `Tenant`).
3.  **Tenant and User Creation**:
    *   A new `Tenant` is created.
    *   A new `User` is created and linked to the tenant. This user is typically assigned a `Tenant Admin` role by default.
4.  **Subscription Creation**:
    *   A `Subscription` record is created for the tenant, linked to the chosen `Plan`.
    *   If the plan has a trial, the status is set to `trialing`, and `trial_ends_at` is populated.
    *   If the plan requires immediate payment, the user is redirected to the payment gateway (M-Pesa).
5.  **Payment Handling (for paid plans)**:
    *   The user completes the payment process.
    *   A webhook notification is received from the payment provider.
    *   The `Subscription` status is updated to `active`.
6.  **Login and Access**: The user is automatically logged in and can start using the application within their new tenant context.

---

## 💰 Subscription & Billing Management

This section details how to manage plans, subscriptions, and feature access.

### Feature Gating

Feature gating restricts access to functionality based on the tenant's subscription plan.

#### 1. **Permission-Based Gating**
The most robust method is to link features to `Permissions`.

-   Create a `Permission` for each premium feature (e.g., `feature:advanced-reporting`).
-   When creating a `Plan`, associate it with the features it should have access to.
-   Create a `Role` (e.g., `pro-plan-features`) that has these permissions.
-   When a tenant subscribes to a plan, all users with a specific role (e.g., `user`) within that tenant could dynamically inherit the permissions of the `pro-plan-features` role.

A simpler approach is to have a decorator check the tenant's subscription status.

#### 2. **Decorator-Based Gating**

A custom decorator can check if the current tenant's plan includes a specific feature.

```python
from functools import wraps
from flask import g
from .exceptions import ForbiddenError

def require_feature(feature_slug):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            tenant = g.current_tenant
            if not tenant.subscription or tenant.subscription.status != 'active':
                raise ForbiddenError("No active subscription found.")

            # Check if the feature is in the tenant's plan
            has_feature = any(
                feature.slug == feature_slug 
                for feature in tenant.subscription.plan.features
            )
            
            if not has_feature:
                raise ForbiddenError(f"Your plan does not include the '{feature_slug}' feature.")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage in a route
@bp.route('/advanced-reports')
@jwt_required
@require_feature('advanced-reporting')
def generate_advanced_report():
    # Only tenants with 'advanced-reporting' feature can access this
    ...
```

### Subscription Lifecycle

-   **Trialing**: A new subscription on a plan with a trial period. Access is granted, but the subscription will be `canceled` or `past_due` if not converted to `active`.
-   **Active**: A healthy, paid subscription.
-   **Past Due**: Payment failed. Access might be restricted. The system should retry payment.
-   **Canceled**: The subscription has been terminated by the user or due to non-payment. Access to premium features is revoked.

### Payment Integration: Safaricom M-Pesa

Integrating with M-Pesa typically involves the Daraja API.

#### 1. **Configuration**
Add M-Pesa credentials to your `.env` file.
```ini
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_SHORTCODE=...
MPESA_PASSKEY=...
MPESA_CALLBACK_URL=https://yourapi.com/api/v1/payments/mpesa-callback
```

#### 2. **STK Push (Payment Initiation)**
When a user needs to pay, initiate an STK Push.

```python
# In your payments service
def initiate_mpesa_payment(phone_number, amount, transaction_desc):
    # Logic to get an access token from Daraja
    access_token = get_daraja_token()
    
    # Construct STK Push payload
    payload = {
        "BusinessShortCode": Config.MPESA_SHORTCODE,
        "Password": generate_mpesa_password(), # Base64(shortcode + passkey + timestamp)
        "Timestamp": get_timestamp(),
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": Config.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": Config.MPESA_CALLBACK_URL,
        "AccountReference": "YOUR_APP_NAME",
        "TransactionDesc": transaction_desc
    }
    
    # Make POST request to Daraja API
    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    return response.json()
```

#### 3. **Handling the Callback**
Create a webhook endpoint to receive notifications from M-Pesa.

-   **Security**: Verify that the request is genuinely from Safaricom.
-   **Data Processing**: The callback contains the result of the transaction.
    -   If successful, find the corresponding `PaymentTransaction` in your database, update its status to `completed`, and set the `Subscription` status to `active`.
    -   If failed, update the transaction status to `failed` and notify the user.

```python
# /api/v1/payments/mpesa-callback
@bp.route('/mpesa-callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    
    # Extract relevant data from the callback
    result_code = data['Body']['stkCallback']['ResultCode']
    
    if result_code == 0:
        # Success
        amount = data['Body']['stkCallback']['CallbackMetadata']['Item'][0]['Value']
        receipt_number = data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']
        
        # Find the pending transaction and update it
        # Activate the tenant's subscription
        subscription_service.activate_subscription_for_tenant(...)
        
    else:
        # Failure
        # Log the error and notify the user
        ...
        
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

```

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:5000/api/v1
```

### SaaS Onboarding & Registration

#### Register New Tenant and User
This endpoint is for new customers creating an account and a tenant simultaneously.

```http
POST /api/v1/onboarding/register
Content-Type: application/json

{
  "tenant_name": "New Corp",
  "plan_slug": "pro",
  "user": {
    "email": "admin@newcorp.com",
    "password": "StrongPassword123!",
    "first_name": "Admin",
    "last_name": "User"
  }
}

Response: 201 Created
{
  "message": "Tenant and user created successfully.",
  "access_token": "...",
  "refresh_token": "...",
  "user": { ... },
  "tenant": { ... },
  "subscription": { ... }
}
```

### Authentication Endpoints

#### Register User
This endpoint is for adding a user to an *existing* tenant.
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "tenant_slug": "acme-corp",
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}

Response: 201 Created
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "tenant_id": 1,
    "email": "user@example.com",
    "username": "johndoe"
  }
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "tenant_slug": "acme-corp",
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response: 200 OK
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "tenant_id": 1,
    "email": "user@example.com",
    "username": "johndoe"
  }
}

# JWT Payload includes:
{
  "user_id": 1,
  "tenant_id": 1,
  "roles": ["user"],
  "exp": 1234567890
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>

Response: 200 OK
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Forgot Password
```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "tenant_slug": "acme-corp",
  "email": "user@example.com"
}

Response: 200 OK
{
  "message": "Password reset email sent"
}
```

#### Reset Password
```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123!"
}

Response: 200 OK
{
  "message": "Password reset successful"
}
```

### User Endpoints

#### Get Current User
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": 1,
  "tenant_id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "roles": ["user"]
}
```

#### Update Profile
```http
PUT /api/v1/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith"
}

Response: 200 OK
{
  "message": "Profile updated successfully"
}
```

#### List Users (Admin Only, Tenant-Scoped)
```http
GET /api/v1/users
Authorization: Bearer <access_token>

Response: 200 OK
{
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "username": "johndoe",
      "roles": ["user"]
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
# Note: Only returns users within the same tenant_id
```

### Store Endpoints

#### Store Management Endpoints

```http
# Create Store (Tenant Admin only)
POST /api/v1/stores
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Downtown Store",
  "slug": "downtown-store",
  "domain": "downtown.mystore.com"
}

Response: 201 Created
{
  "id": 1,
  "name": "Downtown Store",
  "slug": "downtown-store",
  "tenant_id": 1
}

# List Accessible Stores (returns only stores user can access)
GET /api/v1/stores
Authorization: Bearer <token>

Response: 200 OK
{
  "stores": [
    {
      "id": 1,
      "name": "Downtown Store",
      "slug": "downtown-store",
      "is_default": true
    },
    {
      "id": 2,
      "name": "Uptown Store",
      "slug": "uptown-store",
      "is_default": false
    }
  ]
}

# Get Store Details
GET /api/v1/stores/:id
Authorization: Bearer <token>

Response: 200 OK
{
  "id": 1,
  "name": "Downtown Store",
  "slug": "downtown-store",
  "settings": {...}
}

# Update Store
PUT /api/v1/stores/:id
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Downtown Flagship Store"
}

# Assign User to Store
POST /api/v1/stores/:id/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 5,
  "role_id": 3,  # Optional: store-specific role
  "is_default": false
}

# Remove User from Store
DELETE /api/v1/stores/:id/users/:user_id
Authorization: Bearer <token>
```

### Store-Scoped Resource Endpoints (Example: Products)

```http
# List Products (requires X-Store-ID)
GET /api/v1/products
Authorization: Bearer <token>
X-Store-ID: 1

Response: 200 OK
{
  "products": [
    {
      "id": 1,
      "name": "Product A",
      "store_id": 1,
      "sku": "PROD-001"
    }
  ]
}

# Create Product (requires X-Store-ID)
POST /api/v1/products
Authorization: Bearer <token>
X-Store-ID: 1
Content-Type: application/json

{
  "name": "New Product",
  "sku": "PROD-002",
  "price": 29.99
}

# If X-Store-ID is missing:
Response: 400 Bad Request
{
  "error": "Store context required. Please provide X-Store-ID header."
}
```

### Tenant Endpoints

#### Create Tenant (System Admin Only)
```http
POST /api/v1/tenants
Authorization: Bearer <system_admin_token>
Content-Type: application/json

{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "domain": "acme.example.com"
}

Response: 201 Created
{
  "id": 1,
  "name": "Acme Corporation",
  "slug": "acme-corp"
}
```

#### Get Current Tenant Info
```http
GET /api/v1/tenants/current
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": 1,
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "is_active": true
}
```

### Subscription & Billing Endpoints

#### List Public Plans
```http
GET /api/v1/plans
Response: 200 OK
{
  "plans": [
    {
      "name": "Free",
      "slug": "free",
      "price": 0,
      "billing_cycle": "monthly"
    },
    {
      "name": "Pro",
      "slug": "pro",
      "price": 5000,
      "currency": "KES",
      "billing_cycle": "monthly"
    }
  ]
}
```

#### Get Tenant Subscription
```http
GET /api/v1/subscriptions/current
Authorization: Bearer <access_token>
Response: 200 OK
{
  "id": 1,
  "plan": { "name": "Pro", "slug": "pro" },
  "status": "active",
  "starts_at": "...",
  "ends_at": "..."
}
```

#### Change Subscription Plan
```http
PUT /api/v1/subscriptions/current
Authorization: Bearer <access_token>
Content-Type: application/json
{
  "new_plan_slug": "enterprise"
}
Response: 200 OK
{
  "message": "Subscription update initiated. Please complete payment if required."
}
```

#### Get Billing History
```http
GET /api/v1/billing/history
Authorization: Bearer <access_token>
Response: 200 OK
{
  "transactions": [
    {
      "id": 1,
      "amount": 5000,
      "currency": "KES",
      "status": "completed",
      "provider": "mpesa",
      "created_at": "..."
    }
  ]
}
```

### Payment Endpoints

#### Initiate M-Pesa Payment
```http
POST /api/v1/payments/mpesa/initiate
Authorization: Bearer <access_token>
Content-Type: application/json
{
  "phone_number": "254712345678",
  "amount": 5000,
  "description": "Subscription for Pro Plan"
}
Response: 200 OK
{
  "message": "STK push sent to your phone."
}
```

#### M-Pesa Callback/Webhook
This endpoint is for receiving server-to-server notifications from Safaricom.
```http
POST /api/v1/payments/mpesa-callback
Content-Type: application/json

{ ... M-Pesa callback payload ... }

Response: 200 OK
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

### RBAC Endpoints

#### Assign Role to User
```http
POST /api/v1/users/{user_id}/roles
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "role_id": 2,
  "expires_at": "2025-12-31T23:59:59Z"
}

Response: 201 Created
{
  "message": "Role assigned successfully"
}
```

#### List Roles (Tenant-Scoped)
```http
GET /api/v1/roles
Authorization: Bearer <access_token>

Response: 200 OK
{
  "roles": [
    {
      "id": 1,
      "name": "admin",
      "description": "Administrator role"
    },
    {
      "id": 2,
      "name": "user",
      "description": "Standard user role"
    }
  ]
}
```

### Health Check
```http
GET /api/v1/health

Response: 200 OK
{
  "status": "healthy",
  "timestamp": "2025-11-26T10:30:00Z",
  "database": "connected",
  "version": "1.0.0"
}
```

---

## 🔐 Authentication Flow


### JWT Token Generation (using PyJWT)

```python
import jwt
from datetime import datetime, timedelta
from app.config import Config

def generate_access_token(user):
    """Generate JWT access token without store_id"""
    payload = {
        'user_id': user.id,
        'tenant_id': user.tenant_id,
        'roles': [role.name for role in user.roles],
        'exp': datetime.utcnow() + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
```

### Password Hashing (using Werkzeug)

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Hash password
hashed = generate_password_hash(password, method='pbkdf2:sha256')

# Verify password
is_valid = check_password_hash(user.password_hash, password)
```

### Registration Flow
1. User submits registration data with tenant_slug
2. Validate tenant exists and is active
3. Validation (email format, password strength)
4. Password hashing (werkzeug.security)
5. User creation in database with tenant_id
6. Assign default "user" role
7. Email verification sent (optional)
8. Return success message

### Login Flow
1. User submits credentials with tenant_slug
2. Validate tenant exists and is active
3. User lookup by tenant_id + email
4. Password verification (werkzeug.security)
5. JWT token generation with tenant_id (PyJWT)
6. Update last_login timestamp
7. Return tokens + user data

### Token Refresh Flow
1. Client sends refresh token
2. Token validation & decoding (PyJWT)
3. Verify tenant_id is still valid
4. Generate new access token
5. Return new access token

### Password Reset Flow
1. User requests password reset with tenant_slug + email
2. Lookup user by tenant_id + email
3. Generate secure reset token (JWT with short expiry)
4. Send email with reset link
5. User clicks link, submits new password
6. Validate token, update password (werkzeug hash)
7. Invalidate reset token

---

## 🛡️ RBAC System

### Permission Naming Convention
```
<resource>:<action>
```

Examples:
- `users:create`
- `users:read`
- `users:update`
- `users:delete`
- `roles:assign`
- `tenants:manage`
- `stores:manage`
- `products:create`

### Tenant-Scoped Permissions

All RBAC operations are automatically scoped to the current tenant:

```python
# User in Tenant A can only:
- Assign roles that exist in Tenant A
- View users in Tenant A
- Manage permissions for roles in Tenant A
```

### Store-Scoped Permissions
Permissions can be further scoped to a specific store. A user might be an admin for one store but only a viewer for another store within the same tenant.

### Permission Checking with Store Scope

```python
# app/blueprints/rbac/services.py

class RBACService:
    def has_permission(self, user_id, permission_name, store_id=None):
        """
        Check if user has permission, optionally scoped to a store
        
        Args:
            user_id: User ID
            permission_name: Permission to check (e.g., 'products:create')
            store_id: Optional store ID for store-scoped permission check
        
        Returns:
            bool: True if user has permission
        """
        # Get user's roles
        query = UserRole.query.filter_by(
            user_id=user_id,
            is_active=True
        )
        
        if store_id:
            # Check both tenant-wide roles (store_id=NULL) and store-specific roles
            query = query.filter(
                (UserRole.store_id == store_id) | 
                (UserRole.store_id == None)
            )
        else:
            # Only check tenant-wide roles
            query = query.filter(UserRole.store_id == None)
        
        user_roles = query.all()
        
        # Get permissions for these roles
        for user_role in user_roles:
            role_permissions = RolePermission.query.filter_by(
                role_id=user_role.role_id
            ).all()
            
            for rp in role_permissions:
                if rp.permission.name == permission_name:
                    return True
        
        return False
```

### Updated Permission Decorator

```python
# app/core/decorators.py

def require_permission(permission_name, store_scoped=False):
    """
    Decorator to check if user has required permission
    
    Args:
        permission_name: Permission to check (e.g., 'products:create')
        store_scoped: If True, check store-specific permissions
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user_id'):
                raise UnauthorizedError("Authentication required")
            
            store_id = g.current_store_id if store_scoped else None
            
            if not rbac_service.has_permission(
                g.current_user_id, 
                permission_name,
                store_id=store_id
            ):
                raise ForbiddenError(
                    f"Permission denied: {permission_name}" +
                    (f" for store {store_id}" if store_id else "")
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage examples:
@bp.route('/users')
@jwt_required
@require_permission('users:read', store_scoped=False)  # Tenant-wide
def list_users():
    pass

@bp.route('/products')
@jwt_required
@require_permission('products:read', store_scoped=True)  # Store-specific
def list_products():
    pass
```

### Default Roles (per Tenant)

#### Admin (Tenant Admin)
- Full access within tenant
- User management
- Role assignment
- Store creation
- Cannot access other tenants' data

#### Store Manager
- Full access within a specific store
- Product management
- Order management
- Cannot manage other stores

#### User
- Basic authenticated access
- Own profile management
- View tenant/store information

### Checking Permissions

#### In Routes (with Decorators)
```python
from app.core.decorators import require_permission, jwt_required

@bp.route('/admin/users')
@jwt_required
@require_permission('users:read')
def list_users():
    # Automatically filtered by g.current_tenant_id
    users = user_service.get_all_users()
    return jsonify(users)
```

#### In Services
```python
def can_user_perform_action(user_id, permission_name, store_id=None):
    # Checks if user has permission through any active role
    # within their tenant, potentially scoped to a store.
    return rbac_service.has_permission(user_id, permission_name, store_id=store_id)
```

### RBAC Models Relationships

```
User ←→ UserRole ←→ Role ←→ RolePermission ←→ Permission
```

### Assigning Roles

```python
# Via CLI
flask user assign-role --user-id 1 --role-id 2 --store-id 5 # Optional store scope

# Via API (admin only)
POST /api/v1/users/1/roles
Authorization: Bearer <admin_token>
{
  "role_id": 2,
  "store_id": 5, # Optional: Assign role for a specific store
  "expires_at": "2025-12-31T23:59:59Z"
}
```

---

## 🔄 Store Selection Flow

### Client-Side Implementation

```javascript
// 1. Login and get accessible stores
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password, tenant_slug })
});

const { access_token, stores } = await loginResponse.json();

// 2. User selects a store from UI dropdown
const selectedStoreId = stores[0].id;  // Or user choice

// 3. Make store-scoped requests with X-Store-ID header
const productsResponse = await fetch('/api/v1/products', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'X-Store-ID': selectedStoreId.toString()
  }
});

// 4. To switch stores, just change the header (no re-auth needed)
const newStoreId = stores[1].id;
const ordersResponse = await fetch('/api/v1/orders', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'X-Store-ID': newStoreId.toString()
  }
});
```

### Updated Login Response

```python
# app/blueprints/auth/services.py

def login(tenant_slug, email, password):
    # ... existing login logic ...
    
    # Get user's accessible stores
    user_stores = UserStore.query.filter_by(
        user_id=user.id
    ).join(Store).filter(
        Store.is_active == True,
        Store.deleted_at == None
    ).all()
    
    stores = [{
        'id': us.store_id,
        'name': us.store.name,
        'slug': us.store.slug,
        'is_default': us.is_default
    } for us in user_stores]
    
    return {
        'access_token': generate_access_token(user),
        'refresh_token': generate_refresh_token(user),
        'user': user_schema.dump(user),
        'stores': stores  # Include accessible stores
    }
```

---

## 🏪 Store Context Requirements

### When Store Context is Required

**REQUIRED (X-Store-ID header mandatory):**
- Product management
- Order processing
- Inventory operations
- Store-specific analytics
- Customer management (if store-scoped)
- Any resource with `store_id` column

**OPTIONAL (tenant-wide operations):**
- User management
- Role management
- Tenant settings
- Subscription management
- Billing history
- Listing accessible stores

**NOT ALLOWED (system-wide operations):**
- Authentication endpoints
- Health checks
- Public endpoints (pricing plans)

### Handling Missing Store Context

```python
# In routes that require store context
@bp.route('/products')
@jwt_required
@require_permission('products:read', store_scoped=True)
def list_products():
    if not g.current_store_id:
        return jsonify({
            "error": "Store context required",
            "message": "Please provide X-Store-ID header"
        }), 400
    
    products = product_service.get_all()
    return jsonify(products), 200
```

---

## 🏢 Tenant Management

### Tenant Isolation Strategy

#### 1. **Middleware-Based Tenant Detection**
```python
# Extract tenant_id from JWT token
g.current_tenant_id = decoded_token['tenant_id']
g.current_user_id = decoded_token['user_id']
```

#### 2. **Repository-Level Filtering**
```python
class BaseRepository:
    def get_all(self):
        # Automatically filter by tenant_id
        query = self.model.query.filter_by(
            tenant_id=g.current_tenant_id,
            deleted_at=None
        )
        return query.all()
```

#### 3. **Database Constraints**
```sql
-- Composite unique constraints
ALTER TABLE users ADD CONSTRAINT users_tenant_email_unique 
  UNIQUE (tenant_id, email);

-- Foreign key constraints
ALTER TABLE users ADD CONSTRAINT users_tenant_fk 
  FOREIGN KEY (tenant_id) REFERENCES tenants(id);
```

### Creating a New Tenant

```bash
# Via CLI
flask tenant create --name "Acme Corp" --slug "acme-corp"

# Creates:
# 1. Tenant record
# 2. Default roles (admin, user)
# 3. Default permissions
```

### Tenant-Specific Settings

```python
# Stored in tenants.settings (JSON column)
{
  "max_users": 100,
  "features": ["api_access", "advanced_reporting"],
  "branding": {
    "primary_color": "#007bff",
    "logo_url": "https://..."
  }
}
```

## 📝 Usage Examples

### Creating a Store-Scoped Resource (Product)

1. **Define Model with TenantMixin and StoreMixin**
```python
# app/blueprints/products/models.py
from app.core.models import BaseModel, TenantMixin, StoreMixin
from app.extensions import db

class Product(BaseModel, TenantMixin, StoreMixin):
    __tablename__ = 'products'
    
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Composite unique constraint for SKU within a store
    __table_args__ = (
        db.UniqueConstraint('store_id', 'sku', name='products_store_sku_unique'),
    )
```

2. **Create Repository with Tenant and Store Filtering**
```python
# app/blueprints/products/repositories.py
from flask import g
from app.blueprints.products.models import Product
from app.extensions import db

class ProductRepository:
    def get_all(self):
        # Automatically filter by tenant and store
        return Product.query.filter_by(
            tenant_id=g.current_tenant_id,
            store_id=g.current_store_id, # Assumes store_id is in g
            deleted_at=None
        ).all()
    
    def create(self, data):
        # Automatically inject tenant_id and store_id
        data['tenant_id'] = g.current_tenant_id
        data['store_id'] = g.current_store_id
        product = Product(**data)
        db.session.add(product)
        db.session.commit()
        return product
```

3. **Create Service**
```python
# app/blueprints/products/services.py
class ProductService:
    def __init__(self, repository):
        self.repository = repository
    
    def create_product(self, data):
        # Business logic for creating a product
        return self.repository.create(data)
```

4. **Define Schema**
```python
# app/blueprints/products/schemas.py
from marshmallow import Schema, fields

class ProductSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    sku = fields.Str(required=True)
    price = fields.Decimal(as_string=True, required=True)
    tenant_id = fields.Int(dump_only=True)
    store_id = fields.Int(dump_only=True)
```

5. **Create Route**
```python
# app/blueprints/products/routes.py
from app.core.decorators import jwt_required, require_permission

@bp.route('/products', methods=['POST'])
@jwt_required
@require_permission('products:create')
def create_product():
    # Assumes store context is set by middleware
    data = request.get_json()
    product = product_service.create_product(data)
    return jsonify(product), 201
```

---

## 🛠️ CLI Commands

### Database Commands
```bash
# Initialize database
flask db-init

# Seed initial data
flask seed-db

# Reset database (caution!)
flask db-reset
```

### Tenant Commands
```bash
# Create new tenant
flask tenant create --name "Acme Corp" --slug "acme-corp"

# List all tenants
flask tenant list

# Deactivate tenant
flask tenant deactivate --slug "acme-corp"

# Seed default roles for tenant
flask tenant seed-roles --tenant-id 1
```

### User Commands
```bash
# Create user within tenant
flask user create --tenant-slug "acme-corp" \
  --email admin@acme.com --username admin

# Assign role to user
flask user assign-role --user-id 1 --role-id 2

# List users in tenant
flask user list --tenant-slug "acme-corp"
```

---

## 🧪 Development Guide

### Adding a New Store-Scoped Feature

1. Create model inheriting from `BaseModel`, `TenantMixin`, and `StoreMixin`.
2. Add composite unique constraints with `tenant_id` and/or `store_id`.
3. Create repository with automatic tenant and store filtering.
4. Implement service layer with business logic.
5. Define Marshmallow schemas (exclude `tenant_id` and `store_id` from input).
6. Create route handlers with `@jwt_required` and permission decorators.
7. Register blueprint in the application factory.
8. Add migrations for new models.
9. Write tests with tenant and store fixtures to ensure isolation.

### Security Best Practices

1. **Never trust client-provided tenant_id or store_id** - Always use context from JWT or middleware.
2. **Validate cross-tenant/store references** - Ensure FK relationships stay within the correct scope.
3. **Use composite unique constraints** - `(tenant_id, unique_field)` or `(store_id, unique_field)`.
4. **Test tenant and store isolation** - Verify queries don't leak data between tenants or stores.
5. **Audit cross-scope access attempts** - Log suspicious activities.

### Testing Multi-Tenancy

```python
# tests/conftest.py
@pytest.fixture
def tenant_a():
    tenant = Tenant(name="Tenant A", slug="tenant-a")
    db.session.add(tenant)
    db.session.commit()
    return tenant

@pytest.fixture
def tenant_b():
    tenant = Tenant(name="Tenant B", slug="tenant-b")
    db.session.add(tenant)
    db.session.commit()
    return tenant

def test_tenant_isolation(tenant_a, tenant_b):
    # Create user in tenant A
    user_a = create_user(tenant_id=tenant_a.id)
    
    # Create user in tenant B
    user_b = create_user(tenant_id=tenant_b.id)
    
    # Login as user A
    token_a = login(user_a)
    
    # Attempt to access user B's data
    response = client.get('/api/v1/users', headers={'Authorization': f'Bearer {token_a}'})
    
    # Should not see user B in results
    assert user_b.id not in [u['id'] for u in response.json['users']]
```

---

## ✅ Implementation Checklist

### Database Models
- [ ] Create Store model with TenantMixin
- [ ] Create UserStore model for access control
- [ ] Update UserRole model with nullable store_id
- [ ] Create store-scoped resource models (e.g., Product)
- [ ] Add composite unique constraints

### Middleware & Context
- [ ] Implement store context extraction middleware
- [ ] Add store access validation
- [ ] Handle missing store context gracefully
- [ ] Set g.current_store_id and g.current_store

### Repositories
- [ ] Update BaseRepository with store filtering
- [ ] Add store_scoped parameter to methods
- [ ] Implement automatic store_id injection
- [ ] Add store validation in update/delete

### Services
- [ ] Create StoreService
- [ ] Implement store access control methods
- [ ] Add default store selection logic
- [ ] Update RBAC service for store-scoped permissions

### Routes & API
- [ ] Create store management endpoints
- [ ] Update authentication to return accessible stores
- [ ] Add X-Store-ID header to store-scoped endpoints
- [ ] Implement proper error responses

### RBAC
- [ ] Update permission checking for store context
- [ ] Modify decorators to support store_scoped parameter
- [ ] Test tenant-wide vs store-specific roles
- [ ] Add store-specific role assignment

### Onboarding
- [ ] Create default store during tenant creation
- [ ] Assign admin user to default store
- [ ] Return store list in login response

### Testing
- [ ] Test store isolation within same tenant
- [ ] Test cross-store access prevention
- [ ] Test user-store access control
- [ ] Test store context requirement enforcement
- [ ] Test default store selection

---

## 🎯 Summary of Key Changes

1. **JWT Token:** Does NOT contain `store_id` - allows store switching without re-auth
2. **Store Context:** Provided via `X-Store-ID` header, validated by middleware
3. **Access Control:** Users explicitly assigned to stores via `UserStore` table
4. **RBAC:** Roles can be tenant-wide OR store-specific via nullable `store_id` in UserRole
5. **Repositories:** Automatic filtering by both `tenant_id` and `store_id` where applicable
6. **API Design:** Store-scoped endpoints require `X-Store-ID` header, return 400 if missing
7. **Flexibility:** Clients can switch stores by changing header value

This architecture provides secure, flexible multi-store support while maintaining strong tenant isolation and allowing users to seamlessly work across multiple stores.

---

## 🧪 Testing Multi-Store Isolation

### Test Store Data Isolation

```python
# tests/test_stores.py

def test_store_isolation(tenant_a, store_1, store_2, user_a):
    """Test that products from store_1 are not visible in store_2"""
    
    # Create product in store_1
    product_1 = Product(
        tenant_id=tenant_a.id,
        store_id=store_1.id,
        name="Store 1 Product",
        sku="S1-001",
        price=10.00
    )
    db.session.add(product_1)
    db.session.commit()
    
    # Login as user with access to both stores
    token = login_user(user_a)
    
    # Request products for store_1
    response = client.get('/api/v1/products',
        headers={
            'Authorization': f'Bearer {token}',
            'X-Store-ID': str(store_1.id)
        })
    
    assert response.status_code == 200
    assert product_1.id in [p['id'] for p in response.json['products']]
    
    # Request products for store_2
    response = client.get('/api/v1/products',
        headers={
            'Authorization': f'Bearer {token}',
            'X-Store-ID': str(store_2.id)
        })
    
    assert response.status_code == 200
    assert product_1.id not in [p['id'] for p in response.json['products']]

def test_store_access_control(tenant_a, store_1, store_2, user_a, user_b):
    """Test that users can only access stores they're assigned to"""
    
    # Assign user_a to store_1 only
    UserStore(user_id=user_a.id, store_id=store_1.id).save()
    
    token = login_user(user_a)
    
    # Try to access store_2 (should fail)
    response = client.get('/api/v1/products',
        headers={
            'Authorization': f'Bearer {token}',
            'X-Store-ID': str(store_2.id)
        })
    
    assert response.status_code == 403
    assert 'Access denied' in response.json['error']
```

### Code Style

- **PEP 8** compliance
- **Type hints** for function signatures
- **Docstrings** for classes and functions
- **Constants** in `UPPER_CASE`
- **Private methods** prefixed with `_`
- **Tenant-scoped models** must inherit `TenantMixin`

---

## 💡 Other SaaS Considerations

To build a truly comprehensive SaaS application, consider these additional areas:

-   **User Invitations**: Create a flow for users to invite team members into their tenant. This typically involves generating a unique invitation token, sending an email, and providing an endpoint for the new user to accept the invitation and create their account.

-   **Custom Domains**: Allow tenants to use their own domain name (e.g., `app.customer.com`) to access the service. This involves CNAME record handling on the DNS side and programmatic SSL certificate provisioning (e.g., using Let's Encrypt) on the server side. The `domain` field in the `Tenant` model is the first step for this.

-   **Audit Trails**: Keep a log of important actions performed by users within a tenant (e.g., `user X updated project Y`). This is crucial for security, compliance, and debugging. Create an `AuditLog` model that records the user, action, target resource, and timestamp.

-   **Admin Dashboard**: Build a separate interface (or a protected area in your main app) for system administrators to manage tenants, view aggregated analytics, handle support requests, and manage subscription plans.

-   **Background Jobs & Scalability**: For tasks like sending emails, processing data, or generating reports, use a background worker system like Celery with a message broker like Redis or RabbitMQ. This ensures your API remains fast and responsive.

-   **Analytics**: Provide tenant-level analytics to show customers how they are using the application. Additionally, implement platform-level analytics for your own team to monitor application health and user engagement.

---

## 📚 Technology Stack Summary

| Component | Technology |
|-----------|-----------|
| Framework | Flask 2.3+ |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | PyJWT |
| Password Hashing | Werkzeug.security |
| Validation | Marshmallow |
| Email | Flask-Mail |
| Database | PostgreSQL |

---

## 📄 License

This template is open-source and available for reuse in your projects.

---

**Happy Coding! 🚀**