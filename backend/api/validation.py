"""Validation blueprint — POST /api/validate/data-quality.

Route handlers are implemented in issue #13 (Flask API Routes & OpenAPI Docs).
Governing: SPEC-0001 REQ "Flask Application Factory", SPEC-0001 REQ "API Endpoint Compatibility", ADR-0001
"""

from flask import Blueprint

validation_bp = Blueprint("validation", __name__)

# Route: POST /data-quality
# Registered with url_prefix="/api/validate" in create_app().
# Full implementation in story #13.
