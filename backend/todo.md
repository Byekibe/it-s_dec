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
- [ ] **Implement JWT utilities** in `app/core/utils.py`
  - JWT token generation
  - JWT token validation
  - Token payload extraction
- [ ] **Implement custom exceptions** in `app/core/exceptions.py`
  - NotFoundError
  - ForbiddenError
  - UnauthorizedError
  - TenantNotFoundError
  - InvalidCredentialsError
- [ ] **Create TenantMiddleware** in `app/core/middleware.py`
- [ ] **Create StoreMiddleware** in `app/core/middleware.py`
- [ ] **Register middleware** in `app/__init__.py`

## 🎯 High Priority

### Authentication System
- [ ] Implement AuthService in `app/blueprints/auth/services.py`
  - register() method
  - login() method
  - refresh_token() method
- [ ] Create auth schemas in `app/blueprints/auth/schemas.py`
  - LoginSchema
  - RegisterSchema
  - TokenResponseSchema
- [ ] Implement auth routes in `app/blueprints/auth/routes.py`
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
- [ ] Create bootstrap script or endpoint for first user/tenant
- [ ] Register auth blueprint in `app/__init__.py`

### Core Decorators
- [ ] Implement `@jwt_required` decorator in `app/core/decorators.py`
- [ ] Implement `@require_permission(permission_name)` decorator
- [ ] Implement `@require_tenant` decorator
- [ ] Implement `@require_store` decorator

### Permission System
- [ ] Define permission constants in `app/core/constants.py`
- [ ] Create permission seeding migration
- [ ] Implement permission checking logic

## 📋 Medium Priority

### User Management
- [ ] Implement UserService in `app/blueprints/users/services.py`
- [ ] Implement UserRepository in `app/blueprints/users/repositories.py`
- [ ] Create user schemas in `app/blueprints/users/schemas.py`
- [ ] Implement user routes
  - GET /api/v1/users/me
  - PUT /api/v1/users/me
  - GET /api/v1/users (admin only)

### Tenant Management
- [ ] Implement TenantService
- [ ] Implement TenantRepository
- [ ] Create tenant schemas
- [ ] Implement tenant routes
  - GET /api/v1/tenants/current
  - PUT /api/v1/tenants/current

### Store Management
- [ ] Implement StoreService
- [ ] Implement StoreRepository
- [ ] Create store schemas
- [ ] Implement store routes
  - POST /api/v1/stores
  - GET /api/v1/stores
  - GET /api/v1/stores/:id
  - PUT /api/v1/stores/:id
  - DELETE /api/v1/stores/:id

### RBAC Management
- [ ] Implement RBACService
- [ ] Implement RoleRepository and PermissionRepository
- [ ] Create RBAC schemas
- [ ] Implement RBAC routes
  - GET /api/v1/roles
  - POST /api/v1/roles
  - POST /api/v1/users/:id/roles
  - GET /api/v1/permissions

## 📦 Low Priority (Future)

### Testing
- [ ] Set up pytest configuration in pytest.ini
- [ ] Create test fixtures in tests/conftest.py
- [ ] Write authentication tests
- [ ] Write tenant isolation tests
- [ ] Write RBAC tests
- [ ] Write API endpoint tests

### Health Checks
- [ ] Implement health check routes
  - GET /health
  - GET /health/db

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

- [ ] Empty files need implementation (run.py, docker-compose.yml, pytest.ini)
- [ ] Blueprint registration missing in app/__init__.py
- [ ] No error handlers registered yet

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
