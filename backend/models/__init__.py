"""SQLAlchemy ORM models for the Clinical Data Reconciliation Engine.

Importing all models here ensures Flask-Migrate (Alembic) discovers them
during `flask db migrate` autogenerate.  The `db` instance is created in
backend/__init__.py and imported by each model module.

Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from .patient import Patient
from .medication import Medication
from .reconciliation import ReconciliationResult, DataQualityResult

__all__ = ["Patient", "Medication", "ReconciliationResult", "DataQualityResult"]
