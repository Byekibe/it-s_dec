# TODO List - Multi-Tenant SaaS Core

**Goal**: Complete a reusable multi-tenant SaaS foundation that can power any B2B application (POS, Property Management, etc.)

**Last Updated**: 2025-12-12

---

## 🎯 Core Completion Roadmap

### Phase 1: Foundation ✅ COMPLETE
- [x] Multi-tenant data models (User, Tenant, Store)
- [x] Security middleware (TenantMiddleware, StoreMiddleware)
- [x] Authentication system (JWT, login, register, password reset, email verification)
- [x] User management (CRUD, invitations, multi-tenant users)
- [x] RBAC system (roles, permissions, tenant & store-level)
- [x] Store/location management
- [x] Subscription & plan management with limits
- [x] Settings (tenant and store level)
- [x] Health check endpoints
- [x] Testing infrastructure (216 tests passing)
- [x] Docker & Celery setup

### Phase 2: Core Features 🔄 IN PROGRESS
- [ ] **Audit Logging** - Track who did what, when
- [ ] **Notifications System** - In-app, email, push
- [ ] **File Storage** - Attachments, avatars, documents

### Phase 3: Integration & Polish
- [ ] **Webhooks** - Event notifications to external systems
- [ ] **API Keys** - Service-to-service authentication
- [ ] **API Documentation** - OpenAPI/Swagger
- [ ] **Admin Dashboard Endpoints** - Super admin features

---

## 🔥 High Priority - Phase 2 Tasks

### Audit Logging System
Track all significant actions for compliance, debugging, and accountability.

**Models:**
- [ ] `AuditLog` model with fields:
  - `id`, `tenant_id`, `user_id`, `action`, `resource_type`, `resource_id`
  - `old_values` (JSON), `new_values` (JSON)
  - `ip_address`, `user_agent`, `created_at`

**Implementation:**
- [ ] Create `app/blueprints/audit/` blueprint
- [ ] AuditService for logging events
- [ ] Decorator `@audit_action("resource.action")` for automatic logging
- [ ] SQLAlchemy event listeners for model changes (optional)
- [ ] Routes:
  - [ ] GET /api/v1/audit - List audit logs (with filters)
  - [ ] GET /api/v1/audit/:id - Get specific log entry
  - [ ] GET /api/v1/audit/export - Export audit logs (CSV/JSON)

**Permissions:**
- [ ] `audit.view` - View audit logs
- [ ] `audit.export` - Export audit data

**Tests:**
- [ ] Audit log creation on user actions
- [ ] Filtering and pagination
- [ ] Permission enforcement

---

### Notifications System
Unified notification system for in-app alerts, emails, and future push notifications.

**Models:**
- [ ] `Notification` model:
  - `id`, `tenant_id`, `user_id`, `type` (info, warning, success, error)
  - `title`, `message`, `data` (JSON for action links, etc.)
  - `channel` (in_app, email, push)
  - `read_at`, `sent_at`, `created_at`
- [ ] `NotificationPreference` model:
  - `user_id`, `notification_type`, `email_enabled`, `in_app_enabled`, `push_enabled`

**Implementation:**
- [ ] Create `app/blueprints/notifications/` blueprint
- [ ] NotificationService for creating and sending notifications
- [ ] Background task for sending emails/push
- [ ] Routes:
  - [ ] GET /api/v1/notifications - List user's notifications
  - [ ] GET /api/v1/notifications/unread-count - Get unread count
  - [ ] PUT /api/v1/notifications/:id/read - Mark as read
  - [ ] PUT /api/v1/notifications/read-all - Mark all as read
  - [ ] DELETE /api/v1/notifications/:id - Delete notification
  - [ ] GET /api/v1/notifications/preferences - Get preferences
  - [ ] PUT /api/v1/notifications/preferences - Update preferences

**Notification Types (to implement):**
- [ ] User invited to tenant
- [ ] Password changed
- [ ] Subscription expiring
- [ ] Plan limit approaching
- [ ] Generic system announcements

**Tests:**
- [ ] Notification CRUD
- [ ] Mark as read functionality
- [ ] Preference management
- [ ] Email sending integration

---

### File Storage System
Generic file upload/download for avatars, documents, attachments.

