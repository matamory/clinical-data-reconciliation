---
status: accepted
date: 2026-03-27
decision-makers: Yesenia
---

# ADR-0001: Flask + SQLAlchemy Backend and React + Tailwind + DaisyUI Frontend Project Structure

## Context and Problem Statement

The Clinical Data Reconciliation Engine currently uses FastAPI as the web framework with no database persistence layer, and a plain React frontend with custom CSS. As the project evolves, it requires a persistent data store for patient records, reconciliation history, and audit trails, alongside a consistent, accessible UI component system. What framework and tooling combination best supports these needs while remaining ergonomic for a Python/React developer?

## Decision Drivers

* Need for a relational database to persist patient records, reconciliation results, and audit logs
* HIPAA compliance considerations requiring traceable, auditable data access
* Developer ergonomics: a familiar, batteries-included Python web framework
* Frontend consistency: a utility-first CSS approach with accessible, pre-built clinical UI components
* Ability to integrate with OpenAI API and other external services without framework friction

## Considered Options

* **Option A**: Keep FastAPI + add SQLAlchemy + add Tailwind/DaisyUI to React
* **Option B**: Migrate to Flask + SQLAlchemy backend + React + Tailwind + DaisyUI frontend
* **Option C**: Full-stack Python with Flask + SQLAlchemy + HTMX (no separate React app)

## Decision Outcome

Chosen option: **Option B — Flask + SQLAlchemy backend + React + Tailwind + DaisyUI frontend**, because Flask's explicit routing and application factory pattern pair naturally with SQLAlchemy ORM for a clinical domain model, and React + Tailwind + DaisyUI provide a component-first UI layer with accessible defaults suitable for healthcare dashboards.

### Consequences

* Good, because SQLAlchemy ORM enables rich domain models (Patient, Medication, ReconciliationResult) with migrations via Alembic
* Good, because Flask's blueprint system cleanly separates reconciliation, validation, and auth concerns
* Good, because DaisyUI's semantic component classes (badge, alert, card) map well to clinical data display patterns
* Good, because Tailwind's utility classes eliminate the need for per-component CSS files (removing `ReconciliationForm.css`, `ValidationForm.css`, etc.)
* Bad, because migration from FastAPI requires rewriting API route handlers and Pydantic models to Flask/marshmallow or Flask-Pydantic patterns
* Bad, because Flask lacks FastAPI's automatic OpenAPI doc generation — Flasgger or flask-smorest would need to be added separately
* Bad, because the team loses FastAPI's native async support; async tasks (LLM calls) must be handled via threads or a task queue (Celery/Redis)

### Confirmation

Implementation is confirmed when:
- `backend/` contains a Flask app factory (`create_app()`), SQLAlchemy models under `backend/models/`, and blueprints under `backend/api/`
- Database migrations run cleanly via `flask db upgrade`
- `frontend/` installs `tailwindcss` and `daisyui` and removes hand-written `.css` files
- All existing API endpoints (`/api/reconcile/medication`, `/api/validate/data-quality`, `/health`) pass the existing test suite

## Pros and Cons of the Options

### Option A: Keep FastAPI + add SQLAlchemy + Tailwind/DaisyUI

Minimal disruption — existing routes, Pydantic models, and async patterns stay in place. SQLAlchemy integrates with FastAPI cleanly via dependency injection.

* Good, because zero framework migration cost
* Good, because FastAPI's async handlers work natively with async LLM clients
* Good, because automatic OpenAPI docs are already in place at `/docs`
* Bad, because FastAPI's dependency injection style adds boilerplate for DB session management
* Bad, because FastAPI is newer and less documented for clinical/enterprise patterns compared to Flask

### Option B: Flask + SQLAlchemy + React + Tailwind + DaisyUI (chosen)

A deliberate migration to a well-established Python micro-framework with an explicit ORM and a modern frontend stack.

* Good, because Flask + SQLAlchemy is the dominant pattern in Python clinical and enterprise web apps, with extensive documentation and community support
* Good, because Flask blueprints provide natural separation of the reconciliation, validation, and AI service concerns
* Good, because Tailwind + DaisyUI removes custom CSS overhead and provides consistent, accessible components (modals, alerts, badges) out of the box
* Neutral, because Flask is synchronous by default — LLM calls must use `concurrent.futures` or be offloaded
* Bad, because OpenAPI/Swagger docs require an additional library (flask-smorest recommended)

### Option C: Flask + SQLAlchemy + HTMX (no React)

Replace the React SPA with server-rendered Jinja2 templates enhanced by HTMX for dynamic updates.

* Good, because eliminates the frontend build pipeline entirely (no npm, webpack, or node_modules)
* Good, because server-side rendering simplifies session management and reduces frontend complexity
* Bad, because existing React components (ReconciliationForm, ValidationForm) would need full rewrites as Jinja2 templates
* Bad, because HTMX's partial-replacement model is harder to reason about for complex, multi-step clinical forms
* Bad, because the team loses React's component reuse and ecosystem (charting libraries, form validation)

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (React + Tailwind + DaisyUI) — port 3000"]
        A[App.js] --> B[ReconciliationForm]
        A --> C[ValidationForm]
        B --> D[DaisyUI Components\nbadge · alert · card · modal]
        C --> D
    end

    subgraph Backend ["Backend (Flask + SQLAlchemy) — port 5000"]
        E[Flask App Factory\ncreate_app] --> F[Blueprints]
        F --> G[/api/reconcile/medication]
        F --> H[/api/validate/data-quality]
        F --> I[/health]
        E --> J[SQLAlchemy ORM]
        J --> K[(PostgreSQL / SQLite)]
        G --> L[reconciliation_service]
        H --> M[validation_service]
        L --> N[ai_service / LLM]
        M --> N
    end

    Frontend -- "HTTP JSON\nproxy → :5000" --> Backend
    N -- "OpenAI API" --> O[GPT-3.5-turbo]
```

## More Information

- The `reconcilation_service/` directory name is intentionally misspelled in the current codebase and should be preserved or corrected as part of this migration.
- PII must remain excluded from LLM prompts (HIPAA). This constraint carries forward unchanged.
- Flask-Migrate (Alembic) is the recommended migration tool for SQLAlchemy schema changes.
- Recommended Flask extensions: `flask-sqlalchemy`, `flask-migrate`, `flask-cors`, `flask-smorest` (OpenAPI), optionally `flask-pydantic` for request validation.
- DaisyUI themes should be evaluated for WCAG 2.1 AA contrast compliance before adoption in a clinical UI.
- Related next step: define a spec for the data persistence layer (Patient, Medication, ReconciliationResult models) and the frontend component library setup.
