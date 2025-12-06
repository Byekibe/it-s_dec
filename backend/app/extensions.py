from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
cors = CORS()
migrate = Migrate()

def init_extension(app):
    db.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)