# SPEC-0003: Data Quality Validation

## Overview

This specification defines the requirements for the `POST /api/validate/data-quality` endpoint and its underlying `DataValidator` service. Given a patient data payload, the engine SHALL score data quality across four independent dimensions and return a calibrated overall score with a per-dimension breakdown and a list of detected issues. The endpoint is registered via the `validation` Flask blueprint (ADR-0001) and persists every result to the database (SPEC-0001 REQ "SQLAlchemy ORM Data Layer").

---

## Requirements

### Requirement: API Contract

The validation endpoint MUST accept a JSON payload and MUST return a JSON response containing `overall_score` (integer 0–100), `breakdown` (object with four dimension scores), and `issues_detected` (array of issue objects).

#### Scenario: Complete patient data

- **WHEN** a client POSTs to `/api/validate/data-quality` with a fully populated payload (demographics, medications, allergies, conditions, vital_signs, last_updated)
- **THEN** the response MUST include `overall_score` (int 0–100), `breakdown.completeness`, `breakdown.validity`, `breakdown.consistency`, `breakdown.timeliness` (all int 0–100), and `issues_detected` (array, may be empty)

#### Scenario: Malformed or missing input

- **WHEN** a POST request is made with a missing required structure or an unparseable body
- **THEN** the endpoint MUST return HTTP 400 or HTTP 422 with a structured error body and MUST NOT return a partial quality score

---

### Requirement: Overall Score Formula

The engine MUST compute `overall_score` using the formula:

```
overall_score = (avg_dimensions × 0.30) + (completeness × 0.70)
```

where `avg_dimensions = (completeness + validity + consistency + timeliness) / 4`. The final score MUST be clamped to [0, 100] and returned as an integer.

#### Scenario: Completeness dominates the overall score

- **WHEN** completeness is 0 and all other dimensions are 100
- **THEN** `overall_score` MUST equal `(75 × 0.30) + (0 × 0.70)` = 22 (rounded), not the simple average of 75

#### Scenario: Perfect data

- **WHEN** all four dimension scores are 100
- **THEN** `overall_score` MUST equal 100

---

### Requirement: Completeness Dimension

The engine MUST assess completeness by checking for the presence of required patient fields and applying a penalty per missing field. The completeness score MUST start at 100 and decrease by the configured penalty for each missing field.

Required fields and their penalties:

| Field | Severity | Penalty |
|-------|----------|---------|
| `demographics.name` | high | 10 |
| `demographics.dob` | medium | 6 |
| `demographics.gender` | low | 4 |
| `medications` (non-empty list) | medium | 8 |
| `allergies` (non-empty list) | medium | 15 |
| `vital_signs` (object present) | high | 15 |
| `vital_signs.blood_pressure` | medium | 6 |
| `vital_signs.heart_rate` | medium | 6 |
| `conditions` (non-empty list) | low | 4 |

#### Scenario: All fields present

- **WHEN** demographics, medications, allergies, conditions, vital_signs, and last_updated are all populated
- **THEN** `breakdown.completeness` MUST equal 100 and no completeness issues MUST appear in `issues_detected`

#### Scenario: Missing allergies

- **WHEN** the `allergies` array is absent or empty
- **THEN** `breakdown.completeness` MUST be reduced by 15 and `issues_detected` MUST contain an issue with `field: "allergies"` and `severity: "medium"`

---

### Requirement: Validity Dimension

The engine MUST assess validity by checking field values against expected formats and clinical ranges. The validity score MUST start at 100 and decrease by a penalty per invalid field.

Validity rules:

| Field | Rule | Penalty |
|-------|------|---------|
| `demographics.dob` | ISO date format; MUST NOT be in the future | 12 (invalid format), 20 (future date) |
| `demographics.gender` | MUST be one of: male, female, other, unknown | 8 |
| `vital_signs.blood_pressure` | Format `"systolic/diastolic"`; systolic 70–250, diastolic 40–150; systolic MUST exceed diastolic | 15 (invalid format or impossible value), 25 (clinically implausible range) |
| `vital_signs.heart_rate` | Integer 30–200 | 15 |
| `vital_signs.temperature` | Numeric 35.0–42.0 °C | 15 |

