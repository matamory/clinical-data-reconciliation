"""Health blueprint — GET /health.

Governing: SPEC-0001 REQ "Flask Application Factory", SPEC-0001 REQ "API Endpoint Compatibility", ADR-0001
"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """API health check endpoint."""
    return jsonify({"status": "healthy"})
