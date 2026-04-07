# SPEC-0001: Flask + SQLAlchemy + React + Tailwind + DaisyUI Project Structure

## Overview

This specification defines the target project structure and tooling requirements for the Clinical Data Reconciliation Engine when migrated to a Flask + SQLAlchemy backend and a React + Tailwind CSS + DaisyUI frontend. See [ADR-0001](../../../adrs/ADR-0001-flask-sqlalchemy-react-tailwind-daisyui-project-structure.md) for the decision rationale behind this stack selection.

---

## Requirements

### Requirement: Flask Application Factory

The backend MUST be organized as a Flask application using the application factory pattern (`create_app()`). All routes MUST be registered via Flask Blueprints, with one blueprint per domain: `reconciliation`, `validation`, and `health`.

#### Scenario: App factory creates a runnable app

- **WHEN** `create_app()` is called with a configuration object or name
- **THEN** a configured Flask application instance is returned with all blueprints registered, CORS enabled, and SQLAlchemy bound

#### Scenario: Blueprints isolate domain routing

- **WHEN** a request arrives at `/api/reconcile/medication` or `/api/validate/data-quality`
- **THEN** it is handled by the `reconciliation` or `validation` blueprint respectively, with no cross-domain route collisions

---

### Requirement: SQLAlchemy ORM Data Layer

The backend MUST use Flask-SQLAlchemy for all database interactions. Domain models (Patient, Medication, ReconciliationResult, DataQualityResult) MUST be defined as SQLAlchemy ORM classes under `backend/models/`. Database schema changes MUST be managed via Flask-Migrate (Alembic).

#### Scenario: ORM model persists a reconciliation result

- **WHEN** the reconciliation service produces a result for a patient medication
- **THEN** the result MUST be saved to the database via the `ReconciliationResult` ORM model with a timestamp and patient reference

#### Scenario: Migration applies cleanly to a fresh database

- **WHEN** `flask db upgrade` is run against an empty database
- **THEN** all tables are created without errors and the schema matches the current ORM model definitions

#### Scenario: Database session is scoped per request

- **WHEN** a request begins and ends
- **THEN** a SQLAlchemy session MUST be opened at request start and committed or rolled back and closed at request end, with no session leakage between requests

---

### Requirement: API Endpoint Compatibility

All existing API endpoints MUST be preserved with identical HTTP methods, URL paths, request schemas, and response schemas after migration. The endpoints are:

| Method | Path | Blueprint |
|--------|------|-----------|
| GET | `/health` | `health` |
| POST | `/api/reconcile/medication` | `reconciliation` |
| POST | `/api/validate/data-quality` | `validation` |

#### Scenario: Existing tests pass after migration

- **WHEN** `pytest tests/test_api.py -v` is run against the Flask app (server running on port 5000)
- **THEN** all tests MUST pass without modification to test logic

#### Scenario: Request validation rejects malformed input

- **WHEN** a POST request is made with a missing required field (e.g., no `sources` array)
- **THEN** the endpoint MUST return HTTP 400 or HTTP 422 with a structured error body

---

### Requirement: OpenAPI Documentation

The Flask app SHOULD provide auto-generated OpenAPI 3.x documentation accessible at `/docs`. The documentation MUST cover all three endpoints with request/response schemas.

#### Scenario: Docs endpoint is reachable

- **WHEN** a GET request is made to `/docs`
- **THEN** an interactive OpenAPI UI (Swagger or ReDoc) MUST be returned

---

### Requirement: React Frontend with Tailwind CSS

The frontend MUST use Tailwind CSS (v3 or later) as its styling system. All hand-written component-level CSS files (`ReconciliationForm.css`, `ValidationForm.css`, `App.css`) MUST be replaced with Tailwind utility classes. Custom CSS MAY be used only for styles that cannot be expressed with Tailwind utilities.

#### Scenario: Application builds without custom CSS files

- **WHEN** `npm run build` is run after removing all `.css` component files
- **THEN** the build MUST succeed and the UI MUST render correctly with Tailwind-only styling

#### Scenario: Tailwind purges unused classes in production

