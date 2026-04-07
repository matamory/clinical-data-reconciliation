# SPEC-0002: Medication Reconciliation

## Overview

This specification defines the requirements for the `POST /api/reconcile/medication` endpoint and its underlying reconciliation engine. Given conflicting medication records from multiple EHR sources, the engine SHALL determine the most likely accurate medication for a patient and return a calibrated confidence score with clinical reasoning. See [ADR-0002](../../../adrs/ADR-0002-hybrid-deterministic-llm-reconciliation-scoring.md) for the decision to use a hybrid 60% deterministic + 40% LLM scoring model.

---

## Requirements

### Requirement: API Contract

The reconciliation endpoint MUST accept a JSON payload containing a `patient_context` object and a `sources` array, and MUST return a JSON response containing `reconciled_medication`, `confidence_score`, `reasoning`, `recommended_actions`, and `clinical_safety_check`.

#### Scenario: Valid multi-source request

- **WHEN** a client POSTs to `/api/reconcile/medication` with a `patient_context` (age, conditions, recent_labs) and two or more `sources` (each with system, medication, last_updated or last_filled, source_reliability)
- **THEN** the response MUST include `reconciled_medication` (string), `confidence_score` (float 0–1), `reasoning` (string), `recommended_actions` (non-empty list), and `clinical_safety_check` ("PASSED", "FAILED", or "REVIEW_REQUIRED")

#### Scenario: Empty sources array

- **WHEN** a client POSTs with an empty or absent `sources` array
- **THEN** the API MUST return an error response (HTTP 422 or 400) and MUST NOT return a reconciled medication

#### Scenario: Missing optional fields

- **WHEN** a source record omits `last_updated` and `last_filled`
- **THEN** the engine MUST assign a neutral recency score (0.5) to that source rather than rejecting the request

---

### Requirement: Deterministic Scoring

The engine MUST compute a deterministic sub-score for each source candidate based on four weighted components: source reliability (0.30), recency (0.30), cross-source agreement (0.15), and clinical appropriateness (0.25). The combined deterministic score MUST be clamped to the range [0.0, 1.0].

#### Scenario: High-reliability source wins on reliability alone

- **WHEN** two sources have equal recency and agreement scores but different reliability levels ("high" vs "low")
- **THEN** the "high" reliability source MUST receive a higher deterministic sub-score

#### Scenario: Recency decay between sources

- **WHEN** two sources have the same reliability but one was updated 60 days before the other
- **THEN** the older source MUST receive a meaningfully lower recency sub-score (exponential decay with 30-day half-life relative to the newest source)

#### Scenario: Clinical appropriateness — Metformin with renal impairment

- **WHEN** a source records "Metformin" at a daily dose exceeding 1000 mg and the patient context includes eGFR ≤ 45
- **THEN** that source's clinical appropriateness sub-score MUST be less than 0.5, reducing its overall deterministic score

---

### Requirement: LLM Scoring

The engine MUST query an LLM (GPT-3.5-turbo) to produce a medication score and reasoning when a valid `OPENAI_API_KEY` is present. The LLM prompt MUST include patient age, conditions, and recent labs, but MUST NOT include any PII (name, date of birth, MRN, or other direct identifiers). LLM calls MUST be retried once on transient failure before falling back.

#### Scenario: LLM available

- **WHEN** `OPENAI_API_KEY` is set and the OpenAI API responds successfully
- **THEN** the response MUST include `"model_used": "gpt-3.5-turbo"` and the LLM score MUST be incorporated at 40% weight in the hybrid formula

#### Scenario: LLM unavailable — missing API key

- **WHEN** `OPENAI_API_KEY` is absent or does not start with "sk-"
- **THEN** the engine MUST fall back to the local heuristic scorer and MUST NOT raise an exception or return an error to the caller; the response MUST include `"model_used": "local-heuristic"`

#### Scenario: LLM call fails after retry

- **WHEN** the OpenAI API raises an exception on both the initial call and the single retry
- **THEN** the engine MUST fall back to the local heuristic scorer; the response MUST include `"model_used": "fallback"` and the `reasoning` field MUST indicate the fallback was used

---

### Requirement: Hybrid Score Combination

The engine MUST combine deterministic and LLM sub-scores using the formula `hybrid_score = (det_score × 0.60) + (llm_score × 0.40)` for each candidate. When the LLM is unavailable (model_used is "fallback" or "local-heuristic"), the LLM score for each candidate MUST be set equal to that candidate's deterministic score to avoid first-source bias.

#### Scenario: Normal hybrid combination

- **WHEN** both deterministic and LLM scores are available
- **THEN** the winning candidate MUST be the source with the highest `det × 0.60 + llm × 0.40` value

#### Scenario: LLM fallback — unbiased ranking

- **WHEN** the LLM is unavailable and all sources have different deterministic scores
- **THEN** the candidate ranking MUST match pure deterministic ordering (the source with the highest det_score MUST have the highest hybrid_score)

---

### Requirement: Confidence Score Calibration

The engine MUST compute `confidence_score` from three factors: winner quality (`hybrid_score × 0.70`), score separation from the second-best candidate (`gap × 0.50 × 0.10`, capped at 0.10), and det/LLM agreement (`(1 − |det − llm|) × 0.20`). The final score MUST be clamped to [0.0, 1.0].

#### Scenario: High-confidence single dominant source

- **WHEN** one source scores significantly higher than all others (gap ≥ 0.4) and det/LLM scores agree within 0.1
- **THEN** `confidence_score` SHOULD be ≥ 0.80

#### Scenario: Conflicting sources reduce confidence

- **WHEN** all sources report different medications and no single candidate dominates
- **THEN** `confidence_score` MUST be lower than the scenario where sources agree, all else equal

---

### Requirement: Safety Check

The engine MUST perform a clinical safety check on the reconciled medication using LLM-based drug-condition interaction analysis when the API is available, falling back to a "REVIEW_REQUIRED" result when it is not. The safety check MUST produce one of three values: "PASSED", "FAILED", or "REVIEW_REQUIRED". A "FAILED" status MUST appear in `clinical_safety_check` when a known contraindication is detected.

#### Scenario: Safe medication, no concerns

- **WHEN** the LLM safety check returns `is_safe: true` and no concerns
- **THEN** `clinical_safety_check` MUST equal "PASSED"

#### Scenario: Medication flagged as unsafe

- **WHEN** the LLM safety check returns `is_safe: false`
- **THEN** `clinical_safety_check` MUST equal "FAILED"

#### Scenario: LLM unavailable for safety check

- **WHEN** the API key is absent or the safety check call fails
- **THEN** `clinical_safety_check` MUST equal "REVIEW_REQUIRED" and the engine MUST NOT raise an exception

---

### Requirement: Uncertainty Detection and Recommended Actions

The engine MUST detect uncertainty signals (source conflict, missing data) and MUST reflect them in `recommended_actions`. When any uncertainty signal is present, `requires_review` MUST be `true` in the response.

#### Scenario: Sources conflict

- **WHEN** two or more sources report different normalized medication names
- **THEN** `recommended_actions` MUST contain at least one action instructing the clinician to clarify conflicting records, and `requires_review` MUST be `true`

#### Scenario: All sources agree

- **WHEN** all sources report the same normalized medication name
- **THEN** `recommended_actions` MAY be limited to documentation actions and `requires_review` MAY be `false`
