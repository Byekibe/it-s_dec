# CLI Commands Reference

This document describes the CLI commands available for managing the application.

## Overview

Flask CLI commands are organized into groups:

| Group | Purpose |
|-------|---------|
| `flask db-commands` | Database management (create, drop, reset tables) |
| `flask db` | Database migrations (Flask-Migrate/Alembic) |
| `flask seed` | Seed data (permissions, roles, demo data) |
| `flask users` | User management (create, list, roles) |

---

## Database Commands

### `flask db-commands`

Low-level database table management (bypasses migrations).

```bash
flask db-commands create   # Create all tables
flask db-commands drop     # Drop all tables
flask db-commands reset    # Drop + Create (full reset)
```

### `flask db` (Migrations)

Standard Flask-Migrate commands for schema versioning.

```bash
flask db init              # Initialize migrations (first time only)
flask db migrate -m "msg"  # Generate migration from model changes
flask db upgrade           # Apply pending migrations
flask db downgrade         # Rollback last migration
flask db current           # Show current migration version
flask db history           # Show migration history
```

---

## Seed Commands

### `flask seed permissions`

Seeds all 48 permissions into the database. This is also done automatically via migration, but can be run manually if needed.

```bash
flask seed permissions
```

Output:
```
Permissions seeded: 48 created, 0 skipped (already exist)
```

### `flask seed roles <tenant_slug>`

Seeds default roles (Owner, Admin, Manager, Cashier, Viewer) for a specific tenant.

```bash
flask seed roles acme-corp
```

Output:
```
  Created: Owner (48 permissions)
  Created: Admin (22 permissions)
  Created: Manager (21 permissions)
  Created: Cashier (7 permissions)
  Created: Viewer (7 permissions)

Roles seeded for tenant 'Acme Corp': 5 created, 0 skipped
```

### `flask seed demo`

Seeds complete demo data for testing and development.

```bash
# With defaults
flask seed demo

# With custom options
flask seed demo \
  --tenant-name "Acme Corp" \
  --owner-email "owner@acme.com" \
  --password "secure123"
```

**What it creates:**
- 1 Tenant (trial status, 14-day trial)
- 5 Users: owner, admin, manager, cashier, viewer
- 5 Roles with proper permissions
- 1 Store with all users assigned

Output:
```
Seeding demo data...
  Created tenant: Acme Corp (acme-corp)
  Created owner: owner@acme.com
  Creating roles...
    Created role: Owner
    Created role: Admin
    Created role: Manager
    Created role: Cashier
    Created role: Viewer
  Created store: Main Store
  Created user: admin@demo.com (Admin)
  Created user: manager@demo.com (Manager)
  Created user: cashier@demo.com (Cashier)
  Created user: viewer@demo.com (Viewer)

==================================================
Demo data seeded successfully!
==================================================
```

---

## User Commands

### `flask users create-owner`

Bootstrap command for initial system setup. Creates the first tenant and owner user.

```bash
flask users create-owner
```

**Interactive prompts:**
- Owner email
- Full name
- Password (hidden, with confirmation)
- Tenant/Company name

**What it creates:**
- 1 Tenant (active status)
- 1 Owner user
- 5 Default roles with permissions
- Owner role assigned to user

### `flask users create <email>`

Create a new user in an existing tenant.

```bash
# Basic usage (prompts for name and password)
flask users create newuser@company.com --tenant acme-corp

# With all options
flask users create newuser@company.com \
  --tenant acme-corp \
  --name "John Doe" \
  --password "secure123" \
  --role Manager
```

**Options:**
| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--tenant` | `-t` | Yes | Tenant slug |
| `--name` | `-n` | Prompted | Full name |
| `--password` | `-p` | Prompted | Password |
| `--role` | `-r` | No | Role to assign |

### `flask users list`

List users in the system.

```bash
# List all users
flask users list

# List users in specific tenant
flask users list --tenant acme-corp
```

Output:
```
Users in tenant 'Acme Corp':
------------------------------------------------------------
Email                          Name                 Active
------------------------------------------------------------
owner@acme.com                 John Owner           Yes
admin@acme.com                 Jane Admin           Yes
------------------------------------------------------------
Total: 2 users
```

### `flask users assign-role <email> <role>`

Assign a role to a user.

```bash
# Tenant-wide role
flask users assign-role user@company.com Manager --tenant acme-corp

# Store-specific role
flask users assign-role user@company.com Cashier \
  --tenant acme-corp \
  --store <store-uuid>
```

### `flask users revoke-role <email> <role>`

Remove a role from a user.

```bash
flask users revoke-role user@company.com Manager --tenant acme-corp
```

### `flask users activate <email>`

Activate a deactivated user account.

```bash
flask users activate user@company.com
```

### `flask users deactivate <email>`

Deactivate a user account. User will not be able to log in.

```bash
# With confirmation prompt
flask users deactivate user@company.com

# Skip confirmation
flask users deactivate user@company.com --confirm
```

---

## Common Workflows

### Initial System Setup (Production)

```bash
# 1. Run migrations
flask db upgrade

# 2. Create first owner
flask users create-owner
# Follow prompts...

# 3. (Optional) Create additional users
flask users create admin@company.com -t my-company -r Admin
```

### Development Setup

```bash
# 1. Run migrations
flask db upgrade

# 2. Seed demo data
flask seed demo

# 3. Start server
flask run
```

### Reset Everything (Development Only)

```bash
# WARNING: Destroys all data
flask db-commands reset
flask db upgrade
flask seed demo
```

### Add New Tenant

```bash
# Use create-owner to create a new tenant with its first user
flask users create-owner
# Enter new tenant details...
```

---

## Default Roles and Permissions

The system includes 5 default roles:

| Role | Description | Permission Count |
|------|-------------|------------------|
| **Owner** | Full access to everything | 48 (all) |
| **Admin** | User, store, role, and settings management | 22 |
| **Manager** | Store operations, products, orders, invoices | 21 |
| **Cashier** | POS operations - orders and payments | 7 |
| **Viewer** | Read-only access to data | 7 |

These roles are created automatically when:
- Running `flask users create-owner`
- Running `flask seed demo`
- Running `flask seed roles <tenant>`

---

## File Structure

```
app/cli/
├── __init__.py          # CLI initialization
├── db_commands.py       # Database commands
├── seed_commands.py     # Seeding commands
└── user_commands.py     # User management commands
```

Commands are registered in `app/__init__.py` via `init_cli(app)`.
