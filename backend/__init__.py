"""Flask application factory for the Clinical Data Reconciliation Engine.

Governing: SPEC-0001 REQ "Flask Application Factory", ADR-0001
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_smorest import Api

# Extension instances — created here, bound to the app in create_app().
# This separation prevents circular imports when models import `db`.
# NOTE: The smorest Api instance is named `smorest_api` to avoid shadowing
# the `api/` subpackage when Python resolves attributes on this module.
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
smorest_api: Api = Api()


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
    # Governing: SPEC-0001 REQ "OpenAPI Documentation"
    smorest_api.init_app(app)

    # Import ORM models so Flask-Migrate (Alembic) discovers them during
    # `flask db migrate` autogenerate. Must happen inside create_app() to
    # avoid circular imports.
    # Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer"
    from . import models  # noqa: F401

    # Register one smorest blueprint per domain via Api — this enables
    # automatic OpenAPI spec generation at /docs.
    # Governing: ADR-0001 blueprint-per-domain, SPEC-0001 REQ "OpenAPI Documentation"
    from .api.health import health_bp
    from .api.reconciliation import reconciliation_bp
    from .api.validation import validation_bp

    smorest_api.register_blueprint(health_bp)
    smorest_api.register_blueprint(reconciliation_bp, url_prefix="/api/reconcile")
    smorest_api.register_blueprint(validation_bp, url_prefix="/api/validate")

    return app
