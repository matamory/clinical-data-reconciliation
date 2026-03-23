from pydantic import BaseModel, ConfigDict, model_validator, Field
from typing import List, Optional
from datetime import date
from enum import Enum


#JSON schema for the input data to the reconciliation engine
class LabValue(BaseModel):
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    unit: Optional[str] = None

    # Ensure that exactly one of numeric_value or text_value is provided after field validation
    @model_validator(mode='after')
    def validate_single_lab(self):
        if (self.numeric_value is None) == (self.text_value is None):
            raise ValueError("LabValue must have exactly one of numeric_value or text_value.")
        return self

class Lab(BaseModel):
    name: str
    value: LabValue

class PatientContext(BaseModel):
    age : int
    conditions: List[str] = Field(default_factory=list)
    recent_labs: List[Lab] = Field(default_factory=list)

class SourceReliability(str, Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'

class SourceRecord(BaseModel):
    system: str
    medication: str
    last_filled: Optional[date] = None
    last_updated: Optional[date] = None
    source_reliability: SourceReliability

class PatientRecord(BaseModel):
    patient_context: PatientContext
    sources: List[SourceRecord] = Field(default_factory=list)

#JSON schema for the output data from the reconciliation engine

class SafetyCheck(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class ReconciliationResult(BaseModel):
    reconciled_medication: str
    confidence_score: float
    reasoning: str
    recommended_actions: List[str] = Field(default_factory=list)
    clinical_safety_check: SafetyCheck

#JSON schema for the input data to the validation engine

class PatientDemographics(BaseModel):
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None

class Vitals(BaseModel):
    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None

    #model_config = ConfigDict(extra="allow")  # Allow extra fields not defined in the model
class DataQualityInput(BaseModel):
    demographics: PatientDemographics
    medications: List[str] = Field(default_factory=list)
    allergies : List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    vital_signs: Optional[Vitals] = None
    last_updated: Optional[date] = None


#JSON schema for the output data from the validation engine

class QualityBreakdown(BaseModel):
    completeness: float = Field(ge=0.0, le=100)
    validity: float = Field(ge=0.0, le=100)
    consistency: float = Field(ge=0.0, le=100)
    timeliness: float = Field(ge=0.0, le=100)

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"    

class Issue(BaseModel):
    field: str
    issue: str
    severity: Severity

class DataQualityOutput(BaseModel):
    overall_score: float = Field(ge=0.0, le=100)
    breakdown: QualityBreakdown
    issues_detected: List[Issue] = Field(default_factory=list)