"""Reconciliation blueprint — POST /api/reconcile/medication.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "API Endpoint Compatibility",
           SPEC-0002 REQ "API Contract", ADR-0001, ADR-0002
"""

from flask import jsonify, make_response
from flask_smorest import Blueprint

from ..schemas import PatientRecordSchema, ReconciliationResultSchema
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
    confidence score with safety checks.
    """
    # Governing: SPEC-0001 REQ "API Endpoint Compatibility" — return 422 for empty sources
    if not args.get("sources"):
        return make_response(
            jsonify({"detail": "At least one medication source is required"}), 422
        )

    try:
        result = _service.reconcile_medication(args)
        return {
            "reconciled_medication": result.get("reconciled_medication") or "Unknown",
            "confidence_score": result.get("confidence_score", 0.0),
            "clinical_safety_check": result.get("clinical_safety_check", "REVIEW_REQUIRED"),
            "reasoning": result.get("reasoning", ""),
            "recommended_actions": result.get("recommended_actions", []),
        }
    except Exception as exc:
        return make_response(
            jsonify({"detail": f"Reconciliation failed: {exc}"}), 400
        )
