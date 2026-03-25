# Clinical Data Reconciliation Engine

A comprehensive EHR (Electronic Health Record) integration system that reconciles medication data from multiple sources and validates clinical data quality using hybrid scoring algorithms combining deterministic metrics with LLM-powered reasoning.

## Architecture Overview

**Architecture Pattern**: 3-tier modular monolithic with clear separation of concerns:
- **Presentation Layer**: React components handling UI/UX
- **Business Logic Layer**: Domain-specific services (reconciliation, validation)
- **AI Service Layer**: LLM integration with fallback mechanisms
- **Data Models**: Pydantic models for validation and typing

## Features

### 1. Medication Reconciliation
- **Hybrid Scoring Algorithm**: Combines deterministic metrics (60%) with LLM reasoning (40%)
- **Multi-source Support**: Reconciles medications from multiple sources (EMR, pharmacy, patient)
- **Confidence Scoring**: 4-factor confidence calculation (quality, separation, agreement, uncertainty)
- **Uncertainty Detection**: Identifies conflicting sources and incomplete data
- **Safety Validation**: LLM-powered safety checks against patient conditions
- **Recommended Actions**: Provides actionable reconciliation guidance

**Scoring Formula**:
```
Deterministic Score = (reliability × 0.4) + (recency × 0.3) + (agreement × 0.3)
Recency Score = max(0, 1 - (days_old / 30)) with exponential decay
Hybrid Score = (deterministic × 0.6) + (llm × 0.4)
Confidence = quality + separation + agreement - uncertainty_penalty
```

### 2. Data Quality Validation
- **4-Dimension Assessment**:
  - **Completeness**: Checks for required fields (0-100)
  - **Validity**: Format and range validation (0-100)
  - **Consistency**: Logic validation (0-100)
  - **Timeliness**: Data freshness assessment (0-100)
- **Severity Classification**: High/Medium/Low issue categorization
- **Status Levels**: EXCELLENT (≥90), GOOD (≥75), ACCEPTABLE (≥60), POOR (≥40), CRITICAL (<40)
- **Issue Detection**: Identifies specific problems with actionable insights

**Validation Criteria**:
- Completeness: -5 points per missing critical field (max 100)
- Validity: -10 points per invalid field (DOB, gender, vitals, temp)
- Consistency: -15 points per inconsistency (negative age, missing medications for conditions)
- Timeliness: Based on last_updated (recent=100, >1yr=0)

### 3. LLM Integration
- **OpenAI GPT-3.5-turbo**: Primary model for clinical reasoning
- **Fallback Mechanism**: Default scores (0.5) if API fails
- **Structured Output**: JSON parsing for reliable extraction
- **Clinical Context**: Prompt engineering with patient conditions, allergies, labs
- **Safety Validation**: Identifies potential drug-condition conflicts
- **API Key Management**: Secure environment variable configuration

## Installation & Setup

