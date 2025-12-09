"""
Seed commands for populating the database with initial data.

Usage:
    flask seed permissions          # Seed all permissions
    flask seed roles <tenant_slug>  # Seed default roles for a tenant
    flask seed demo                 # Seed demo data for testing
"""
import click
from datetime import datetime, timedelta

from app.extensions import db
from app.core.constants import ALL_PERMISSIONS, DEFAULT_ROLES


def register_seed_commands(app):
    """Register seed-related CLI commands."""

    @app.cli.group()
    def seed():
        """Seed database with initial data."""
        pass

    @seed.command('permissions')
    def seed_permissions():
        """Seed all permissions into the database.

        This is also done via migration, but can be run manually if needed.
        Existing permissions are skipped (upsert behavior).
        """
        from app.blueprints.rbac.models import Permission

        created = 0
        skipped = 0

        for perm_data in ALL_PERMISSIONS:
            existing = Permission.query.filter_by(name=perm_data['name']).first()
            if existing:
                skipped += 1
                continue

            permission = Permission(
                name=perm_data['name'],
                resource=perm_data['resource'],
                action=perm_data['action'],
                description=perm_data['description']
            )
            db.session.add(permission)
            created += 1

        db.session.commit()
        click.echo(f"Permissions seeded: {created} created, {skipped} skipped (already exist)")

    @seed.command('roles')
    @click.argument('tenant_slug')
    def seed_roles(tenant_slug):
        """Seed default roles for a tenant.

        Creates Owner, Admin, Manager, Cashier, and Viewer roles
        with their associated permissions.

        TENANT_SLUG: The slug of the tenant to seed roles for.
        """
        from app.blueprints.tenants.models import Tenant
        from app.blueprints.rbac.models import Role, Permission, RolePermission

        # Find the tenant
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            click.echo(f"Error: Tenant with slug '{tenant_slug}' not found.", err=True)
            raise SystemExit(1)

        created_roles = 0
        skipped_roles = 0

        for role_name, role_data in DEFAULT_ROLES.items():
            # Check if role already exists for this tenant
            existing = Role.query.filter_by(
                tenant_id=tenant.id,
                name=role_name
            ).first()

            if existing:
                skipped_roles += 1
                click.echo(f"  Skipped: {role_name} (already exists)")
                continue

            # Create the role
            role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_data['description'],
                is_system_role=role_data['is_system_role']
            )
            db.session.add(role)
            db.session.flush()  # Get the role ID

            # Assign permissions to the role
            perm_count = 0
            for perm_name in role_data['permissions']:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    db.session.add(role_perm)
                    perm_count += 1

            created_roles += 1
            click.echo(f"  Created: {role_name} ({perm_count} permissions)")

        db.session.commit()
        click.echo(f"\nRoles seeded for tenant '{tenant.name}': {created_roles} created, {skipped_roles} skipped")

    @seed.command('demo')
    @click.option('--tenant-name', default='Demo Company', help='Name for the demo tenant')
    @click.option('--owner-email', default='owner@demo.com', help='Email for the owner user')
    @click.option('--password', default='demo1234', help='Password for demo users')
    def seed_demo(tenant_name, owner_email, password):
        """Seed demo data for testing and development.

        Creates:
        - A demo tenant with trial status
        - An owner user with all permissions
        - Default roles (Owner, Admin, Manager, Cashier, Viewer)
        - A sample store
        - Additional demo users with different roles
        """
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
        from app.blueprints.stores.models import Store, StoreUser
        from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission

        click.echo("Seeding demo data...")

        # Check if owner email already exists
        existing_user = User.query.filter_by(email=owner_email).first()
        if existing_user:
            click.echo(f"Error: User with email '{owner_email}' already exists.", err=True)
            raise SystemExit(1)

        # Create demo tenant
        tenant_slug = tenant_name.lower().replace(' ', '-')
        existing_tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if existing_tenant:
            click.echo(f"Error: Tenant with slug '{tenant_slug}' already exists.", err=True)
            raise SystemExit(1)

        tenant = Tenant(
            name=tenant_name,
            slug=tenant_slug,
            status=TenantStatus.TRIAL,
            trial_ends_at=datetime.utcnow() + timedelta(days=14)
        )
        db.session.add(tenant)
        db.session.flush()
        click.echo(f"  Created tenant: {tenant.name} ({tenant.slug})")

        # Create owner user
        owner = User(
            email=owner_email,
            full_name='Demo Owner',
            is_active=True
        )
        owner.set_password(password)
        db.session.add(owner)
        db.session.flush()
        click.echo(f"  Created owner: {owner.email}")

        # Link owner to tenant
        tenant_user = TenantUser(
            user_id=owner.id,
            tenant_id=tenant.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user)

        # Create default roles
        click.echo("  Creating roles...")
        roles = {}
        for role_name, role_data in DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_data['description'],
                is_system_role=role_data['is_system_role'],
                created_by=owner.id
            )
            db.session.add(role)
            db.session.flush()
            roles[role_name] = role

            # Assign permissions
            for perm_name in role_data['permissions']:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    db.session.add(role_perm)

            click.echo(f"    Created role: {role_name}")

        # Assign Owner role to owner user
        owner_role_assignment = UserRole(
            user_id=owner.id,
            role_id=roles['Owner'].id,
            tenant_id=tenant.id,
            assigned_at=datetime.utcnow()
        )
        db.session.add(owner_role_assignment)

        # Create a demo store
        store = Store(
            tenant_id=tenant.id,
            name='Main Store',
            address='123 Demo Street',
            phone='+1234567890',
            email='store@demo.com',
            is_active=True,
            created_by=owner.id
        )
        db.session.add(store)
        db.session.flush()
        click.echo(f"  Created store: {store.name}")

        # Assign owner to store
        store_user = StoreUser(
            user_id=owner.id,
            store_id=store.id,
            tenant_id=tenant.id,
            assigned_at=datetime.utcnow(),
            assigned_by=owner.id
        )
        db.session.add(store_user)

        # Create additional demo users
        demo_users = [
            ('admin@demo.com', 'Demo Admin', 'Admin'),
            ('manager@demo.com', 'Demo Manager', 'Manager'),
            ('cashier@demo.com', 'Demo Cashier', 'Cashier'),
            ('viewer@demo.com', 'Demo Viewer', 'Viewer'),
        ]

        for email, name, role_name in demo_users:
            user = User(email=email, full_name=name, is_active=True)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            # Link to tenant
            tu = TenantUser(
                user_id=user.id,
                tenant_id=tenant.id,
                joined_at=datetime.utcnow(),
                invited_by=owner.id
            )
            db.session.add(tu)

            # Assign role
            ur = UserRole(
                user_id=user.id,
                role_id=roles[role_name].id,
                tenant_id=tenant.id,
                assigned_at=datetime.utcnow(),
                assigned_by=owner.id
            )
            db.session.add(ur)

            # Assign to store
            su = StoreUser(
                user_id=user.id,
                store_id=store.id,
                tenant_id=tenant.id,
                assigned_at=datetime.utcnow(),
                assigned_by=owner.id
            )
            db.session.add(su)

            click.echo(f"  Created user: {email} ({role_name})")

        db.session.commit()

        click.echo("\n" + "=" * 50)
        click.echo("Demo data seeded successfully!")
        click.echo("=" * 50)
        click.echo(f"\nTenant: {tenant.name} ({tenant.slug})")
        click.echo(f"Owner:  {owner_email} / {password}")
        click.echo(f"Store:  {store.name}")
        click.echo("\nDemo users (all use same password):")
        for email, name, role_name in demo_users:
            click.echo(f"  - {email} ({role_name})")
