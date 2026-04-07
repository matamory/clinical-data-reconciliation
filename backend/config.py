"""Flask configuration classes for the Clinical Data Reconciliation Engine.

Governing: SPEC-0001 REQ "Environment Variable Configuration", ADR-0001
"""

import os


class Config:
    """Base configuration — reads all settings from environment variables."""

    # LLM integration (absent → heuristic fallback, per SPEC-0002)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database — defaults to SQLite for local development
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///cdre.db")
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Server
    DEBUG: bool = False
    HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BACKEND_PORT", "5000"))

    # OpenAPI / flask-smorest (Governing: SPEC-0001 REQ "OpenAPI Documentation")
    API_TITLE: str = "Clinical Data Reconciliation Engine"
    API_VERSION: str = "v1"
    OPENAPI_VERSION: str = "3.0.3"
    OPENAPI_URL_PREFIX: str = "/"
    OPENAPI_SWAGGER_UI_PATH: str = "/docs"
    OPENAPI_SWAGGER_UI_URL: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"


class DevelopmentConfig(Config):
    DEBUG: bool = os.getenv("BACKEND_DEBUG", "False").lower() == "true"


class TestingConfig(Config):
    TESTING: bool = True
    # In-memory SQLite for fast, isolated test runs
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG: bool = False


# Registry used by create_app(config_name)
config: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    # Short aliases
    "dev": DevelopmentConfig,
    "test": TestingConfig,
    "prod": ProductionConfig,
    "default": DevelopmentConfig,
}
