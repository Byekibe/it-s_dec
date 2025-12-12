from flask import Flask
from app.config import config
from dotenv import load_dotenv
from app.extensions import db, cors, migrate
from app.extensions import init_extension

load_dotenv()

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    init_extension(app)

    # Initialize Celery
    from app.core.celery import init_celery
    init_celery(app)

    # Initialize Mail
    from app.core.email import init_mail
    init_mail(app)

    # Import models for Flask-Migrate to discover them
    # This must be done after db initialization
    with app.app_context():
        from app.blueprints.users.models import User
        from app.blueprints.tenants.models import Tenant, TenantUser, TenantSettings
        from app.blueprints.stores.models import Store, StoreUser, StoreSettings
        from app.blueprints.rbac.models import Role, Permission, UserRole, RolePermission
        from app.blueprints.auth.models import BlacklistedToken, UserTokenRevocation
        from app.blueprints.subscriptions.models import Plan, Subscription

    # Initialize security middleware and error handlers
    from app.core.middleware import init_middleware
    init_middleware(app)

    # Initialize CLI commands
    from app.cli import init_cli
    init_cli(app)

    # Register API blueprints
    from app.blueprints.api.v1 import api_v1
    app.register_blueprint(api_v1)

    # Register health check blueprint (at root level, bypasses auth)
    from app.blueprints.health import health_bp
    app.register_blueprint(health_bp)

    return app