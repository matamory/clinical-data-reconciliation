from typing import Dict, List, Any, Optional
from datetime import datetime, date
from ..pydantic_models import Issue, Severity

# Governing: SPEC-0003 REQ "API Contract", SPEC-0003 REQ "Overall Score Formula",
#            SPEC-0003 REQ "Completeness Dimension", SPEC-0003 REQ "Validity Dimension",
#            SPEC-0003 REQ "Consistency Dimension", SPEC-0003 REQ "Timeliness Dimension",
#            SPEC-0003 REQ "Issue Object Schema"


class DataValidator:
    """Validates clinical data quality across multiple dimensions."""

    def __init__(self):
        self.required_fields = {
            "demographics.name": "high",
            "vital_signs": "medium"
        }

    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate patient data quality across four dimensions:
        - Completeness (0-100)
        - Validity (0-100)
        - Consistency (0-100)
        - Timeliness (0-100)

        Returns a detailed quality assessment.
        """
        issues = []

        # Check completeness
        completeness_score, completeness_issues = self._check_completeness(data)
        issues.extend(completeness_issues)

        # Check validity
        validity_score, validity_issues = self._check_validity(data)
        issues.extend(validity_issues)

        # Check consistency
        consistency_score, consistency_issues = self._check_consistency(data)
        issues.extend(consistency_issues)

        # Check timeliness
        timeliness_score, timeliness_issues = self._check_timeliness(data)
        issues.extend(timeliness_issues)

        # Governing: SPEC-0003 REQ "Overall Score Formula"
        # overall_score = (avg_dimensions × 0.30) + (completeness × 0.70), clamped to [0, 100]
        base_average = (completeness_score + validity_score + consistency_score + timeliness_score) / 4
        overall_score = (base_average * 0.3) + (completeness_score * 0.7)

        high_severity_count = 0
        for issue in issues:
            if hasattr(issue, "severity"):
                severity_value = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            elif isinstance(issue, dict):
                severity_value = issue.get("severity")
            else:
                severity_value = None

            if severity_value == "high":
                high_severity_count += 1
        
        return {
            "overall_score": overall_score,
            "breakdown": {
                "completeness": completeness_score,
                "validity": validity_score,
                "consistency": consistency_score,
                "timeliness": timeliness_score
            },
            "issues_detected": issues,
            "total_issues": len(issues),
            "high_severity_count": high_severity_count,
            "data_quality_status": self._get_quality_status(overall_score)
        }
    
    def _check_completeness(self, data: Dict[str, Any]) -> tuple:
        """
        Check for missing required fields.

        Governing: SPEC-0003 REQ "Completeness Dimension"
        Score starts at 100; each missing field subtracts a fixed penalty.
        """
        issues = []
        missing_critical = 0
        total_fields = 0
        completeness_penalty = 0
        
        # Check demographics
        demographics = data.get("demographics", {})
        if not demographics.get("name"):
            issues.append(Issue(
                field="demographics.name",
                issue="Patient name is missing",
                severity=Severity.high
            ))
            missing_critical += 1
            completeness_penalty += 10
        total_fields += 1
        
        if not demographics.get("dob"):
            issues.append(Issue(
                field="demographics.dob",
                issue="Date of birth is missing",
                severity=Severity.medium
            ))
            completeness_penalty += 6
        total_fields += 1
        
        if not demographics.get("gender"):
            issues.append(Issue(
                field="demographics.gender",
                issue="Gender is not specified",
                severity=Severity.low
            ))
            completeness_penalty += 4
        total_fields += 1
        
        # Check medications list
        medications = data.get("medications", [])
        if not medications or len(medications) == 0:
            issues.append(Issue(
                field="medications",
                issue="No medications documented",
                severity=Severity.medium
            ))
            completeness_penalty += 8
        total_fields += 1

        # Check allergies list
        allergies = data.get("allergies", [])
        if allergies is None or len(allergies) == 0:
            issues.append(Issue(
                field="allergies",
                issue="Allergy information is missing",
                severity=Severity.medium
            ))
            completeness_penalty += 15
        total_fields += 1
        
        # Check vital signs
        vitals = data.get("vital_signs")
        if not vitals:
            issues.append(Issue(
                field="vital_signs",
                issue="Vital signs data is missing",
                severity=Severity.high
            ))
            missing_critical += 1
            completeness_penalty += 15
        else:
            if not vitals.get("blood_pressure"):
                issues.append(Issue(
                    field="vital_signs.blood_pressure",
                    issue="Blood pressure reading is missing",
                    severity=Severity.medium
                ))
                completeness_penalty += 6
            if not vitals.get("heart_rate"):
                issues.append(Issue(
                    field="vital_signs.heart_rate",
                    issue="Heart rate reading is missing",
                    severity=Severity.medium
                ))
                completeness_penalty += 6
        total_fields += 1
        
        # Check conditions
        conditions = data.get("conditions", [])
        if not conditions:
            issues.append(Issue(
                field="conditions",
                issue="No medical conditions documented",
                severity=Severity.low
            ))
            completeness_penalty += 4
        total_fields += 1
        
        # Calculate score
        score = max(0, 100 - completeness_penalty)
        
        return score, issues
    
    def _check_validity(self, data: Dict[str, Any]) -> tuple:
        """
        Check for invalid data formats and values.

        Governing: SPEC-0003 REQ "Validity Dimension"
        Score starts at 100; each invalid field subtracts a fixed penalty.
        """
        issues = []
        
        # Validate DOB
        demographics = data.get("demographics", {})
        dob = demographics.get("dob")
        if dob:
            try:
                if isinstance(dob, str):
                    dob_date = datetime.fromisoformat(dob).date()
                elif isinstance(dob, date):
                    dob_date = dob
                else:
                    dob_date = None
                
                if dob_date and dob_date > datetime.now().date():
                    issues.append(Issue(
                        field="demographics.dob",
                        issue="Date of birth is in the future",
                        severity=Severity.high
                    ))
            except (ValueError, TypeError):
                issues.append(Issue(
                    field="demographics.dob",
                    issue="Date of birth format is invalid",
                    severity=Severity.medium
                ))
        
        # Validate gender
        gender = demographics.get("gender")
        if gender and gender.lower() not in ["male", "female", "other", "unknown"]:
            issues.append(Issue(
                field="demographics.gender",
                issue=f"Gender value '{gender}' is not valid",
                severity=Severity.low
            ))
        
        # Validate vital signs ranges
        vitals = data.get("vital_signs") or {}

        bp = vitals.get("blood_pressure")
        if bp:
            try:
                if not isinstance(bp, str) or "/" not in bp:
                    raise ValueError("Invalid blood pressure format")

                systolic_str, diastolic_str = bp.split("/", 1)
                systolic = int(systolic_str.strip())
                diastolic = int(diastolic_str.strip())

                if systolic < 70 or systolic > 250 or diastolic < 40 or diastolic > 150:
                    issues.append(Issue(
                        field="vital_signs.blood_pressure",
                        issue=f"Blood pressure {bp} is clinically implausible",
                        severity=Severity.medium
                    ))
                elif systolic <= diastolic:
                    issues.append(Issue(
                        field="vital_signs.blood_pressure",
                        issue=f"Blood pressure {bp} is invalid (systolic must exceed diastolic)",
                        severity=Severity.medium
                    ))
            except (ValueError, TypeError):
                issues.append(Issue(
                    field="vital_signs.blood_pressure",
                    issue=f"Blood pressure value '{bp}' format is invalid (expected 'systolic/diastolic')",
                    severity=Severity.medium
                ))
        
        hr = vitals.get("heart_rate")
        if hr is not None:
            # Accept both int and float (Marshmallow deserializes heart_rate as Float)
            if not isinstance(hr, (int, float)) or isinstance(hr, bool) or hr < 30 or hr > 200:
                issues.append(Issue(
                    field="vital_signs.heart_rate",
                    issue=f"Heart rate value {hr} is outside normal range (30-200)",
                    severity=Severity.medium
                ))
        
        temp = vitals.get("temperature")
        if temp is not None:
            if not isinstance(temp, (int, float)) or temp < 35 or temp > 42:
                issues.append(Issue(
                    field="vital_signs.temperature",
                    issue=f"Temperature {temp}°C is outside normal range (35-42°C)",
                    severity=Severity.medium
                ))
        
        # Calculate validity score using weighted penalties
        penalty = 0
        for issue in issues:
            field_name = issue.field if hasattr(issue, "field") else issue.get("field", "")
            issue_text = issue.issue.lower() if hasattr(issue, "issue") else str(issue.get("issue", "")).lower()

            if field_name == "vital_signs.blood_pressure" and "clinically implausible" in issue_text:
                penalty += 25
            elif field_name == "vital_signs.blood_pressure":
                penalty += 15
            elif field_name in {"vital_signs.heart_rate", "vital_signs.temperature"}:
                penalty += 15
            elif field_name == "demographics.dob" and "future" in issue_text:
                penalty += 20
            elif field_name == "demographics.dob":
                penalty += 12
            elif field_name == "demographics.gender":
                penalty += 8
            else:
                penalty += 10

        score = max(0, 100 - penalty)
        
        return score, issues
    
    def _check_consistency(self, data: Dict[str, Any]) -> tuple:
        """
        Check for internal data consistency.

        Governing: SPEC-0003 REQ "Consistency Dimension"
        Score starts at 100; each inconsistency subtracts 15.
        """
        issues = []
        
        demographics = data.get("demographics", {})
        conditions = data.get("conditions", [])
        medications = data.get("medications", [])
        
        # Check age consistency with DOB
        dob = demographics.get("dob")
        if dob:
            try:
                if isinstance(dob, str):
                    dob_date = datetime.fromisoformat(dob).date()
                elif isinstance(dob, date):
                    dob_date = dob
                else:
                    dob_date = None
                
                if dob_date:
                    calculated_age = (datetime.now().date() - dob_date).days // 365
                    if calculated_age < 0:
                        issues.append(Issue(
                            field="demographics.dob",
                            issue="Age cannot be negative based on DOB",
                            severity=Severity.high
                        ))
            except:
                pass
        
        # Check for empty but declared arrays
        if len(conditions) == 0:
            # Not an error, just an observation
            pass
        
        # Check medication-condition alignment
        if conditions and medications:
            # Simple heuristic: if diabetic, should have diabetes meds
            has_diabetes_condition = any("diabetes" in c.lower() for c in conditions)
            has_diabetes_med = any(
                any(term in m.lower() for term in ["metformin", "insulin", "glipizide"])
                for m in medications
            )
            if has_diabetes_condition and not has_diabetes_med:
                issues.append(Issue(
                    field="medications",
                    issue="Patient has diabetes but no diabetes medication documented",
                    severity=Severity.low
                ))
        
        # Calculate consistency score
        score = max(0, 100 - (len(issues) * 15))
        
        return score, issues
    
    def _check_timeliness(self, data: Dict[str, Any]) -> tuple:
        """
        Check how recent the data is.

        Governing: SPEC-0003 REQ "Timeliness Dimension"
        Missing last_updated defaults to score=50 (neutral, medium severity).
        """
        issues = []
        
        last_updated = data.get("last_updated")
        if not last_updated:
            issues.append(Issue(
                field="last_updated",
                issue="Last update timestamp is missing",
                severity=Severity.medium
            ))
            score = 50  # Neutral score
        else:
            try:
                if isinstance(last_updated, str):
                    update_date = datetime.fromisoformat(last_updated).date()
                elif isinstance(last_updated, date):
                    update_date = last_updated
                else:
                    update_date = None
                
                if update_date:
                    days_ago = (datetime.now().date() - update_date).days
                    
                    if days_ago < 0:
                        issues.append(Issue(
                            field="last_updated",
                            issue="Last update date is in the future",
                            severity=Severity.high
                        ))
                        score = 30
                    elif days_ago > 365:
                        issues.append(Issue(
                            field="last_updated",
                            issue=f"Data is {days_ago} days old (over 1 year)",
                            severity=Severity.high
                        ))
                        score = 20
                    elif days_ago > 90:
                        issues.append(Issue(
                            field="last_updated",
                            issue=f"Data is {days_ago} days old (over 3 months)",
                            severity=Severity.medium
                        ))
                        score = 50
                    elif days_ago > 30:
                        issues.append(Issue(
                            field="last_updated",
                            issue=f"Data is {days_ago} days old (over 1 month)",
                            severity=Severity.low
                        ))
                        score = 75
                    else:
                        score = 100  # Recent data
                else:
                    score = 50
            except:
                score = 50
        
        return score, issues
    
    def _get_quality_status(self, overall_score: float) -> str:
        """Determine overall data quality status."""
        if overall_score >= 90:
            return "EXCELLENT"
        elif overall_score >= 75:
            return "GOOD"
        elif overall_score >= 60:
            return "ACCEPTABLE"
        elif overall_score >= 40:
            return "POOR"
        else:
            return "CRITICAL"