**Models:**
- [ ] `File` model:
  - `id`, `tenant_id`, `uploaded_by`
  - `filename`, `original_filename`, `content_type`, `size`
  - `storage_path`, `storage_backend` (local, s3)
  - `entity_type`, `entity_id` (polymorphic attachment)
  - `is_public`, `created_at`

**Implementation:**
- [ ] Create `app/blueprints/files/` blueprint
- [ ] FileService with storage backend abstraction
- [ ] Local storage backend (for development)
- [ ] S3-compatible storage backend (for production)
- [ ] Routes:
  - [ ] POST /api/v1/files - Upload file
  - [ ] GET /api/v1/files/:id - Get file metadata
  - [ ] GET /api/v1/files/:id/download - Download file
  - [ ] DELETE /api/v1/files/:id - Delete file
  - [ ] POST /api/v1/users/me/avatar - Upload user avatar (convenience)

**Configuration:**
- [ ] `FILE_STORAGE_BACKEND` (local, s3)
- [ ] `FILE_UPLOAD_MAX_SIZE`
- [ ] `FILE_ALLOWED_EXTENSIONS`
- [ ] S3 credentials (for production)

**Tests:**
- [ ] File upload/download
- [ ] File deletion
- [ ] Permission checks
- [ ] Size and type validation

---

## 📋 Medium Priority - Phase 3 Tasks

### Webhooks System
Allow tenants to receive event notifications at their endpoints.

**Models:**
- [ ] `Webhook` model:
  - `id`, `tenant_id`, `url`, `secret`
  - `events` (JSON array of subscribed events)
  - `is_active`, `created_at`
- [ ] `WebhookDelivery` model:
  - `id`, `webhook_id`, `event`, `payload`
  - `response_status`, `response_body`
  - `delivered_at`, `created_at`

**Implementation:**
- [ ] WebhookService for managing webhooks
- [ ] Event dispatcher for triggering webhooks
- [ ] Background task for webhook delivery with retry
- [ ] Routes:
  - [ ] GET /api/v1/webhooks - List webhooks
  - [ ] POST /api/v1/webhooks - Create webhook
  - [ ] PUT /api/v1/webhooks/:id - Update webhook
  - [ ] DELETE /api/v1/webhooks/:id - Delete webhook
  - [ ] GET /api/v1/webhooks/:id/deliveries - List recent deliveries
  - [ ] POST /api/v1/webhooks/:id/test - Send test event

**Events to support:**
- [ ] `user.created`, `user.updated`, `user.deleted`
- [ ] `subscription.changed`, `subscription.canceled`
- [ ] `store.created`, `store.updated`
- [ ] App-specific events (added per app)

---

### API Keys System
Machine-to-machine authentication for integrations.

**Models:**
- [ ] `APIKey` model:
  - `id`, `tenant_id`, `name`, `key_hash` (hashed, never store plain)
  - `key_prefix` (first 8 chars for identification)
  - `scopes` (JSON array of allowed permissions)
  - `last_used_at`, `expires_at`, `created_at`

**Implementation:**
- [ ] APIKeyService for key management
- [ ] Middleware to authenticate API key requests
- [ ] Routes:
  - [ ] GET /api/v1/api-keys - List API keys (without full key)
  - [ ] POST /api/v1/api-keys - Create API key (returns full key once)
  - [ ] DELETE /api/v1/api-keys/:id - Revoke API key
  - [ ] PUT /api/v1/api-keys/:id - Update key name/scopes

**Security:**
- [ ] Keys shown only once at creation
- [ ] Keys stored as hashes
- [ ] Rate limiting per key
- [ ] Scope restrictions

---

### API Documentation
Auto-generated API documentation.

- [ ] Set up Flask-RESTX or Flasgger for OpenAPI
- [ ] Document all existing endpoints
- [ ] Swagger UI at /api/docs
- [ ] Export OpenAPI spec

---

## 📦 Low Priority (Future)

### Session Management
- [ ] GET /api/v1/auth/sessions - List active sessions
- [ ] DELETE /api/v1/auth/sessions/:id - Revoke specific session
- [ ] Session model with device, IP, last activity

### Profile Enhancements
- [ ] User avatar upload (uses File Storage)
- [ ] User preferences/settings model

### Tenant Branding
- [ ] Tenant logo upload
- [ ] Custom colors/theme settings

