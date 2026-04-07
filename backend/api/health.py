"""Health blueprint — GET / and GET /health.

Governing: SPEC-0001 REQ "Flask Application Factory", SPEC-0001 REQ "API Endpoint Compatibility", ADR-0001
"""

from flask_smorest import Blueprint

health_bp = Blueprint("health", __name__, description="Health checks")


@health_bp.get("/")
def root():
    """Root endpoint — basic connectivity check."""
    return {
        "status": "healthy",
        "service": "Clinical Data Reconciliation Engine",
        "version": "1.0.0",
    }


@health_bp.get("/health")
def health_check():
    """API health check endpoint."""
    return {"status": "healthy"}
