"""Patient ORM model.

Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from datetime import datetime
from backend import db


class Patient(db.Model):
    """Clinical patient record.

    Stores demographic context associated with reconciliation and data
    quality evaluation requests.  PII is intentionally minimal — age
    and conditions only.  Full identifiers are excluded per HIPAA
    considerations documented in design.md.

    Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer"
    """

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer, nullable=True)
    # Stored as JSON array of strings, e.g. ["Type 2 Diabetes", "Hypertension"]
    conditions = db.Column(db.JSON, nullable=True, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    # Medications are owned by the patient — cascade delete is appropriate.
    medications = db.relationship(
        "Medication", back_populates="patient", cascade="all, delete-orphan"
    )
    # Result rows use SET NULL on the FK (not CASCADE) so clinical audit history
    # is preserved when a patient record is deleted.  ORM cascade must NOT include
    # "delete" or "delete-orphan" here or SQLAlchemy will delete the rows before
    # the DB-level SET NULL fires, destroying the audit trail.
    # Governing: design.md HIPAA requirement "audit trails must be maintained"
    reconciliation_results = db.relationship(
        "ReconciliationResult", back_populates="patient"
    )
    data_quality_results = db.relationship(
        "DataQualityResult", back_populates="patient"
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} age={self.age}>"