### Billing/Invoicing (Generic)
- [ ] Invoice model
- [ ] InvoiceService
- [ ] PDF generation
- [ ] (Note: Payment processing like M-Pesa may be app-specific)

### Rate Limiting
- [ ] Redis-based rate limiting
- [ ] Per-endpoint and per-user limits
- [ ] Rate limit headers in responses

### Two-Factor Authentication
- [ ] TOTP support (Google Authenticator)
- [ ] Backup codes
- [ ] 2FA enforcement per tenant

---

## ✅ Completed

### Core Infrastructure
- [x] Project structure and configuration
- [x] Flask application factory
- [x] Environment-based config (dev, test, prod)
- [x] Database migrations with Flask-Migrate
- [x] Docker & docker-compose setup
- [x] Celery for background tasks
- [x] Flask-Mail for emails

### Data Models
- [x] BaseModel, TenantScopedModel, StoreScopedModel
- [x] User model with password hashing
- [x] Tenant, TenantUser models
- [x] Store, StoreUser, StoreSettings models
- [x] Role, Permission, UserRole, RolePermission models
- [x] Plan, Subscription models
- [x] Token models (blacklist, reset, verification, invitation)
- [x] TenantSettings model

### Security
- [x] JWT token generation and validation
- [x] TenantMiddleware (context from token)
- [x] StoreMiddleware (X-Store-ID header)
- [x] Permission decorators
- [x] Subscription limit decorators

### Authentication (12 endpoints)
- [x] POST /auth/login
- [x] POST /auth/register
- [x] POST /auth/refresh
- [x] POST /auth/bootstrap
- [x] POST /auth/logout
- [x] POST /auth/logout-all
- [x] POST /auth/forgot-password
- [x] POST /auth/reset-password
- [x] POST /auth/verify-email
- [x] POST /auth/resend-verification
- [x] POST /auth/accept-invite
- [x] POST /auth/switch-tenant

### User Management (9 endpoints)
- [x] GET /users/me
- [x] PUT /users/me
- [x] GET /users/me/tenants
- [x] GET /users
- [x] GET /users/:id
- [x] POST /users
- [x] PUT /users/:id
- [x] DELETE /users/:id
- [x] POST /users/invite

### Tenant Management (4 endpoints)
- [x] GET /tenants/current
- [x] PUT /tenants/current
- [x] GET /tenants/current/settings
- [x] PUT /tenants/current/settings

### Store Management (10 endpoints)
- [x] GET /stores
- [x] GET /stores/:id
- [x] POST /stores
- [x] PUT /stores/:id
- [x] DELETE /stores/:id
- [x] GET /stores/:id/users
- [x] POST /stores/:id/users
- [x] DELETE /stores/:id/users
- [x] GET /stores/:id/settings
- [x] PUT /stores/:id/settings

### RBAC Management (9 endpoints)
- [x] GET /roles
- [x] GET /roles/:id
- [x] POST /roles
- [x] PUT /roles/:id
- [x] DELETE /roles/:id
- [x] GET /permissions
- [x] GET /users/:id/roles
- [x] POST /users/:id/roles
- [x] DELETE /users/:id/roles/:role_id

### Subscription Management (10 endpoints)
- [x] GET /subscriptions/plans
- [x] GET /subscriptions/plans/:id
- [x] GET /subscriptions/current
- [x] GET /subscriptions/current/details
- [x] GET /subscriptions/current/usage
- [x] GET /subscriptions/current/trial
- [x] POST /subscriptions/current/change-plan
- [x] POST /subscriptions/current/cancel
- [x] POST /subscriptions/current/reactivate
- [x] PUT /subscriptions/current/payment-method

### Health (2 endpoints)
- [x] GET /health
- [x] GET /health/db

### Testing
- [x] pytest configuration
- [x] Comprehensive fixtures
- [x] 216 tests passing
- [x] test_auth.py
- [x] test_tenant_isolation.py
- [x] test_rbac.py
- [x] test_api_users.py
- [x] test_api_stores.py
- [x] test_api_tenants.py
- [x] test_health.py
- [x] test_subscriptions.py

---

## 📊 Metrics

- **Total API Endpoints**: 56
- **Tests Passing**: 216
- **Blueprints Implemented**: 6 core + 1 health
- **Database Tables**: 14
- **Permissions Defined**: 50
