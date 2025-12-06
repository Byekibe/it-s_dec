# Development Notes

## Project Overview Notes

This is a multi-tenant SaaS backend built with Flask. The key architectural pattern is strict data isolation at the tenant level, enforced through middleware and automatic query filtering.

---

## Architecture Decisions

### Multi-Tenancy Approach

**Decision**: Shared database with tenant_id column (Row-Level Multi-Tenancy)

**Rationale**:
- More cost-effective than separate databases per tenant
- Easier to maintain and update
- Sufficient isolation for most SaaS applications
- Performance is manageable with proper indexing

**Trade-offs**:
- Must be extremely careful about tenant isolation in queries
- Risk of data leaks if middleware fails
- Cannot easily give tenants their own database backups

**Mitigation**:
- Automatic query filtering via SQLAlchemy hooks
- Comprehensive middleware validation
- Extensive testing of tenant isolation

### Authentication Strategy

**Decision**: JWT-based authentication with tenant_id in token

**Structure**:
```json
{
  "user_id": "uuid",
  "tenant_id": "uuid",
  "iat": timestamp,
  "exp": timestamp
}
```

**Why include tenant_id in JWT?**
- Avoids database lookup on every request to find user's tenant
- Enables stateless authentication
- Middleware can validate tenant access immediately

**Considerations**:
- User switching between tenants requires new token
- Token must be invalidated if user is removed from tenant

### Model Inheritance Pattern

**Decision**: Abstract base classes for common functionality

```
BaseModel → TenantScopedModel → StoreScopedModel
```

**Benefits**:
- DRY principle for common fields (id, timestamps, tenant_id, etc.)
- Consistent behavior across all models
- Easy to identify which models need tenant filtering

### Blueprint Organization

**Decision**: Feature-based blueprints with consistent structure

Each blueprint contains:
- models.py (data models)
- services.py (business logic)
- repositories.py (data access)
- routes.py (API endpoints)
- schemas.py (validation)

**Rationale**:
- Clear separation of concerns
- Easy to navigate codebase
- Each feature is self-contained
- Testable in isolation

---

## Security Considerations

### Critical Security Layers

1. **TenantMiddleware**: First line of defense - validates user/tenant relationship
2. **SQLAlchemy Query Hook**: Safety net - auto-filters queries by tenant
3. **Permission Decorators**: Ensures user has required permissions
4. **Input Validation**: Marshmallow schemas validate all inputs

### Known Security Risks

⚠️ **Bootstrap Endpoint**: The initial user creation must bypass tenant middleware. This endpoint should be:
- Disabled after first use
- Protected by environment variable flag
- Only accessible in development/setup mode

⚠️ **JWT Secret Keys**: Must be different in development vs production
- Never commit production secrets to git
- Use strong, randomly generated keys in production
- Rotate keys periodically

⚠️ **SQL Injection**: Using SQLAlchemy ORM mitigates this, but:
- Never use raw SQL with user input
- If raw SQL is needed, always use parameterized queries

---

## Database Notes

### Migration Strategy

- Alembic migrations for all schema changes
- Never modify database schema directly in production
- Always review auto-generated migrations before applying
- Test migrations on staging/copy of production data first

### UUID vs Auto-increment IDs

**Decision**: Use UUIDs for all primary keys

**Rationale**:
- Prevents enumeration attacks
- Can generate IDs client-side if needed
- Easier to merge data from different sources
- No conflicts when scaling to multiple databases

**Trade-offs**:
- Slightly larger storage (16 bytes vs 4-8 bytes)
- Slightly slower indexing
- Not human-readable

### Soft Deletes

**Decision**: Implement soft deletes for tenant-scoped models

**Why?**
- Enables data recovery
- Maintains referential integrity
- Useful for audit trails
- Can comply with data retention policies

**Implementation**:
- `deleted_at` timestamp column (NULL = not deleted)
- Queries must filter out deleted records
- Consider adding `is_deleted` property for convenience

---

