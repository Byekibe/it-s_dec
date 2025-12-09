"""
User management CLI commands.

Usage:
    flask users create-owner           # Create first owner (bootstrap)
    flask users create <email> <tenant> # Create user in a tenant
    flask users list                   # List all users
    flask users list --tenant <slug>   # List users in a tenant
    flask users assign-role <email> <role> --tenant <slug>
"""
import click
from datetime import datetime

from app.extensions import db
from app.core.constants import DEFAULT_ROLES


def register_user_commands(app):
    """Register user-related CLI commands."""

    @app.cli.group()
    def users():
        """User management commands."""
        pass

    @users.command('create-owner')
    @click.option('--email', prompt='Owner email', help='Email for the owner')
    @click.option('--name', prompt='Full name', help='Full name of the owner')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
    @click.option('--tenant-name', prompt='Tenant/Company name', help='Name of the tenant/company')
    def create_owner(email, name, password, tenant_name):
        """Create the first owner user and tenant (bootstrap).

        This is used for initial system setup when no users exist.
        Creates a tenant, owner user, default roles, and assigns Owner role.
        """
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser, TenantStatus
        from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            click.echo(f"Error: User with email '{email}' already exists.", err=True)
            raise SystemExit(1)

        # Generate tenant slug
        tenant_slug = tenant_name.lower().replace(' ', '-').replace('_', '-')
        # Remove non-alphanumeric characters except hyphens
        tenant_slug = ''.join(c for c in tenant_slug if c.isalnum() or c == '-')

        if Tenant.query.filter_by(slug=tenant_slug).first():
            click.echo(f"Error: Tenant with slug '{tenant_slug}' already exists.", err=True)
            raise SystemExit(1)

        # Create tenant
        tenant = Tenant(
            name=tenant_name,
            slug=tenant_slug,
            status=TenantStatus.ACTIVE  # First tenant is active immediately
        )
        db.session.add(tenant)
        db.session.flush()

        # Create user
        user = User(
            email=email,
            full_name=name,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Link user to tenant
        tenant_user = TenantUser(
            user_id=user.id,
            tenant_id=tenant.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user)

        # Create default roles for the tenant
        owner_role = None
        for role_name, role_data in DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_data['description'],
                is_system_role=role_data['is_system_role'],
                created_by=user.id
            )
            db.session.add(role)
            db.session.flush()

            if role_name == 'Owner':
                owner_role = role

            # Assign permissions to role
            for perm_name in role_data['permissions']:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    db.session.add(role_perm)

        # Assign Owner role to user
        user_role = UserRole(
            user_id=user.id,
            role_id=owner_role.id,
            tenant_id=tenant.id,
            assigned_at=datetime.utcnow()
        )
        db.session.add(user_role)

        db.session.commit()

        click.echo("\n" + "=" * 50)
        click.echo("Owner created successfully!")
        click.echo("=" * 50)
        click.echo(f"Tenant: {tenant.name} ({tenant.slug})")
        click.echo(f"Owner:  {user.email}")
        click.echo(f"Role:   Owner (all permissions)")
        click.echo("\nDefault roles created: Owner, Admin, Manager, Cashier, Viewer")

    @users.command('create')
    @click.argument('email')
    @click.option('--tenant', '-t', required=True, help='Tenant slug')
    @click.option('--name', '-n', prompt='Full name', help='Full name')
    @click.option('--password', '-p', prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option('--role', '-r', default=None, help='Role to assign (e.g., Admin, Manager)')
    def create_user(email, tenant, name, password, role):
        """Create a new user in a tenant.

        EMAIL: Email address for the new user
        """
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser
        from app.blueprints.rbac.models import Role, UserRole

        # Check if email exists
        if User.query.filter_by(email=email).first():
            click.echo(f"Error: User with email '{email}' already exists.", err=True)
            raise SystemExit(1)

        # Find tenant
        tenant_obj = Tenant.query.filter_by(slug=tenant).first()
        if not tenant_obj:
            click.echo(f"Error: Tenant '{tenant}' not found.", err=True)
            raise SystemExit(1)

        # Create user
        user = User(
            email=email,
            full_name=name,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Link to tenant
        tenant_user = TenantUser(
            user_id=user.id,
            tenant_id=tenant_obj.id,
            joined_at=datetime.utcnow()
        )
        db.session.add(tenant_user)

        # Assign role if specified
        if role:
            role_obj = Role.query.filter_by(
                tenant_id=tenant_obj.id,
                name=role
            ).first()
            if not role_obj:
                click.echo(f"Warning: Role '{role}' not found in tenant. User created without role.")
            else:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role_obj.id,
                    tenant_id=tenant_obj.id,
                    assigned_at=datetime.utcnow()
                )
                db.session.add(user_role)

        db.session.commit()

        click.echo(f"User created: {email}")
        if role:
            click.echo(f"Role assigned: {role}")

    @users.command('list')
    @click.option('--tenant', '-t', default=None, help='Filter by tenant slug')
    def list_users(tenant):
        """List all users, optionally filtered by tenant."""
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser

        if tenant:
            tenant_obj = Tenant.query.filter_by(slug=tenant).first()
            if not tenant_obj:
                click.echo(f"Error: Tenant '{tenant}' not found.", err=True)
                raise SystemExit(1)

            # Get users in this tenant
            users = db.session.query(User).join(
                TenantUser, TenantUser.user_id == User.id
            ).filter(
                TenantUser.tenant_id == tenant_obj.id
            ).all()

            click.echo(f"\nUsers in tenant '{tenant_obj.name}':")
        else:
            users = User.query.all()
            click.echo("\nAll users:")

        if not users:
            click.echo("  No users found.")
            return

        click.echo("-" * 60)
        click.echo(f"{'Email':<30} {'Name':<20} {'Active':<8}")
        click.echo("-" * 60)
        for user in users:
            status = "Yes" if user.is_active else "No"
            click.echo(f"{user.email:<30} {user.full_name:<20} {status:<8}")
        click.echo("-" * 60)
        click.echo(f"Total: {len(users)} users")

    @users.command('assign-role')
    @click.argument('email')
    @click.argument('role_name')
    @click.option('--tenant', '-t', required=True, help='Tenant slug')
    @click.option('--store', '-s', default=None, help='Store ID for store-specific role')
    def assign_role(email, role_name, tenant, store):
        """Assign a role to a user.

        EMAIL: User's email address
        ROLE_NAME: Name of the role to assign (e.g., Admin, Manager)
        """
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser
        from app.blueprints.stores.models import Store
        from app.blueprints.rbac.models import Role, UserRole

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"Error: User '{email}' not found.", err=True)
            raise SystemExit(1)

        # Find tenant
        tenant_obj = Tenant.query.filter_by(slug=tenant).first()
        if not tenant_obj:
            click.echo(f"Error: Tenant '{tenant}' not found.", err=True)
            raise SystemExit(1)

        # Check user is in tenant
        tenant_user = TenantUser.query.filter_by(
            user_id=user.id,
            tenant_id=tenant_obj.id
        ).first()
        if not tenant_user:
            click.echo(f"Error: User '{email}' is not a member of tenant '{tenant}'.", err=True)
            raise SystemExit(1)

        # Find role
        role = Role.query.filter_by(
            tenant_id=tenant_obj.id,
            name=role_name
        ).first()
        if not role:
            click.echo(f"Error: Role '{role_name}' not found in tenant.", err=True)
            raise SystemExit(1)

        # Handle store-specific role
        store_id = None
        if store:
            store_obj = Store.query.filter_by(id=store, tenant_id=tenant_obj.id).first()
            if not store_obj:
                click.echo(f"Error: Store '{store}' not found.", err=True)
                raise SystemExit(1)
            store_id = store_obj.id

        # Check if already assigned
        existing = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant_obj.id,
            store_id=store_id
        ).first()
        if existing:
            click.echo(f"User already has role '{role_name}'.")
            return

        # Assign role
        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant_obj.id,
            store_id=store_id,
            assigned_at=datetime.utcnow()
        )
        db.session.add(user_role)
        db.session.commit()

        if store_id:
            click.echo(f"Role '{role_name}' assigned to {email} for store {store}")
        else:
            click.echo(f"Role '{role_name}' assigned to {email} (tenant-wide)")

    @users.command('revoke-role')
    @click.argument('email')
    @click.argument('role_name')
    @click.option('--tenant', '-t', required=True, help='Tenant slug')
    def revoke_role(email, role_name, tenant):
        """Revoke a role from a user.

        EMAIL: User's email address
        ROLE_NAME: Name of the role to revoke
        """
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant
        from app.blueprints.rbac.models import Role, UserRole

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"Error: User '{email}' not found.", err=True)
            raise SystemExit(1)

        # Find tenant
        tenant_obj = Tenant.query.filter_by(slug=tenant).first()
        if not tenant_obj:
            click.echo(f"Error: Tenant '{tenant}' not found.", err=True)
            raise SystemExit(1)

        # Find role
        role = Role.query.filter_by(
            tenant_id=tenant_obj.id,
            name=role_name
        ).first()
        if not role:
            click.echo(f"Error: Role '{role_name}' not found in tenant.", err=True)
            raise SystemExit(1)

        # Find and delete assignment
        user_role = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant_obj.id
        ).first()
        if not user_role:
            click.echo(f"User does not have role '{role_name}'.")
            return

        db.session.delete(user_role)
        db.session.commit()

        click.echo(f"Role '{role_name}' revoked from {email}")

    @users.command('deactivate')
    @click.argument('email')
    @click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
    def deactivate_user(email, confirm):
        """Deactivate a user account.

        EMAIL: User's email address
        """
        from app.blueprints.users.models import User

        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"Error: User '{email}' not found.", err=True)
            raise SystemExit(1)

        if not user.is_active:
            click.echo(f"User '{email}' is already deactivated.")
            return

        if not confirm:
            if not click.confirm(f"Are you sure you want to deactivate user '{email}'?"):
                click.echo("Cancelled.")
                return

        user.is_active = False
        db.session.commit()
        click.echo(f"User '{email}' has been deactivated.")

    @users.command('activate')
    @click.argument('email')
    def activate_user(email):
        """Activate a user account.

        EMAIL: User's email address
        """
        from app.blueprints.users.models import User

        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"Error: User '{email}' not found.", err=True)
            raise SystemExit(1)

        if user.is_active:
            click.echo(f"User '{email}' is already active.")
            return

        user.is_active = True
        db.session.commit()
        click.echo(f"User '{email}' has been activated.")
