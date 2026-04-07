"""Validation blueprint — POST /api/validate/data-quality.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "API Endpoint Compatibility", ADR-0001
"""

from flask import jsonify, make_response
from flask_smorest import Blueprint

from ..schemas import DataQualityInputSchema, DataQualityOutputSchema
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
    """
    try:
        result = _service.validate_data_quality(args)
        breakdown = result.get("breakdown", {})
        return {
            "overall_score": int(result.get("overall_score", 0)),
            "breakdown": {
                "completeness": int(breakdown.get("completeness", 0)),
                "validity": int(breakdown.get("validity", 0)),
                "consistency": int(breakdown.get("consistency", 0)),
                "timeliness": int(breakdown.get("timeliness", 0)),
            },
            "issues_detected": [
                {
                    "field": issue.get("field", "unknown") if isinstance(issue, dict) else issue.field,
                    "issue": issue.get("issue", "") if isinstance(issue, dict) else issue.issue,
                    "severity": issue.get("severity", "low") if isinstance(issue, dict) else (
                        issue.severity.value if hasattr(issue.severity, "value") else issue.severity
                    ),
                }
                for issue in result.get("issues_detected", [])
            ],
        }
    except Exception as exc:
        return make_response(
            jsonify({"detail": f"Data validation failed: {exc}"}), 400
        )
