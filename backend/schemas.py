"""Marshmallow schemas for request/response validation.

Governing: SPEC-0001 REQ "Flask API Routes", SPEC-0001 REQ "OpenAPI Documentation", ADR-0001
"""

from marshmallow import Schema, fields, EXCLUDE


class LabValueSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    numeric_value = fields.Float(allow_none=True)
    text_value = fields.Str(allow_none=True)
    unit = fields.Str(allow_none=True)


class LabResultSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True)
    value = fields.Nested(LabValueSchema, required=True)


class PatientContextSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    age = fields.Int(required=True)
    conditions = fields.List(fields.Str(), load_default=[])
    recent_labs = fields.List(fields.Nested(LabResultSchema), load_default=[])


class SourceRecordSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    system = fields.Str(required=True)
    medication = fields.Str(required=True)
    # Date fields kept as strings — service expects ISO date strings, not date objects
    last_updated = fields.Str(allow_none=True)
    last_filled = fields.Str(allow_none=True)
    source_reliability = fields.Str(required=True)


class PatientRecordSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    patient_context = fields.Nested(PatientContextSchema, required=True)
    sources = fields.List(fields.Nested(SourceRecordSchema), load_default=[])


class ReconciliationResultSchema(Schema):
    reconciled_medication = fields.Str(required=True)
    confidence_score = fields.Float(required=True)
    clinical_safety_check = fields.Str(required=True)
    reasoning = fields.Str(dump_default="")
    recommended_actions = fields.List(fields.Str(), dump_default=[])
    # Governing: SPEC-0002 REQ "LLM Scoring" — response MUST include model_used
    model_used = fields.Str(dump_default="unknown")
    # Governing: SPEC-0002 REQ "Uncertainty Detection and Recommended Actions" — MUST be in response
    requires_review = fields.Bool(dump_default=False)


class DemographicsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(allow_none=True)
    dob = fields.Str(allow_none=True)
    gender = fields.Str(allow_none=True)


class VitalSignsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    blood_pressure = fields.Str(allow_none=True)
    heart_rate = fields.Float(allow_none=True)
    temperature = fields.Float(allow_none=True)
    respiratory_rate = fields.Float(allow_none=True)


class DataQualityInputSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    demographics = fields.Nested(DemographicsSchema, allow_none=True)
    medications = fields.List(fields.Str(), load_default=[])
    allergies = fields.List(fields.Str(), load_default=[])
    conditions = fields.List(fields.Str(), load_default=[])
    vital_signs = fields.Nested(VitalSignsSchema, allow_none=True)
    last_updated = fields.Str(allow_none=True)


class QualityBreakdownSchema(Schema):
    completeness = fields.Int(required=True)
    validity = fields.Int(required=True)
    consistency = fields.Int(required=True)
    timeliness = fields.Int(required=True)


class IssueSchema(Schema):
    field = fields.Str(required=True)
    issue = fields.Str(required=True)
    severity = fields.Str(required=True)


class DataQualityOutputSchema(Schema):
    overall_score = fields.Int(required=True)
    breakdown = fields.Nested(QualityBreakdownSchema, required=True)
    issues_detected = fields.List(fields.Nested(IssueSchema), dump_default=[])
