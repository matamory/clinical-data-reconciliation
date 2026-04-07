# Clinical Data Reconciliation Engine

A clinical medication reconciliation engine that compares medication records from multiple EHR sources (EMR, pharmacy, patient reports) and validates healthcare data quality. Uses a **hybrid 60/40 scoring model**: 60% deterministic heuristics + 40% OpenAI GPT-3.5-turbo reasoning to produce reconciliation recommendations with confidence scores and drug-condition safety checks.

## Architecture

**Backend**: Flask + SQLAlchemy + Flask-Migrate (port 5000)
**Frontend**: React (port 3000)
**AI**: OpenAI GPT-3.5-turbo with local heuristic fallback
**Database**: SQLite (default) or PostgreSQL via `DATABASE_URL`

### Backend services

| Module | Purpose |
|--------|---------|
| `backend/api/` | Flask blueprints — reconciliation, validation, health |
| `backend/reconcilation_service/reconcile_meds.py` | Hybrid 60/40 scoring, confidence calculation, safety checks |
| `backend/validation_service/data_validator.py` | 4-dimension data quality scoring (0–100 per dimension) |
| `backend/ai_service/llm.py` | OpenAI GPT-3.5-turbo wrapper with heuristic fallback |
| `backend/models/` | SQLAlchemy ORM models (Patient, Medication, ReconciliationResult, DataQualityResult) |
| `backend/schemas.py` | Marshmallow request/response schemas |

### Scoring formulas

```
Deterministic score = (reliability × 0.30) + (recency × 0.30) + (agreement × 0.15) + (clinical_appropriateness × 0.25)
Recency score       = exp decay relative to newest source (30-day half-life)
Hybrid score        = (deterministic × 0.6) + (llm × 0.4)
Confidence          = (quality × 0.7) + (separation × 0.1) + (det_llm_agreement × 0.2)
```

If `OPENAI_API_KEY` is absent or the API call fails, the LLM score is replaced by a local heuristic — the engine remains fully functional.

## Setup

### Prerequisites

- Python 3.8+
- Node.js 14+
- pip and npm

### Backend

```bash
# From project root
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example backend/.env
# Edit backend/.env and set OPENAI_API_KEY (optional — falls back to heuristics)

flask --app backend db upgrade    # creates SQLite DB and applies migrations
flask --app backend run --port 5000 --reload
# OpenAPI docs: http://localhost:5000/docs
```

### Frontend

```bash
cd frontend
npm install
npm start
# Opens at http://localhost:3000, proxies API calls to localhost:5000
```

## Running tests

Tests use Flask's test client with an in-memory SQLite database — the backend server does **not** need to be running.

```bash
source venv/bin/activate
pytest tests/test_api.py -v

# Single test class
pytest tests/test_api.py::TestReconciliationAPI -v
pytest tests/test_api.py::TestValidationAPI -v
```

## API endpoints

### `GET /health`

```json
{"status": "healthy"}
```

### `POST /api/reconcile/medication`

**Request**
```json
{
  "patient_context": {
    "age": 65,
    "conditions": ["Type 2 Diabetes", "CKD Stage 3"],
    "recent_labs": [
      {"name": "eGFR", "value": {"numeric_value": 42, "unit": "mL/min"}}
    ]
  },
  "sources": [
    {
      "system": "EMR",
      "medication": "Metformin 500mg",
      "last_updated": "2026-03-15",
      "source_reliability": "high"
    },
    {
      "system": "Pharmacy",
      "medication": "Metformin 1000mg",
      "last_filled": "2026-02-01",
      "source_reliability": "medium"
    }
  ]
}
```

**Response**
```json
{
  "reconciled_medication": "Metformin 500mg",
  "confidence_score": 0.74,
  "clinical_safety_check": "REVIEW_REQUIRED",
  "reasoning": "eGFR of 42 warrants dose reduction per clinical guidelines...",
  "recommended_actions": [
    "Reduce Metformin dose for eGFR ≤ 45",
    "Confirm with prescriber"
  ],
  "model_used": "gpt-3.5-turbo"
}
```

`model_used` values: `"gpt-3.5-turbo"` | `"local-heuristic"` | `"fallback"`

### `POST /api/validate/data-quality`

**Request**
```json
{
  "demographics": {"name": "Jane Doe", "dob": "1961-04-12", "gender": "F"},
  "medications": ["Lisinopril 10mg daily"],
  "allergies": ["Penicillin"],
  "conditions": ["Hypertension"],
  "vital_signs": {"blood_pressure": "138/88", "heart_rate": 74, "temperature": 36.8},
  "last_updated": "2026-04-01"
}
```

**Response**
```json
{
  "overall_score": 91,
  "breakdown": {
    "completeness": 100,
    "validity": 100,
    "consistency": 95,
    "timeliness": 100
  },
  "issues_detected": []
}
```

Interactive OpenAPI docs (Swagger UI) are available at `http://localhost:5000/docs` when the server is running.

## Environment variables

Create `backend/.env` (template at `.env.example`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI key for LLM scoring | *(none — falls back to heuristics)* |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///cdre.db` |
| `BACKEND_DEBUG` | Flask debug mode | `False` |
| `BACKEND_HOST` | Bind host | `0.0.0.0` |
| `BACKEND_PORT` | Bind port | `5000` |

## Project structure

```
ClinicalDataReconciliationEngine/
├── backend/
│   ├── __init__.py              # Flask app factory: create_app()
│   ├── config.py                # Dev / Prod / Test config classes
│   ├── schemas.py               # Marshmallow request/response schemas
│   ├── pydantic_models.py       # Pydantic models used by service layer
│   ├── api/                     # Flask blueprints
│   │   ├── health.py
│   │   ├── reconciliation.py
│   │   └── validation.py
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── patient.py
│   │   ├── medication.py
│   │   └── reconciliation.py
│   ├── reconcilation_service/   # Core reconciliation logic (note: intentional spelling)
│   │   └── reconcile_meds.py
│   ├── validation_service/
│   │   └── data_validator.py
│   ├── ai_service/
│   │   └── llm.py
│   └── migrations/              # Flask-Migrate / Alembic
├── frontend/
│   └── src/
│       ├── App.js
│       └── components/
│           ├── ReconciliationForm.js
│           └── ValidationForm.js
├── tests/
│   └── test_api.py
├── docs/
│   ├── adrs/                    # Architecture Decision Records
│   └── openspec/specs/          # Specifications
├── requirements.txt
└── .env.example
```

> **Note**: `reconcilation_service/` is intentionally misspelled (missing an 'i') — match this spelling in imports.

## Security and privacy

- PII (patient name, DOB, MRN) is **never sent to OpenAI** — HIPAA design constraint
- API keys are loaded from environment variables only, never committed
- CORS is enabled via Flask-CORS; restrict origins in production via `CORS_ORIGINS`
- All inputs are validated via Marshmallow schemas before reaching service logic

## Key dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.3 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Migrate | 4.0.7 | Schema migrations (Alembic) |
| flask-smorest | 0.44.0 | OpenAPI 3 docs + request validation |
| marshmallow | 3.21.3 | Schema serialization |
| openai | 1.3.0 | GPT-3.5-turbo integration |
| pydantic | 2.5.0 | Service-layer data models |
| pytest | 7.4.3 | Test suite |
