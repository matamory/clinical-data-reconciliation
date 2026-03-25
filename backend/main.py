from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    PatientRecord, ReconciliationResult, SafetyCheck, DataQualityInput, 
    DataQualityOutput, QualityBreakdown, Issue, Severity
)
from reconcilation_service.reconcile_meds import MedicationReconciliation
from validation_service.data_validator import DataValidator

app = FastAPI(
    title="Clinical Data Reconciliation Engine",
    description="AI-powered medication reconciliation and data quality validation",
    version="1.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
reconciliation_service = MedicationReconciliation()
validation_service = DataValidator()


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Clinical Data Reconciliation Engine",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """API health check."""
    return {"status": "healthy"}


@app.post('/api/reconcile/medication', response_model=ReconciliationResult)
def reconcile_medication(record: PatientRecord) -> ReconciliationResult:
    """
    Reconcile medication records from multiple sources.
    
    Uses hybrid scoring combining:
    - Deterministic scoring (reliability, recency, agreement)
    - LLM-based reasoning for clinical context
    
    Returns:
    - Reconciled medication with confidence score
    - Clinical safety check
    - Recommended actions
    """
    try:
        # Convert Pydantic models to dicts for service processing
        patient_context = record.patient_context.model_dump() if hasattr(record.patient_context, 'model_dump') else record.patient_context.__dict__
        sources = []
        
        for source in record.sources:
            source_dict = source.model_dump() if hasattr(source, 'model_dump') else source.__dict__
            # Convert dates to ISO format strings for JSON compatibility
            if 'last_updated' in source_dict and source_dict['last_updated']:
                source_dict['last_updated'] = source_dict['last_updated'].isoformat()
            if 'last_filled' in source_dict and source_dict['last_filled']:
                source_dict['last_filled'] = source_dict['last_filled'].isoformat()
            sources.append(source_dict)
        
        # Build patient record dict
        patient_record_dict = {
            "patient_context": patient_context,
            "sources": sources
        }
        
        # Perform reconciliation
        result = reconciliation_service.reconcile_medication(patient_record_dict)
        
        # Map safety check string to enum
        safety_map = {
            "PASSED": SafetyCheck.PASSED,
            "FAILED": SafetyCheck.FAILED,
            "REVIEW_REQUIRED": SafetyCheck.REVIEW_REQUIRED
        }
        
        # Create response
        return ReconciliationResult(
            reconciled_medication=result.get("reconciled_medication") or "Unknown",
            confidence_score=result.get("confidence_score", 0.0),
            reasoning=result.get("reasoning", ""),
            recommended_actions=result.get("recommended_actions", []),
            clinical_safety_check=safety_map.get(
                result.get("clinical_safety_check", "REVIEW_REQUIRED"),
                SafetyCheck.REVIEW_REQUIRED
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Reconciliation failed: {str(e)}"
        )


@app.post('/api/validate/data-quality', response_model=DataQualityOutput)
def validate_data_quality(input_data: DataQualityInput) -> DataQualityOutput:
    """
    Validate patient data quality across four dimensions:
    - Completeness: Are all required fields present?
    - Validity: Are values in correct format and range?
    - Consistency: Do values logically align?
    - Timeliness: Is data recent enough?
    
    Returns:
    - Overall score (0-100)
    - Score breakdown by dimension
    - List of detected issues with severity
    """
    try:
        # Convert Pydantic model to dict
        data_dict = input_data.model_dump() if hasattr(input_data, 'model_dump') else input_data.__dict__
        
        # Convert dates to ISO format for processing
        if 'last_updated' in data_dict and data_dict['last_updated']:
            data_dict['last_updated'] = data_dict['last_updated'].isoformat()
        
        # Perform validation
        validation_result = validation_service.validate_data_quality(data_dict)
        
        # Build issues list
        issues = []
        for issue in validation_result.get("issues_detected", []):
            # Handle both Issue objects and dicts
            if isinstance(issue, Issue):
                issues.append(issue)
            else:
                issues.append(Issue(
                    field=issue.get("field", "unknown"),
                    issue=issue.get("issue", ""),
                    severity=Severity(issue.get("severity", "low"))
                ))
        
        # Create response
        return DataQualityOutput(
            overall_score=int(validation_result.get("overall_score", 0)),
            breakdown=QualityBreakdown(
                completeness=int(validation_result.get("breakdown", {}).get("completeness", 0)),
                validity=int(validation_result.get("breakdown", {}).get("validity", 0)),
                consistency=int(validation_result.get("breakdown", {}).get("consistency", 0)),
                timeliness=int(validation_result.get("breakdown", {}).get("timeliness", 0))
            ),
            issues_detected=issues
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Data validation failed: {str(e)}"
        )


@app.get('/test-get-route')
def test_get_route():
    """Test GET endpoint."""
    return {"message": "This is a test GET route"}


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )
