from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Register child blueprints
from app.blueprints.auth import auth_bp
from app.blueprints.users import users_bp
from app.blueprints.tenants import tenants_bp
from app.blueprints.stores import stores_bp
from app.blueprints.rbac import rbac_bp
from app.blueprints.subscriptions import subscriptions_bp

api_v1.register_blueprint(auth_bp)
api_v1.register_blueprint(users_bp)
api_v1.register_blueprint(tenants_bp)
api_v1.register_blueprint(stores_bp)
api_v1.register_blueprint(rbac_bp)
api_v1.register_blueprint(subscriptions_bp)


