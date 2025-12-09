# 2. Sequence of Events: Project Development Timeline

This document outlines the major development steps that have been completed to bring the project to its current state.

## Phase 1: Core Foundation

### Step 1: Project Scaffolding & Initial Setup
- **Action:** Established the initial repository and directory structure.
- **Details:** A standard Flask application structure was created using the "application factory" pattern (`create_app`). Blueprints were introduced as the primary method for organizing features.
- **Outcome:** A runnable, albeit empty, Flask application.

### Step 2: Data Modeling
- **Action:** Defined the core database schema using SQLAlchemy.
- **Details:** All primary models were created: `User`, `Tenant`, `Store`, `Role`, and `Permission`. Abstract base models (`BaseModel`, `TenantScopedModel`) were implemented to enforce consistency and DRY principles.
- **Outcome:** A complete object-relational mapping of the application's data structure.

### Step 3: Database Initialization
- **Action:** Created and applied the initial database migrations.
- **Details:** Using `Flask-Migrate`, the SQLAlchemy models were translated into a database schema. A second migration was created to **seed** the database with 48 essential permissions (e.g., `products.create`, `users.invite`) and pre-defined default roles.
- **Outcome:** A live database with all necessary tables, relationships, and foundational RBAC data.

### Step 4: Core Logic & Utilities
- **Action:** Implemented critical, non-feature-specific helper modules.
- **Details:**
    - `app/core/utils.py`: Created JWT generation and decoding functions.
    - `app/core/exceptions.py`: Defined a full suite of custom, application-specific exceptions for predictable error handling (e.g., `TenantAccessDeniedError`, `InvalidTokenError`).
- **Outcome:** A robust toolkit of shared utilities for security and error handling.

### Step 5: Security Middleware & Decorators
- **Action:** Built the core security enforcement layers.
- **Details:**
    - **Middleware:** Implemented `TenantMiddleware` and `StoreMiddleware`. These intercept every authenticated request to load the correct `User`, `Tenant`, and `Store` objects into the application context (`g`). This is the foundation of our multi-tenancy.
    - **Decorators:** Created decorators like `@require_permission` to provide a simple and declarative way to protect API endpoints based on the current user's permissions.
- **Outcome:** A secure-by-default environment where authentication and authorization are handled automatically and explicitly.

### Step 6: Authentication System
- **Action:** Implemented the complete user authentication and registration flow.
- **Details:** The `AuthService` was built to handle business logic for `register`, `login`, and `refresh_token`. Corresponding API endpoints (`/api/v1/auth/...`) were created and linked to the service.
- **Outcome:** The application now has a fully functional authentication system, marking the completion of the most critical foundational work.
