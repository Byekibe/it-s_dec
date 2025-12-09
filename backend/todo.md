# TODO List

## 🔥 Critical (Do First)

- [x] **Move core models**: Organized models into blueprint-specific files
  - ✓ app/core/models.py (BaseModel, TenantScopedModel, StoreScopedModel)
  - ✓ app/blueprints/users/models.py (User)
  - ✓ app/blueprints/tenants/models.py (Tenant, TenantUser)
  - ✓ app/blueprints/stores/models.py (Store, StoreUser)
  - ✓ app/blueprints/rbac/models.py (Role, Permission, UserRole, RolePermission)
- [x] **Create initial database migration**
  - ✓ Migration created and applied successfully
  - ✓ All tables created in database
- [x] **Implement JWT utilities** in `app/core/utils.py`
  - ✓ JWT token generation (access + refresh tokens)
  - ✓ JWT token validation with proper error handling
  - ✓ Token payload extraction (with and without expiry validation)
  - ✓ Token type verification
- [x] **Implement custom exceptions** in `app/core/exceptions.py`
  - ✓ APIError base class with to_dict() for JSON responses
  - ✓ Auth errors: UnauthorizedError, InvalidCredentialsError, TokenExpiredError, InvalidTokenError
  - ✓ Access errors: ForbiddenError, TenantAccessDeniedError, StoreAccessDeniedError, InsufficientPermissionsError
  - ✓ Not found errors: NotFoundError, UserNotFoundError, TenantNotFoundError, StoreNotFoundError, RoleNotFoundError
  - ✓ Validation errors: ValidationError, BadRequestError
  - ✓ Business logic errors: TenantSuspendedError, UserInactiveError
- [x] **Create TenantMiddleware** in `app/core/middleware.py`
  - ✓ JWT extraction from Authorization header
  - ✓ Token validation and user/tenant loading
  - ✓ Exempt paths for auth routes
  - ✓ Sets g.user, g.tenant, g.tenant_user
- [x] **Create StoreMiddleware** in `app/core/middleware.py`
  - ✓ X-Store-ID header handling
  - ✓ Store access validation
  - ✓ Sets g.store
- [x] **Register middleware** in `app/__init__.py`
  - ✓ Error handlers registered
  - ✓ TenantMiddleware and StoreMiddleware initialized

## 🎯 High Priority

### 🔧 Fix Application Bugs (from tests)
- [ ] Fix TenantStatus enum JSON serialization in `app/blueprints/tenants/schemas.py`
- [ ] Fix UpdateCurrentUserSchema.validate_new_password() signature in `app/blueprints/users/schemas.py`
- [ ] Fix user roles response structure in `app/blueprints/rbac/schemas.py`
- [ ] Fix tenant endpoint permissions for `/tenants/current` GET

### 🔐 Authentication System - Complete Implementation
**Implemented:**
- [x] login() - authenticate user against tenant
- [x] register() - create new user + tenant
- [x] refresh_token() - generate new tokens from refresh token
- [x] bootstrap() - create first user/tenant when system is empty

**Needs Implementation:**
- [ ] **Logout**
  - [ ] POST /api/v1/auth/logout - Invalidate current token
  - [ ] Token blacklist mechanism (Redis or DB table)
  - [ ] POST /api/v1/auth/logout-all - Invalidate all user sessions
- [ ] **Forgot Password Flow**
  - [ ] POST /api/v1/auth/forgot-password - Request password reset email
  - [ ] POST /api/v1/auth/reset-password - Reset password with token
  - [ ] Password reset token model/storage
  - [ ] Email service integration for sending reset links
- [ ] **Email Verification**
  - [ ] POST /api/v1/auth/verify-email - Verify email with token
  - [ ] POST /api/v1/auth/resend-verification - Resend verification email
  - [ ] Email verification token model/storage
  - [ ] Add `email_verified` field to User model