## Performance Considerations

### Database Indexing

**Critical indexes** (must have):
- `tenant_id` on all tenant-scoped tables
- `user_id` on junction tables
- `email` on users table (unique)
- `slug` on tenants table (unique)

**Composite indexes** (for common queries):
- `(tenant_id, is_active)` on stores
- `(tenant_id, name)` on roles
- `(user_id, tenant_id)` on tenant_users
- `(user_id, tenant_id)` on user_roles

### Query Optimization

- Use `.options(joinedload())` for eager loading relationships
- Avoid N+1 queries with proper relationship loading
- Consider pagination for all list endpoints
- Add database query logging in development to identify slow queries

---

## Development Workflow Notes

### Local Development Setup

1. Always activate virtual environment first
2. Keep .env in sync with .env.example (but never commit .env)
3. Run migrations before starting development
4. Use `flask run` for development (auto-reload enabled)

### Testing Strategy

**Test Pyramid**:
- Many unit tests (services, utilities)
- Moderate integration tests (API endpoints)
- Few end-to-end tests (critical user flows)

**Critical test scenarios**:
- User cannot access data from other tenants
- User cannot access stores they're not assigned to
- Permission decorators correctly block unauthorized actions
- JWT expiration is honored
- Soft-deleted records are properly excluded

### Common Gotchas

🔴 **Forgetting tenant_id filter**: SQLAlchemy hook should catch this, but be aware

🔴 **Circular imports**: Be careful with imports between models, services, and routes
- Use lazy imports if needed
- Keep dependencies unidirectional

🔴 **Migration conflicts**: Always pull latest migrations before creating new ones

🔴 **JWT expiration**: Default is 1 hour (3600 seconds) - may need adjustment

---

## Future Technical Debt

### Known Issues to Address

1. **Async/Background Tasks**: No task queue implemented yet
   - Will need Celery or similar for:
     - Email sending
     - Invoice generation
     - Usage aggregation
     - Payment processing

2. **Caching**: No caching layer
   - Consider Redis for:
     - Session storage
     - Rate limiting
     - Frequently accessed data

3. **API Versioning**: Currently using v1, but no versioning strategy defined
   - Need to decide: URL versioning vs header versioning
   - How to deprecate old versions
   - How to maintain multiple versions

4. **Logging**: Basic logging only
   - Need structured logging
   - Centralized log aggregation
   - Error tracking (Sentry?)

5. **Monitoring**: No monitoring implemented
   - Application performance monitoring
   - Database query monitoring
   - Alert system for errors/downtime

---

## Useful Commands Reference

### Database
```bash
# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade

# Show current migration
flask db current

# Show migration history
flask db history
```

### Python/Pip
```bash
# Install new package and update requirements
pip install package_name
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_file.py::test_function

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## Questions/Decisions Needed

- [ ] What email service to use? (SendGrid, AWS SES, etc.)
- [ ] What payment gateways besides M-Pesa? (Stripe, PayPal?)
- [ ] Rate limiting strategy? (per user, per tenant, per endpoint?)
- [ ] File storage for uploads? (S3, local, etc.)
- [ ] Production database: PostgreSQL version?
- [ ] Deployment platform? (AWS, GCP, Azure, Heroku, DigitalOcean?)
- [ ] CI/CD tool? (GitHub Actions, GitLab CI, Jenkins?)

---

## Resources & References

### Documentation
- Flask: https://flask.palletsprojects.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Flask-Migrate: https://flask-migrate.readthedocs.io/
- Marshmallow: https://marshmallow.readthedocs.io/
- PyJWT: https://pyjwt.readthedocs.io/

### Similar Projects/Patterns
- Look at SaaS Boilerplate projects for reference
- Study other multi-tenant implementations
- Review OWASP guidelines for multi-tenant security

---

## Changelog

### 2025-12-06
- Initial project setup
- Core models defined
- Architecture documentation created
- CLAUDE.md, plan.md, progress.md, todo.md, notes.md created
