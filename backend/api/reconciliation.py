"""Reconciliation blueprint — POST /api/reconcile/medication.

Route handlers are implemented in issue #13 (Flask API Routes & OpenAPI Docs).
Governing: SPEC-0001 REQ "Flask Application Factory", SPEC-0001 REQ "API Endpoint Compatibility", ADR-0001
"""

from flask import Blueprint

reconciliation_bp = Blueprint("reconciliation", __name__)

# Route: POST /medication
# Registered with url_prefix="/api/reconcile" in create_app().
# Full implementation in story #13.