- [ ] **Session Management**
  - [ ] GET /api/v1/auth/sessions - List active sessions
  - [ ] DELETE /api/v1/auth/sessions/:id - Revoke specific session
  - [ ] Session tracking model (device, IP, last activity)

### 👥 User Management - Complete Implementation
**Implemented:**
- [x] CRUD operations (create, read, update, deactivate)
- [x] Current user profile (get/update)
- [x] List users with pagination/search

**Needs Implementation:**
- [ ] **User Invitation Flow**
  - [ ] POST /api/v1/users/invite - Send invitation email
  - [ ] POST /api/v1/auth/accept-invite - Accept invitation & set password
  - [ ] Invitation token model/storage
  - [ ] Invitation expiry handling
- [ ] **Profile Enhancements**
  - [ ] Avatar/profile picture upload
  - [ ] PUT /api/v1/users/me/avatar - Upload avatar
  - [ ] User preferences/settings

### 🏢 Tenant Management - Complete Implementation
**Implemented:**
- [x] Get current tenant
- [x] Update current tenant

**Needs Implementation:**
- [ ] **Tenant Settings**
  - [ ] GET /api/v1/tenants/current/settings - Get tenant settings
  - [ ] PUT /api/v1/tenants/current/settings - Update tenant settings
  - [ ] Tenant settings model (timezone, currency, locale, etc.)
- [ ] **Multi-Tenant User Support**
  - [ ] GET /api/v1/users/me/tenants - List user's tenants
  - [ ] POST /api/v1/auth/switch-tenant - Switch active tenant context
- [ ] **Tenant Branding** (optional)
  - [ ] Logo upload
  - [ ] Custom colors/theme

### 🏪 Store Management - Complete Implementation
**Implemented:**
- [x] CRUD operations
- [x] User assignment to stores

**Needs Implementation:**
- [ ] **Store Settings**
  - [ ] GET /api/v1/stores/:id/settings - Get store settings
  - [ ] PUT /api/v1/stores/:id/settings - Update store settings
  - [ ] Store settings model (operating hours, contact info, etc.)
- [ ] **Store Hours/Schedule**
  - [ ] Store operating hours model
  - [ ] Holiday/closure management

---

## ✅ Previously Completed (Basic Implementation)

### Authentication System (Basic)
- [x] Implement AuthService in `app/blueprints/auth/services.py`
- [x] Create auth schemas in `app/blueprints/auth/schemas.py`
- [x] Implement auth routes in `app/blueprints/auth/routes.py`
- [x] Register auth blueprint via api_v1 in `app/blueprints/api/v1/__init__.py`

### Core Decorators
- [x] Implement `@jwt_required` decorator in `app/core/decorators.py`
- [x] Implement `@require_permission(permission_name)` decorator
  - ✓ Supports single permission or list of permissions
  - ✓ `require_all` option for AND logic
  - ✓ Checks tenant-wide and store-specific roles
- [x] Implement `@require_tenant` decorator
- [x] Implement `@require_store` decorator
- [x] Utility functions: `has_permission()`, `has_any_permission()`, `get_user_permissions()`

### Permission System
- [x] Define permission constants in `app/core/constants.py`
  - ✓ 48 permissions defined across 15 resources
  - ✓ Permissions class with all constants
  - ✓ ALL_PERMISSIONS list for seeding
  - ✓ DEFAULT_ROLES with Owner, Admin, Manager, Cashier, Viewer
- [x] Create permission seeding migration
  - ✓ Migration 88ee7b9c4387 seeds all permissions
- [x] Implement permission checking logic
  - ✓ Already implemented in decorators.py (get_user_permissions, has_permission, etc.)

## 📋 Medium Priority

### User Management
- [x] Implement UserService in `app/blueprints/users/services.py`
  - ✓ get_current_user(), get_current_user_details()
  - ✓ update_current_user() with password change
  - ✓ list_users() with pagination, search, filtering
  - ✓ get_user(), create_user(), update_user(), deactivate_user()
