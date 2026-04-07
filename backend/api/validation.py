"""Validation blueprint — POST /api/validate/data-quality.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "API Endpoint Compatibility",
           SPEC-0001 REQ "SQLAlchemy ORM Data Layer", ADR-0001
"""

from flask import jsonify, make_response
from flask_smorest import Blueprint

from .. import db
from ..schemas import DataQualityInputSchema, DataQualityOutputSchema
from ..models import DataQualityResult
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

        # Governing: SPEC-0001 REQ "SQLAlchemy ORM Data Layer" — persist result with timestamp
        db_record = DataQualityResult(
            overall_score=float(result.get("overall_score", 0)),
            completeness=float(breakdown.get("completeness", 0)),
            validity=float(breakdown.get("validity", 0)),
            consistency=float(breakdown.get("consistency", 0)),
            timeliness=float(breakdown.get("timeliness", 0)),
            issues_detected=issues,
        )
        db.session.add(db_record)
        db.session.commit()

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
        db.session.rollback()
        return make_response(
            jsonify({"detail": f"Data validation failed: {exc}"}), 400
        )
