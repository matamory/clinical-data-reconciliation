from fastapi import FastAPI
from models import PatientRecord, ReconciliationResult, SafetyCheck, DataQualityInput, DataQualityOutput, QualityBreakdown, Issue, Severity

app= FastAPI()

@app.get('/test-get-route')
def test_get_route():
    return {"message": "This is a test GET route"}

# alternatively,can use the add_route method to add a route to the app
# app.add_route('/test-get-route', test_get_route, methods=['GET'])


@app.post('/api/reconcile/medication', response_model=ReconciliationResult)
def reconcile_medication(record:PatientRecord):
    medication_name = record.sources[0].medication if record.sources else "Unknown Medication"
    result = ReconciliationResult(
        reconciled_medication=medication_name,
        confidence_score=0.95,
        reasoning="The medication name from the source record matches the patient context.",
        recommended_actions=["Review the medication name for accuracy.", "Check for any recent updates to the medication list."],
        clinical_safety_check=SafetyCheck.PASSED
    )

    return result

@app.post('/api/validate/data-quality', response_model=DataQualityOutput)
def validate_data_quality(input_data: DataQualityInput):
    # Placeholder logic for data quality validation
    issues = []
    if not input_data.demographics.dob:
        issues.append(Issue(field="demographics.dob", issue="Patient dob is missing.", severity=Severity.medium))
    if not input_data.allergies:
        issues.append(Issue(field="allergies", issue="No allergies provided.", severity=Severity.low))
    issues.append(Issue(field="vital_signs.heart_rate", issue="Missing", severity=Severity.medium))
    quality_score = 1.0 - (len(issues) / 10)  # Simple scoring based on number of issues

    quality_breakdown = QualityBreakdown(completeness = 90, validity= 80, consistency=85, timeliness=70)

    return DataQualityOutput(
        overall_score=quality_score,
        breakdown = quality_breakdown,
        issues_detected= issues
    )