- [x] Create user schemas in `app/blueprints/users/schemas.py`
  - ✓ UserResponseSchema, UserDetailResponseSchema
  - ✓ UpdateCurrentUserSchema, CreateUserSchema, UpdateUserSchema
  - ✓ UserListQuerySchema, UserListResponseSchema
- [x] Implement user routes in `app/blueprints/users/routes.py`
  - ✓ GET /api/v1/users/me
  - ✓ PUT /api/v1/users/me
  - ✓ GET /api/v1/users
  - ✓ GET /api/v1/users/:id
  - ✓ POST /api/v1/users
  - ✓ PUT /api/v1/users/:id
  - ✓ DELETE /api/v1/users/:id

### Tenant Management
- [x] Implement TenantService in `app/blueprints/tenants/services.py`
  - ✓ get_current_tenant(), get_current_tenant_details()
  - ✓ update_current_tenant() with slug duplicate check
- [x] Create tenant schemas in `app/blueprints/tenants/schemas.py`
  - ✓ TenantResponseSchema, TenantDetailResponseSchema
  - ✓ UpdateTenantSchema
- [x] Implement tenant routes in `app/blueprints/tenants/routes.py`
  - ✓ GET /api/v1/tenants/current
  - ✓ PUT /api/v1/tenants/current

### Store Management
- [x] Implement StoreService in `app/blueprints/stores/services.py`
  - ✓ list_stores() with pagination, search, filtering
  - ✓ get_store(), create_store(), update_store(), delete_store()
  - ✓ get_store_users(), assign_users_to_store(), remove_users_from_store()
- [x] Create store schemas in `app/blueprints/stores/schemas.py`
  - ✓ StoreResponseSchema, StoreDetailResponseSchema
  - ✓ CreateStoreSchema, UpdateStoreSchema
  - ✓ StoreListQuerySchema, StoreListResponseSchema
  - ✓ StoreUserAssignmentSchema
- [x] Implement store routes in `app/blueprints/stores/routes.py`
  - ✓ GET /api/v1/stores
  - ✓ GET /api/v1/stores/:id
  - ✓ POST /api/v1/stores
  - ✓ PUT /api/v1/stores/:id
  - ✓ DELETE /api/v1/stores/:id
  - ✓ GET /api/v1/stores/:id/users
  - ✓ POST /api/v1/stores/:id/users
  - ✓ DELETE /api/v1/stores/:id/users

### RBAC Management
- [x] Implement RBACService in `app/blueprints/rbac/services.py`
  - ✓ list_roles(), get_role(), create_role(), update_role(), delete_role()
  - ✓ list_permissions() with resource filtering
  - ✓ get_user_roles(), assign_role_to_user(), revoke_role_from_user()
- [x] Create RBAC schemas in `app/blueprints/rbac/schemas.py`
  - ✓ RoleResponseSchema, RoleDetailResponseSchema
  - ✓ CreateRoleSchema, UpdateRoleSchema
  - ✓ PermissionResponseSchema, PermissionListResponseSchema
  - ✓ AssignRoleSchema, UserRolesResponseSchema
- [x] Implement RBAC routes in `app/blueprints/rbac/routes.py`
  - ✓ GET /api/v1/roles
  - ✓ GET /api/v1/roles/:id
  - ✓ POST /api/v1/roles
  - ✓ PUT /api/v1/roles/:id
  - ✓ DELETE /api/v1/roles/:id
  - ✓ GET /api/v1/permissions
  - ✓ GET /api/v1/users/:id/roles
  - ✓ POST /api/v1/users/:id/roles
  - ✓ DELETE /api/v1/users/:id/roles/:role_id

## 📦 Low Priority (Future)

