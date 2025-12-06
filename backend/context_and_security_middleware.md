# Context and Security Middleware Architecture

This document outlines the design and implementation of the security middleware layer, which is responsible for enforcing data isolation and context management for every API request in the multi-tenant application.

## 1. Introduction: The Gatekeeper

The security middleware acts as a gatekeeper for the entire application. Its primary responsibilities are:

1.  **Authentication:** Verifying the identity of the user making the request.
2.  **Tenant Scoping:** Identifying which tenant the request belongs to and ensuring the user is a valid member of that tenant.
3.  **Store Scoping (Optional):** Identifying a specific store context if the request requires it.
4.  **Context Establishment:** Making the validated user, tenant, and store objects globally available for the duration of the request.

This layer is critical for security, as it ensures that all subsequent business logic operates within the correct, isolated data partition.

---

## 2. Middleware Implementation Strategy

We will implement two separate middleware components that run in sequence. They will be registered with the Flask application to execute on incoming requests.

### 2.1. `TenantMiddleware`

This is the first and most important security checkpoint. It runs on every authenticated API request.

**Responsibilities:**

*   Extract the JWT from the `Authorization: Bearer <token>` header.
*   Decode and validate the JWT to retrieve the `user_id` and `tenant_id`.
*   Fetch the `User` and `Tenant` objects from the database.
*   Perform critical validation checks:
    *   Does the user exist and are they active (`is_active == True`)?
    *   Does the tenant exist and is it active (`status == 'active'`)?
    *   Is the user actually a member of the tenant (check `TenantUser` link table)?
*   If all checks pass, attach the validated objects to Flask's request-local `g` object (e.g., `g.user`, `g.tenant`).
*   If any check fails, immediately halt the request and return a `401 Unauthorized` or `403 Forbidden` error.

**Example Flow:**

1.  Request arrives: `GET /api/v1/stores` with `Authorization` header.
2.  `TenantMiddleware` extracts the token.
3.  Token is decoded, yielding `user_id` and `tenant_id`.
4.  Database is queried for the user and tenant.
5.  Membership is confirmed.
6.  `g.user = <User object>` and `g.tenant = <Tenant object>` are set.
7.  The request is passed to the next stage.

### 2.2. `StoreMiddleware`

This middleware runs *after* `TenantMiddleware` and is only concerned with requests that need to be scoped to a specific store.

**Responsibilities:**

*   Check for a store identifier in the request, typically an `X-Store-ID` header.
*   If the header is present:
    *   Retrieve the `store_id` from the header.
    *   Query the database to verify that the store exists and belongs to the current tenant (`store.tenant_id == g.tenant.id`).
    *   Verify that the current user is assigned to that store (check `StoreUser` link table).
*   If validation passes, attach the store object to the context: `g.store = <Store object>`.
*   If the header is present but validation fails, return a `403 Forbidden` error.
*   If the header is not present, the middleware does nothing.

---

## 3. Advanced: Automatic Tenant Query Filtering

To provide a non-bypassable "safety net" against data leaks, we will implement an event listener that automatically scopes all relevant database queries to the current tenant.

**Purpose:** This ensures that even if a developer forgets to add a `.filter(tenant_id=...)` clause in their code, data from other tenants can never be returned.

**Mechanism:**

We will use SQLAlchemy's event system to hook into the ORM execution process.

*   **Event:** `@event.listens_for(Session, 'do_orm_execute')`
*   **Logic:**
    1.  The hook function first checks if it is running within an active request context that has a `g.tenant`.
    2.  It then inspects the query being executed to identify the target model (e.g., `Store`, `Role`, `Product`).
    3.  If the target model is a subclass of our `TenantScopedModel` (meaning it has a `tenant_id` column), the hook **automatically injects a `WHERE` clause** into the query.
    4.  For example, a call to `db.session.query(Store).all()` is dynamically rewritten to `db.session.query(Store).filter(Store.tenant_id == g.tenant.id).all()` before being sent to the database.

**Benefit:**

This powerful pattern makes application code cleaner and dramatically enhances security. Developers can write `Product.query.all()` and trust that the framework will handle the tenant isolation automatically and securely.

---

## 4. Example Request Lifecycle

A complete request to fetch resources for a specific store (`GET /api/v1/products?store_id=...`) would flow like this:

1.  **Request In:** The request hits the Flask application.
2.  **`TenantMiddleware`:**
    *   Validates the JWT.
    *   Sets `g.user` and `g.tenant`.
3.  **`StoreMiddleware`:**
    *   Sees the `store_id` parameter (or an `X-Store-ID` header).
    *   Validates that `g.user` has access to this store within `g.tenant`.
    *   Sets `g.store`.
4.  **View/Controller Logic:**
    *   The route handler is executed.
    *   It calls `Product.query.filter_by(store_id=g.store.id).all()`.
5.  **SQLAlchemy Hook:**
    *   The `'do_orm_execute'` event is triggered.
    *   The hook sees the query is on `Product`, which is a `TenantScopedModel`.
    *   It adds an additional filter: `WHERE products.tenant_id = g.tenant.id`.
    *   The final, secure query is sent to the database.
6.  **Response Out:** The correctly filtered data is returned to the user as JSON.