### Prerequisites
- Python 3.8+ (backend)
- Node.js 14+ (frontend)
- OpenAI API key (get from https://platform.openai.com/api-keys)
- pip (Python package manager)
- npm (Node package manager)

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create a Python virtual environment
python -m venv venv

# 3. Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Configure environment variables
# Edit .env file and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-real-api-key-here

# 6. Run the backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the development server
npm start
# Frontend will open at http://localhost:3000
```

### Running Tests

```bash
# From project root
pytest tests/test_api.py -v

# Run specific test class
pytest tests/test_api.py::TestReconciliationAPI -v

# Run with coverage
pytest tests/test_api.py --cov=backend --cov-report=html
```

## API Endpoints

### Health Check
```http
GET /health
```
Response: `{"status": "healthy"}`

### Medication Reconciliation
```http
POST /api/reconcile/medication
Content-Type: application/json

{
  "patient_id": "P001",
  "patient_age": 65,
  "known_conditions": ["hypertension", "diabetes"],
  "current_labs": {"glucose": 145, "creatinine": 1.2},
  "medication_sources": [
    {
      "source": "EMR",
      "medications": [{"name": "Lisinopril", "dose": "10mg", "frequency": "daily"}],
      "data_date": "2024-03-24",
      "reliability": 0.95
    }
  ]
}
```

Response: 
```json
{
  "patient_id": "P001",
  "reconciled_medication": {
    "name": "Lisinopril",
    "dose": "10mg",
    "frequency": "daily"
  },
  "confidence_score": 0.87,
  "confidence_breakdown": {
    "overall": 0.87,
    "quality": 0.38,
    "separation": 0.26,
    "agreement": 0.18,
    "uncertainty": {
      "sources_conflict": false,
      "missing_data": false,
      "total_uncertainty": 0.0
    }
  },
  "safety_check": "PASSED",
  "safety_message": "No contraindications detected",
  "recommended_actions": [
    "Confirm Lisinopril continuation with prescriber"
  ]
}
```

### Data Quality Validation
```http
POST /api/validate/data-quality
Content-Type: application/json

{
  "patient_name": "John Doe",
  "date_of_birth": "1959-03-24",
  "gender": "M",
  "medications": ["Lisinopril 10mg daily"],
  "allergies": ["Penicillin"],
  "known_conditions": ["hypertension"],
  "heart_rate": 72,
  "blood_pressure": "140/85",
  "temperature": 37.0,
  "last_updated": "2024-03-24"
}
```

Response:
```json
{
  "overall_score": 88,
  "status": "GOOD",
  "dimensions": {
    "completeness": {
      "score": 100,
      "description": "All required fields present"
    },
    "validity": {
      "score": 100,
      "description": "All values in valid ranges"
    },
    "consistency": {
      "score": 95,
      "description": "Consistent data across fields"
    },
    "timeliness": {
      "score": 100,
      "description": "Data is recent"
    }
  },
  "issues_detected": [],
  "recommendations": []
}
```

## Data Models

### PatientRecord
```python
{
  "patient_id": str,
  "patient_age": int,
  "known_conditions": List[str],
  "current_labs": Dict[str, float],
  "medication_sources": List[MedicationSource]
}
```

### MedicationSource
```python
{
  "source": str,  # "EMR", "Pharmacy", "Patient"
  "medications": List[Dict],
  "data_date": str,  # ISO format
  "reliability": float  # 0.0-1.0
}
```

### DataQualityInput
```python
{
  "patient_name": str,
  "date_of_birth": str,  # ISO format
  "gender": str,
  "medications": List[str],
  "allergies": List[str],
  "known_conditions": List[str],
  "heart_rate": int,
  "blood_pressure": str,
  "temperature": float,
  "last_updated": str  # ISO format
}
```

## Project Structure

```
ClinicalDataReconciliationEngine/
├── backend/
│   ├── main.py                          # FastAPI application
│   ├── models.py                        # Pydantic data models
│   ├── requirements.txt                 # Python dependencies
│   ├── .env                             # Environment variables (local)
│   ├── ai_service/
│   │   ├── __init__.py
│   │   └── llm.py                       # LLMScorer with OpenAI
│   ├── reconcilation_service/
│   │   ├── __init__.py
│   │   └── reconcile_meds.py            # Reconciliation logic
│   └── validation_service/
│       ├── __init__.py
│       └── data_validator.py            # Data quality validation
├── frontend/
│   ├── src/
│   │   ├── index.js                     # React entry point
│   │   ├── index.css                    # Global styles
│   │   ├── App.js                       # Main component
│   │   ├── App.css                      # App styling
│   │   └── components/
│   │       ├── ReconciliationForm.js    # Reconciliation UI
│   │       ├── ReconciliationForm.css
│   │       ├── ValidationForm.js        # Validation UI
│   │       └── ValidationForm.css
│   ├── public/
│   │   └── index.html                   # HTML template
│   └── package.json                     # Node dependencies
├── tests/
│   └── test_api.py                      # Pytest test suite
├── .env.example                         # Environment template
└── README.md                            # This file
```

## Testing

The project includes comprehensive test coverage with 10+ test cases:

### Reconciliation Tests
- Single source reconciliation
- Multi-source conflict resolution
- Recency-based scoring
- Error handling for empty sources

### Validation Tests
- Complete data validation
- Incomplete data detection
- Invalid format detection
- Stale data handling

### Integration Tests
- Full workflow testing
- End-to-end reconciliation and validation

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Required
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional (defaults provided)
BACKEND_DEBUG=False
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

### Python Version Requirements

```
Python >= 3.8
```

### Key Dependencies

- **FastAPI**: 0.104.1 (web framework)
- **Uvicorn**: 0.24.0 (ASGI server)
- **Pydantic**: 2.5.0 (data validation)
- **OpenAI**: 1.3.0 (LLM integration)
- **Python-dotenv**: 1.0.0 (environment config)
- **Pytest**: 7.4.3 (testing)
- **React**: 18.2.0 (frontend)
- **React-scripts**: 5.0.1 (build tools)

## Performance Considerations

- **LLM Scoring Timeout**: 30 seconds default (configurable)
- **Medication Caching**: In-memory for current session
- **Concurrent Requests**: FastAPI handles async naturally
- **Frontend Load**: ~200KB JS, optimized component re-renders

## Security & Privacy

 **HIPAA-Safe Implementation**:
- No sensitive patient identifiers stored in memory
- Context-excluded from LLM prompts (no names, MRNs)
- Secure API key management via environment variables
- CORS middleware prevents unauthorized cross-origin requests
- Input validation on all endpoints prevents injection attacks

 **Best Practices**:
- Pydantic validation for all inputs
- Error handling without exposing system details
- Environment variable isolation for secrets
- No credentials in version control (.env.example template only)

## Development Workflow

```bash
# 1. Start backend (from backend directory)
source venv/bin/activate
uvicorn main:app --reload

# 2. In another terminal, start frontend (from frontend directory)
npm start

# 3. In another terminal, run tests (from project root)
pytest tests/test_api.py -v

# 4. Frontend automatically opens at http://localhost:3000
# Backend API available at http://localhost:8000
```

## Troubleshooting

### OpenAI API Key Issues
- Verify key format: `sk-` prefix with 48+ characters
- Check API key has appropriate permissions
- Ensure billing is active on OpenAI account
- Try generating a new key from https://platform.openai.com/api-keys

### Frontend Connection Issues
- Ensure backend is running on port 8000
- Check CORS is enabled in FastAPI
- Verify proxy setting in `frontend/package.json`
- Clear browser cache if needed

### Test Failures
- Ensure OpenAI API key is set in `.env`
- Check backend is not running (tests use test client)
- Verify Python environment is activated
- Run with `-v` flag for detailed output: `pytest tests/test_api.py -v`

## Future Enhancements

- [ ] Database persistence (PostgreSQL)
- [ ] User authentication & authorization
- [ ] Advanced audit logging
- [ ] Real-time reconciliation streaming
- [ ] Mobile application
- [ ] Integration with external EMR systems
- [ ] Machine learning model fine-tuning
- [ ] Advanced analytics dashboard

## License

This project implements requirements from clinical data reconciliation assessment.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test cases for usage examples
3. Verify environment configuration
4. Check backend logs for API errors

---

**Implementation Status**:  Complete
-  3-tier architecture
-  Hybrid scoring algorithm
-  React frontend
-  OpenAI LLM integration
-  Comprehensive test suite
-  API endpoints
-  HIPAA-safe practices