### Testing
- [x] Set up pytest configuration in pytest.ini
- [x] Create test fixtures in tests/conftest.py
- [x] Write authentication tests (tests/test_auth.py)
- [x] Write tenant isolation tests (tests/test_tenant_isolation.py)
- [x] Write RBAC tests (tests/test_rbac.py)
- [x] Write API endpoint tests (tests/test_api_users.py, test_api_stores.py, test_api_tenants.py)
- [x] Write health check tests (tests/test_health.py)
- [x] **Fix test fixtures** - 107 tests now passing (up from 84)
- [ ] **Fix remaining app bugs** - 8 tests failing due to app code issues (see Bugs section)

### Health Checks
- [x] Implement health check routes
  - ✓ GET /health - Basic liveness probe
  - ✓ GET /health/db - Database connectivity check
  - ✓ Added to middleware exempt paths

### Development Tools
- [ ] Create run.py for development server
- [ ] Set up docker-compose.yml for local development
- [ ] Add logging configuration
- [ ] Add request/response logging

### Subscription System
- [ ] Define Subscription and Plan models
- [ ] Implement subscription service
- [ ] Create subscription routes

### Billing System
- [ ] Define billing models (Invoice, Transaction)
- [ ] Implement billing service
- [ ] Create billing routes

### Payment Integration
- [ ] M-Pesa Daraja API integration
- [ ] Payment service implementation
- [ ] Payment callback handling

### Notifications
- [ ] Notification models
- [ ] Email service integration
- [ ] Notification service
- [ ] Notification routes

### Usage Tracking
- [ ] Usage metric models
- [ ] Usage tracking service
- [ ] Usage reporting endpoints

## 🐛 Bugs/Issues

- [ ] Empty files need implementation (run.py, docker-compose.yml)
- [x] Blueprint registration missing in app/__init__.py - auth blueprint registered
- [x] No error handlers registered yet - error handlers registered
- [x] User model foreign_keys ambiguity - fixed relationships with explicit foreign_keys
- [x] **Test fixture issues fixed** - 107 tests now passing (was 84)
- [ ] **Application bugs discovered by tests** (8 failing tests):
  1. **TenantStatus enum not JSON serializable** - `app/blueprints/tenants/` needs `.value` when serializing status
  2. **UpdateCurrentUserSchema.validate_new_password()** - Wrong signature in `app/blueprints/users/schemas.py`
  3. **User roles response structure** - `test_get_user_roles` expects role name but gets None
  4. **Tenant endpoint requires permissions** - `/tenants/current` GET returns 403 even with valid auth

## 📝 Documentation

- [ ] API documentation with Swagger/OpenAPI
- [ ] Authentication flow documentation
- [ ] Postman collection for API testing
- [ ] Development guide for new contributors

## 🔧 DevOps

- [ ] Dockerfile for production
- [ ] Docker Compose for development environment
- [ ] CI/CD pipeline setup
- [ ] Production deployment guide
- [ ] Database backup strategy

## ✅ Completed

- [x] Project structure created
- [x] Core models defined and organized into blueprint files
- [x] Architecture documentation created
- [x] CLAUDE.md, plan.md, progress.md, todo.md, notes.md created
- [x] README.md created
- [x] Environment configuration setup
- [x] Flask application factory implemented
- [x] Models imported in app/__init__.py for migration discovery
- [x] Initial database migration created and applied
- [x] Database tables created (users, tenants, stores, roles, permissions, junction tables)
- [x] Authentication system (login, register, refresh, bootstrap)
- [x] User management endpoints (7 routes)
- [x] Tenant management endpoints (2 routes)
- [x] Store management endpoints (8 routes)
- [x] RBAC management endpoints (9 routes)
- [x] All core blueprints registered in api_v1
- [x] Health check endpoints (2 routes)
- [x] Testing infrastructure setup (2025-12-09)
  - pytest.ini configured with markers (unit, integration, auth, rbac, tenant)
  - Comprehensive fixtures in tests/conftest.py
  - Test files: test_auth.py, test_tenant_isolation.py, test_rbac.py, test_api_users.py, test_api_stores.py, test_api_tenants.py, test_health.py
  - **107 tests passing, 8 failing** (app bugs identified)