- **WHEN** a production build is created
- **THEN** Tailwind MUST purge unused utility classes, keeping the CSS bundle under 20 KB (compressed)

---

### Requirement: DaisyUI Component Integration

The frontend MUST integrate DaisyUI as a Tailwind CSS plugin. Clinical data display elements (reconciliation confidence scores, safety check outcomes, data quality issues) MUST use DaisyUI semantic components: `badge`, `alert`, `card`, `stat`, and `progress`. Components MUST be WCAG 2.1 AA compliant for color contrast.

#### Scenario: Reconciliation result uses semantic DaisyUI components

- **WHEN** a reconciliation result is returned from the API
- **THEN** the confidence score MUST be displayed using a DaisyUI `progress` or `stat` component, and the clinical safety check outcome MUST use a `badge` or `alert` with appropriate semantic color (`success`, `warning`, `error`)

#### Scenario: Data quality breakdown uses DaisyUI cards

- **WHEN** a data quality validation result is returned
- **THEN** each quality dimension (completeness, validity, consistency, timeliness) MUST be displayed in a DaisyUI `card` or `stat` component with the numeric score visible

#### Scenario: DaisyUI theme is applied globally

- **WHEN** the application loads
- **THEN** a DaisyUI theme MUST be applied via the `data-theme` attribute on the root HTML element, and all DaisyUI components MUST inherit that theme's color tokens

---

### Requirement: Frontend–Backend API Proxy

The React development server MUST proxy API calls to the Flask backend. In production, API calls MUST be handled via a reverse proxy (e.g., nginx) or environment-variable-driven base URL configuration.

#### Scenario: Dev proxy routes API calls correctly

- **WHEN** the React dev server is running and a component calls `/api/reconcile/medication`
- **THEN** the request MUST be proxied to `http://localhost:5000/api/reconcile/medication` without CORS errors

---

### Requirement: Environment Variable Configuration

The backend MUST read all runtime configuration from environment variables. The required variables are:

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM service | *(none — fallback to heuristics)* |
| `DATABASE_URL` | SQLAlchemy database connection string | `sqlite:///cdre.db` |
| `BACKEND_DEBUG` | Flask debug mode | `False` |
| `BACKEND_HOST` | Flask bind host | `0.0.0.0` |
| `BACKEND_PORT` | Flask bind port | `5000` |

#### Scenario: App starts without OPENAI_API_KEY

- **WHEN** `OPENAI_API_KEY` is absent from the environment
- **THEN** the application MUST start successfully and LLM scoring MUST fall back to the heuristic scorer without raising an unhandled exception

#### Scenario: App uses DATABASE_URL for DB connection

- **WHEN** `DATABASE_URL` is set to a PostgreSQL connection string
- **THEN** SQLAlchemy MUST connect to that PostgreSQL database instead of the default SQLite file

---

### Requirement: Directory Structure

The project MUST follow this canonical directory layout after migration:

```
ClinicalDataReconciliationEngine/
├── backend/
│   ├── __init__.py           # app factory: create_app()
│   ├── config.py             # Config classes (Dev, Prod, Test)
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── patient.py
│   │   ├── medication.py
│   │   └── reconciliation.py
│   ├── api/                  # Flask blueprints
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── reconciliation.py
│   │   └── validation.py
│   ├── reconcilation_service/
│   ├── validation_service/
│   ├── ai_service/
│   └── migrations/           # Flask-Migrate / Alembic
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ReconciliationForm.jsx
│   │   │   └── ValidationForm.jsx
│   │   └── index.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── tests/
├── docs/
│   ├── adrs/
│   └── openspec/
├── .env.example
└── requirements.txt
```

#### Scenario: Backend module imports resolve correctly

- **WHEN** the Flask app is started via `flask run` from the project root
- **THEN** all blueprint and service imports MUST resolve without `ModuleNotFoundError`

#### Scenario: Frontend build artifacts are produced

- **WHEN** `npm run build` is run in `frontend/`
- **THEN** a `frontend/build/` directory MUST be created containing minified JS and CSS assets referencing DaisyUI-styled components
