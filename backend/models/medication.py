"""Medication ORM model.

Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from datetime import datetime
from backend import db


class Medication(db.Model):
    """Medication record sourced from a clinical system.

    One row per source-medication pair within a reconciliation request.
    Multiple Medication rows may reference the same Patient, each with
    a different `system` origin (e.g. Hospital EMR, Pharmacy System).

    Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer"
    """

    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=True
    )
    # Source system name, e.g. "Hospital EMR", "Pharmacy System"
    system = db.Column(db.String(255), nullable=False)
    # Full medication string, e.g. "Metformin 500mg twice daily"
    name = db.Column(db.String(500), nullable=False)
    last_updated = db.Column(db.Date, nullable=True)
    last_filled = db.Column(db.Date, nullable=True)
    # One of: 'high', 'medium', 'low'
    source_reliability = db.Column(db.String(10), nullable=False, default="medium")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    patient = db.relationship("Patient", back_populates="medications")

    def __repr__(self) -> str:
        return f"<Medication id={self.id} system={self.system!r} name={self.name!r}>"
