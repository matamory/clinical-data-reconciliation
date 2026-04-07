"""Reconciliation blueprint — POST /api/reconcile/medication.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "API Endpoint Compatibility",
           SPEC-0001 REQ "SQLAlchemy ORM Data Layer",
           SPEC-0002 REQ "API Contract", SPEC-0002 REQ "LLM Scoring", ADR-0001, ADR-0002
"""

from flask import jsonify, make_response
from flask_smorest import Blueprint

from .. import db
from ..schemas import PatientRecordSchema, ReconciliationResultSchema
from ..models import ReconciliationResult, Patient
from ..reconcilation_service.reconcile_meds import MedicationReconciliation

reconciliation_bp = Blueprint(
    "reconciliation",
    __name__,
    description="Medication reconciliation across multiple sources",
)

_service = MedicationReconciliation()


@reconciliation_bp.post("/medication")
@reconciliation_bp.arguments(PatientRecordSchema)
@reconciliation_bp.response(200, ReconciliationResultSchema)
def reconcile_medication(args):
    """Reconcile medication records from multiple sources.

    Uses a hybrid 60/40 deterministic + LLM scoring model (ADR-0002) to
    select the most clinically appropriate medication record and compute a
    confidence score with safety checks. Persists each result to the database
    per SPEC-0001 REQ "SQLAlchemy ORM Data Layer".
    """
    # Governing: SPEC-0001 REQ "API Endpoint Compatibility", SPEC-0002 REQ "API Contract"
    if not args.get("sources"):
        return make_response(
            jsonify({"detail": "At least one medication source is required"}), 422
        )

    try:
        result = _service.reconcile_medication(args)

        # Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer" — persist result with patient reference
        patient_context = args.get("patient_context", {})
        patient = Patient(
            age=patient_context.get("age"),
            conditions=patient_context.get("conditions", []),
        )
        db.session.add(patient)
        db.session.flush()  # assigns patient.id within the transaction

        db_record = ReconciliationResult(
            patient_id=patient.id,
            reconciled_medication=result.get("reconciled_medication") or "Unknown",
            confidence_score=result.get("confidence_score", 0.0),
            clinical_safety_check=result.get("clinical_safety_check", "REVIEW_REQUIRED"),
            reasoning=result.get("reasoning", ""),
            recommended_actions=result.get("recommended_actions", []),
        )
        db.session.add(db_record)
        db.session.commit()

        # Governing: SPEC-0002 REQ "LLM Scoring" — response MUST include model_used
        # Governing: SPEC-0002 REQ "Uncertainty Detection" — response MUST include requires_review
        return {
            "reconciled_medication": db_record.reconciled_medication,
            "confidence_score": db_record.confidence_score,
            "clinical_safety_check": db_record.clinical_safety_check,
            "reasoning": db_record.reasoning,
            "recommended_actions": db_record.recommended_actions or [],
            "model_used": result.get("model_used", "unknown"),
            "requires_review": result.get("requires_review", False),
        }
    except Exception as exc:
        db.session.rollback()
        return make_response(
            jsonify({"detail": f"Reconciliation failed: {exc}"}), 400
        )