#### Scenario: Clinically implausible blood pressure

- **WHEN** `vital_signs.blood_pressure` is provided with systolic < 70 or systolic > 250
- **THEN** `breakdown.validity` MUST be reduced by 25 and `issues_detected` MUST contain an issue with `field: "vital_signs.blood_pressure"` and `severity: "medium"`

#### Scenario: Future date of birth

- **WHEN** `demographics.dob` is a date that is after today
- **THEN** `breakdown.validity` MUST be reduced by 20 and `issues_detected` MUST contain an issue with `field: "demographics.dob"` and `severity: "high"`

---

### Requirement: Consistency Dimension

The engine MUST assess internal data consistency. The consistency score MUST start at 100 and decrease by 15 per detected inconsistency.

Consistency rules:

| Rule | Severity |
|------|----------|
| Age derived from DOB MUST NOT be negative | high |
| Patient with a diabetes condition SHOULD have at least one diabetes medication (metformin, insulin, glipizide) | low |

#### Scenario: Negative age from DOB

- **WHEN** `demographics.dob` produces a calculated age below 0 (future date already past validity check)
- **THEN** `breakdown.consistency` MUST be reduced by 15 and `issues_detected` MUST contain an issue with `field: "demographics.dob"` and `severity: "high"`

#### Scenario: Diabetes condition without medication

- **WHEN** `conditions` contains a value with "diabetes" and `medications` contains no metformin, insulin, or glipizide entry
- **THEN** `breakdown.consistency` MUST be reduced by 15 and `issues_detected` MUST contain an issue with `field: "medications"` and `severity: "low"`

---

### Requirement: Timeliness Dimension

The engine MUST assess data freshness using `last_updated`. When `last_updated` is absent, the timeliness score MUST default to 50 (neutral). When present, the score MUST be determined by age of the record.

Timeliness thresholds:

| Data age | Score | Severity |
|----------|-------|---------|
| < 30 days | 100 | — |
| 30–90 days | 75 | low |
| 91–365 days | 50 | medium |
| > 365 days | 20 | high |
| Future date | 30 | high |
| Missing | 50 | medium |

#### Scenario: Data over one year old

- **WHEN** `last_updated` is more than 365 days in the past
- **THEN** `breakdown.timeliness` MUST equal 20 and `issues_detected` MUST contain an issue with `field: "last_updated"` and `severity: "high"`

#### Scenario: Missing last_updated

- **WHEN** `last_updated` is absent from the payload
- **THEN** `breakdown.timeliness` MUST equal 50 and `issues_detected` MUST contain an issue with `field: "last_updated"` and `severity: "medium"`

---

### Requirement: Issue Object Schema

Every entry in `issues_detected` MUST be a JSON object with exactly three fields: `field` (string — the dotted path of the affected field), `issue` (string — human-readable description), and `severity` (string — one of `"high"`, `"medium"`, `"low"`).

#### Scenario: Issue severity values

- **WHEN** the response includes items in `issues_detected`
- **THEN** each item's `severity` field MUST be the string `"high"`, `"medium"`, or `"low"` — never an enum class name like `"Severity.high"`

---

### Requirement: ORM Persistence

Every validation result MUST be persisted to the database via the `DataQualityResult` ORM model immediately after scoring, with a UTC `created_at` timestamp.

#### Scenario: Result saved on success

- **WHEN** a valid request completes scoring
- **THEN** a `DataQualityResult` row MUST be written to the database with `overall_score`, `completeness`, `validity`, `consistency`, `timeliness`, and `issues_detected` populated

#### Scenario: Rollback on failure

- **WHEN** the scoring service raises an exception
- **THEN** `db.session.rollback()` MUST be called and the endpoint MUST return HTTP 400 with a `detail` field — no partial row MUST be committed
