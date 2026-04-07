"""Validation blueprint — POST /api/validate/data-quality.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "API Endpoint Compatibility",
           SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001,
           SPEC-0003 REQ "API Contract", SPEC-0003 REQ "Issue Object Schema",
           SPEC-0003 REQ "ORM Persistence"
"""

from datetime import date
from flask import jsonify, make_response
from flask_smorest import Blueprint

from .. import db
from ..schemas import DataQualityInputSchema, DataQualityOutputSchema
from ..models import DataQualityResult, Patient
from ..validation_service.data_validator import DataValidator

validation_bp = Blueprint(
    "validation",
    __name__,
    description="Patient data quality validation",
)

_service = DataValidator()


@validation_bp.post("/data-quality")
@validation_bp.arguments(DataQualityInputSchema)
@validation_bp.response(200, DataQualityOutputSchema)
def validate_data_quality(args):
    """Validate patient data quality across four dimensions.

    Scores completeness, validity, consistency, and timeliness, returning
    an overall score plus a per-dimension breakdown and a list of detected issues.
    Persists each result to the database per SPEC-0001 REQ "SQLAlchemy ORM Data Layer".
    """
    try:
        result = _service.validate_data_quality(args)
        breakdown = result.get("breakdown", {})

        # Governing: SPEC-0003 REQ "Issue Object Schema" — severity MUST be plain string
        # ("high"/"medium"/"low"), never the Pydantic enum class name ("Severity.high")
        issues = [
            {
                "field": issue.get("field", "unknown") if isinstance(issue, dict) else issue.field,
                "issue": issue.get("issue", "") if isinstance(issue, dict) else issue.issue,
                "severity": issue.get("severity", "low") if isinstance(issue, dict) else (
                    issue.severity.value if hasattr(issue.severity, "value") else issue.severity
                ),
            }
            for issue in result.get("issues_detected", [])
        ]

        # Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer",
        #            SPEC-0003 REQ "ORM Persistence" — persist result with patient reference and UTC timestamp
        demographics = args.get("demographics", {})
        dob_str = demographics.get("dob")
        age = None
        if dob_str:
            try:
                dob = date.fromisoformat(dob_str)
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except (ValueError, TypeError):
                pass
        patient = Patient(
            age=age,
            conditions=args.get("conditions", []),
        )
        db.session.add(patient)
        db.session.flush()  # assigns patient.id within the transaction

        db_record = DataQualityResult(
            patient_id=patient.id,
            overall_score=float(result.get("overall_score", 0)),
            completeness=float(breakdown.get("completeness", 0)),
            validity=float(breakdown.get("validity", 0)),
            consistency=float(breakdown.get("consistency", 0)),
            timeliness=float(breakdown.get("timeliness", 0)),
            issues_detected=issues,
        )
        db.session.add(db_record)
        db.session.commit()

        # Governing: SPEC-0003 REQ "API Contract" — response MUST include overall_score
        # (int 0-100), breakdown (four dimension scores), issues_detected (array)
        return {
            "overall_score": int(db_record.overall_score),
            "breakdown": {
                "completeness": int(db_record.completeness),
                "validity": int(db_record.validity),
                "consistency": int(db_record.consistency),
                "timeliness": int(db_record.timeliness),
            },
            "issues_detected": db_record.issues_detected or [],
        }
    except Exception as exc:
        # Governing: SPEC-0003 REQ "ORM Persistence" Scenario "Rollback on failure"
        db.session.rollback()
        return make_response(
            jsonify({"detail": f"Data validation failed: {exc}"}), 400
        )
