"""Flask application factory for the Clinical Data Reconciliation Engine.

Governing: SPEC-0001 REQ "Flask Application Factory", ADR-0001
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Extension instances — created here, bound to the app in create_app().
# This separation prevents circular imports when models import `db`.
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()


def create_app(config_name: str = "default") -> Flask:
    """Application factory.

    Creates and configures a Flask application instance for the given
    configuration name (development / testing / production / default).

    Governing: SPEC-0001 REQ "Flask Application Factory", ADR-0001
    """
    from .config import config as config_map

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # Allow DATABASE_URL env var to override SQLALCHEMY_DATABASE_URI directly
    if app.config.get("DATABASE_URL"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]

    # Bind extensions to this app instance
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Register one blueprint per domain (Governing: ADR-0001 blueprint-per-domain)
    from .api.health import health_bp
    from .api.reconciliation import reconciliation_bp
    from .api.validation import validation_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(reconciliation_bp, url_prefix="/api/reconcile")
    app.register_blueprint(validation_bp, url_prefix="/api/validate")

    return app
