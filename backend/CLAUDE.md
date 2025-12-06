# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based multi-tenant SaaS backend application with Role-Based Access Control (RBAC). The core system implements tenant and store-level data isolation through a comprehensive security middleware architecture.

## Development Setup

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and secret keys
```

### Running the Application
```bash
# Development server
flask run

# Production server (using wsgi.py)
python wsgi.py
```

### Database Commands
```bash
# Database migrations (using Flask-Migrate/Alembic)
flask db init        # Initialize migrations (first time only)
flask db migrate -m "description"  # Generate migration
flask db upgrade     # Apply migrations
flask db downgrade   # Rollback migration

# Custom CLI commands
flask db-commands create   # Create database tables
flask db-commands drop     # Drop database tables
flask db-commands reset    # Reset database (drop + create)
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app
```

## Core Architecture

### Multi-Tenant Data Model

The system follows a hierarchical multi-tenant architecture:

**User → Tenant → Store**

- **User**: Global entity representing a person who can log in
- **Tenant**: Top-level organization/company (primary data isolation boundary)
- **Store**: Specific location/branch within a tenant

#### Core Models (in `core_models.py`)

**Primary Entities:**
- `User`: Global user with email/password authentication
- `Tenant`: Company/organization with status (trial/active/suspended/canceled)
- `Store`: Location/branch belonging to a tenant
- `Role`: Named permission set within a tenant
- `Permission`: Global, code-defined granular actions (e.g., `products.create`)

**Junction Tables:**
- `TenantUser`: Links users to tenants
- `StoreUser`: Links users to specific stores they can access
- `UserRole`: Assigns roles to users (tenant-wide or store-specific)
- `RolePermission`: Links permissions to roles

#### Model Inheritance Hierarchy

```
BaseModel (abstract)
  ├── id, created_at, updated_at
  ├── TenantScopedModel (abstract)
  │     ├── tenant_id, created_by, updated_by, deleted_at
  │     └── StoreScopedModel (abstract)
  │           └── store_id
```

All tenant-scoped models inherit from `TenantScopedModel` and automatically include tenant_id.

### Security Middleware Architecture

The application uses a two-layer security middleware system that runs on every request:

1. **TenantMiddleware** (first checkpoint):
   - Extracts and validates JWT from Authorization header
   - Retrieves `user_id` and `tenant_id` from token
   - Validates user exists, is active, and is a member of the tenant
   - Sets `g.user` and `g.tenant` in Flask request context
   - Returns 401/403 if validation fails

2. **StoreMiddleware** (second checkpoint):
   - Checks for `X-Store-ID` header (optional)
   - Validates user has access to the requested store within the tenant
   - Sets `g.store` in Flask request context
   - Returns 403 if store validation fails

3. **SQLAlchemy Query Hook** (automatic tenant filtering):
   - Event listener on `Session.do_orm_execute`
   - Automatically injects `WHERE tenant_id = ...` clause on all tenant-scoped queries
   - Prevents data leaks even if developer forgets to filter by tenant
   - Only applies when `g.tenant` exists in request context

### Blueprint Organization

The application uses Flask blueprints organized by feature domain:

```
app/blueprints/
├── api/v1/          # API version wrapper
├── auth/            # Authentication (register, login, password reset)
├── users/           # User management
├── tenants/         # Tenant management
├── stores/          # Store management
├── rbac/            # Role and permission management
├── subscriptions/   # Subscription plans
├── billing/         # Invoicing and billing
├── payments/        # Payment processing (e.g., M-Pesa)
├── usage/           # Usage tracking and metering
├── notifications/   # Notification system
├── onboarding/      # SaaS onboarding flow
└── health/          # Health check endpoints
```

Each blueprint typically contains:
- `models.py`: Data models
- `routes.py`: API endpoints
- `services.py`: Business logic
- `repositories.py`: Data access layer
- `schemas.py`: Request/response validation (Marshmallow)

### Application Factory Pattern

The app uses the application factory pattern (`create_app()` in `app/__init__.py`):

```python
app = create_app("development")  # or "testing", "production"
```

Configuration classes are in `app/config.py` and controlled by environment variables.

## Key Implementation Notes

### Bootstrap Problem

The first user/tenant must be created outside the normal middleware flow since there's no tenant context yet. Solutions:
- Create a separate `bootstrap.py` script
- Create a special `/api/v1/auth/bootstrap` endpoint that bypasses tenant middleware
- Disable/remove after initial setup

### Permission Management

Permissions should be:
- Code-defined, not user-created
- Seeded via database migrations
- Use naming convention: `resource.action` (e.g., `products.create`, `stores.edit`, `invoices.view`)
- Stored globally in the `permissions` table

### JWT Token Structure

JWT tokens must contain at minimum:
- `user_id`: User UUID
- `tenant_id`: Tenant UUID
- Standard claims (iat, exp, etc.)

### Database Considerations

- Uses SQLAlchemy with Flask-Migrate (Alembic) for migrations
- PostgreSQL recommended for production (supports UUID type natively)
- SQLite supported for development (via `sqlite:///dev.db`)
- All primary keys use UUID (not auto-increment integers)
- Soft deletes implemented via `deleted_at` column on tenant-scoped models

### Testing Strategy

- Test files in `tests/` directory
- Use pytest with conftest.py for fixtures
- Key test areas:
  - Authentication and JWT generation
  - Tenant isolation (users cannot access other tenants' data)
  - Store-level access control
  - RBAC permission checking
  - Subscription and billing logic

## Common Development Workflows

### Adding a New Feature Module

1. Create new blueprint directory under `app/blueprints/`
2. Create models inheriting from `TenantScopedModel` or `StoreScopedModel`
3. Create migration: `flask db migrate -m "Add feature models"`
4. Implement services with business logic (services can trust `g.tenant` and `g.store`)
5. Create routes with proper permission decorators
6. Register blueprint in `app/__init__.py`
7. Add permissions to seed data

### Working with Migrations

```bash
# After modifying models
flask db migrate -m "Description of changes"

# Review the generated migration in migrations/versions/
# Edit if needed (e.g., data migrations, complex schema changes)

# Apply the migration
flask db upgrade

# If something goes wrong
flask db downgrade  # Go back one version
```

### Database Configuration

The application uses DATABASE_URL from environment variables:
- Development: `sqlite:///dev.db` (default)
- Production: PostgreSQL connection string (e.g., `postgresql://user:pass@host:port/dbname`)

## Important Files

- `core_models.py`: Complete model definitions (reference for full schema)
- `core_system_architecture.md`: Detailed architectural documentation
- `context_and_security_middleware.md`: Security middleware implementation guide
- `app/extensions.py`: Flask extension initialization (db, cors, migrate)
- `app/config.py`: Environment-based configuration
- `wsgi.py`: Production WSGI entry point
- `.env.example`: Environment variable template

## Technology Stack

- **Framework**: Flask 3.1.2
- **Database ORM**: SQLAlchemy 2.0.44 with Flask-SQLAlchemy 3.1.1
- **Migrations**: Alembic 1.17.1 via Flask-Migrate 4.1.0
- **Authentication**: PyJWT 2.10.1
- **Validation**: Marshmallow 4.0.1
- **Database**: PostgreSQL (production) / SQLite (development)
- **CORS**: Flask-CORS 6.0.1
- **Password Hashing**: Werkzeug (built-in)
