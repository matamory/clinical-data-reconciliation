"""Pydantic schemas for reconciliation and data-quality workflows.

These models define request and response contracts for medication
reconciliation and clinical data-quality validation.
"""

from pydantic import BaseModel, ConfigDict, model_validator, Field
from typing import List, Optional
from datetime import date
from enum import Enum


#JSON schema for the input data to the reconciliation engine
class LabValue(BaseModel):
    """Represent one lab observation in a clinician-friendly format.

    This model supports either a numeric measurement (for values like
    creatinine or glucose) or a text interpretation (for values like
    "positive" or "trace"). Exactly one representation must be present.
    """

    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    unit: Optional[str] = None

    # Ensure that exactly one of numeric_value or text_value is provided after field validation
    @model_validator(mode='after')
    def validate_single_lab(self):
        """Ensure the lab value uses a single representation."""
        if (self.numeric_value is None) == (self.text_value is None):
            raise ValueError("LabValue must have exactly one of numeric_value or text_value.")
        return self

class Lab(BaseModel):
    """Store a normalized lab entry for reconciliation context."""

    name: str
    value: LabValue

class PatientContext(BaseModel):
    """Capture patient factors that influence medication decisions.

    Age, active conditions, and recent labs provide the minimum clinical
    context needed by reconciliation logic and LLM safety reasoning.
    """

    age : int
    conditions: List[str] = Field(default_factory=list)
    recent_labs: List[Lab] = Field(default_factory=list)

class SourceReliability(str, Enum):
    """Rank trust in medication sources for weighted scoring.

    Reliability is used with recency and cross-source agreement to compute
    confidence in the final reconciled medication recommendation.
    """

    low = 'low'
    medium = 'medium'
    high = 'high'

class SourceRecord(BaseModel):
    """Represent one system's medication record for the same patient.

    Each source contributes medication, freshness metadata, and reliability
    so the reconciliation engine can compare conflicting records safely.
    """

    system: str
    medication: str
    last_filled: Optional[date] = None
    last_updated: Optional[date] = None
    source_reliability: SourceReliability

class PatientRecord(BaseModel):
    """Define the reconciliation request payload.

    This object combines patient-level context with source-specific medication
    records, matching the multi-source reconciliation workflow.
    """

    patient_context: PatientContext
    sources: List[SourceRecord] = Field(default_factory=list)

#JSON schema for the output data from the reconciliation engine

class SafetyCheck(str, Enum):
    """Enumerate medication safety outcomes from clinical review.

    Outcomes distinguish safe recommendations from failures and cases that
    require human review before clinical use.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class ReconciliationResult(BaseModel):
    """Return the final reconciliation decision and its rationale.

    Includes selected medication, confidence score, reasoning, follow-up
    actions, and a safety status suitable for downstream UI and API clients.
    """

    reconciled_medication: str
    confidence_score: float
    reasoning: str
    recommended_actions: List[str] = Field(default_factory=list)
    clinical_safety_check: SafetyCheck

#JSON schema for the input data to the validation engine

class PatientDemographics(BaseModel):
    """Store core demographic data used during quality validation."""

    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None

class Vitals(BaseModel):
    """Capture optional vital signs used for validity checks.

    These values are inspected for plausible ranges and formatting as part of
    the data-quality scoring pipeline.
    """

    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None

    #model_config = ConfigDict(extra="allow")  # Allow extra fields not defined in the model
class DataQualityInput(BaseModel):
    """Define the input evaluated by data-quality dimensions.

    The validator scores this payload across completeness, validity,
    consistency, and timeliness, then reports issues by severity.
    """

    demographics: PatientDemographics
    medications: List[str] = Field(default_factory=list)
    allergies : List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    vital_signs: Optional[Vitals] = None
    last_updated: Optional[date] = None


#JSON schema for the output data from the validation engine

class QualityBreakdown(BaseModel):
    """Store per-dimension quality scores on a 0 to 100 scale.

    Dimensions align with the assessment rubric: completeness, validity,
    consistency, and timeliness.
    """

    completeness: float = Field(ge=0.0, le=100)
    validity: float = Field(ge=0.0, le=100)
    consistency: float = Field(ge=0.0, le=100)
    timeliness: float = Field(ge=0.0, le=100)

class Severity(str, Enum):
    """Classify issue impact for triage and remediation priority."""

    low = "low"
    medium = "medium"
    high = "high"    

class Issue(BaseModel):
    """Describe one detected quality problem in a specific field."""

    field: str
    issue: str
    severity: Severity

class DataQualityOutput(BaseModel):
    """Return aggregate and detailed data-quality assessment results.

    Includes overall score, dimension-level breakdown, and discrete issues for
    transparent auditing and action planning.
    """

    overall_score: float = Field(ge=0.0, le=100)
    breakdown: QualityBreakdown
    issues_detected: List[Issue] = Field(default_factory=list)