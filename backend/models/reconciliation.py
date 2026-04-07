"""ReconciliationResult and DataQualityResult ORM models.

Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from datetime import datetime
from backend import db


class ReconciliationResult(db.Model):
    """Persisted output of a medication reconciliation request.

    Stores the winning medication, confidence score, safety check
    outcome, and recommended clinical actions with a UTC timestamp
    and optional patient reference.

    SPEC-0001 REQ "SQLAlchemy ORM Data Layer" scenario:
      WHEN the reconciliation service produces a result for a patient medication
      THEN the result MUST be saved via this model with a timestamp and
           patient reference.

    Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
    """

    __tablename__ = "reconciliation_results"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    # The reconciliation winner, e.g. "Metformin 500mg"
    reconciled_medication = db.Column(db.String(500), nullable=False)
    # 0.0–1.0 hybrid confidence score (ADR-0002: 60% det + 40% LLM)
    confidence_score = db.Column(db.Float, nullable=False)
    # One of: 'PASSED', 'FAILED', 'REVIEW_REQUIRED'
    clinical_safety_check = db.Column(db.String(20), nullable=False)
    reasoning = db.Column(db.Text, nullable=True)
    # JSON array of action strings, e.g. ["Verify with prescriber", ...]
    recommended_actions = db.Column(db.JSON, nullable=True, default=list)
    # Timestamp required by SPEC-0001 REQ "SQLAlchemy ORM Data Layer"
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    patient = db.relationship("Patient", back_populates="reconciliation_results")

    def __repr__(self) -> str:
        return (
            f"<ReconciliationResult id={self.id} "
            f"medication={self.reconciled_medication!r} "
            f"confidence={self.confidence_score:.2f}>"
        )


class DataQualityResult(db.Model):
    """Persisted output of a data quality validation request.

    Stores the four-dimension breakdown (completeness, validity,
    consistency, timeliness) plus the weighted overall score and any
    detected issues.

    Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
    """

    __tablename__ = "data_quality_results"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    # Overall quality score (0–100) per validation_service formula
    overall_score = db.Column(db.Float, nullable=False)
    # Individual dimension scores (0–100 each)
    completeness = db.Column(db.Float, nullable=False)
    validity = db.Column(db.Float, nullable=False)
    consistency = db.Column(db.Float, nullable=False)
    timeliness = db.Column(db.Float, nullable=False)
    # JSON array of issue objects: [{field, issue, severity}, ...]
    issues_detected = db.Column(db.JSON, nullable=True, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    patient = db.relationship("Patient", back_populates="data_quality_results")

    def __repr__(self) -> str:
        return (
            f"<DataQualityResult id={self.id} "
            f"overall={self.overall_score:.1f}>"
        )
