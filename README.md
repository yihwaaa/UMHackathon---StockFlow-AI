# StockFlow AI

## Pitch Video
[Watch the pitch video here](https://youtu.be/replace-with-your-final-pitch-link)

## Overview
StockFlow AI is an AI-powered workflow system for supplier invoice discrepancy handling.  
It transforms unstructured or structured operational input into trackable workflow cases with:
1. issue classification
2. urgency prediction
3. next-action recommendation
4. missing-information handling
5. case timeline traceability

## Why this is not a normal manual workflow
Even if users type input manually, workflow handling is automated after intake:
1. one-time intake instead of repeated retyping across tools
2. consistent routing recommendation (manager/finance/operations)
3. duplicate case detection before creation
4. missing-field detection and clarification workflow
5. event timeline for auditable case history

## Core Features
1. **Smart Text Intake** (`POST /api/v1/analyze`)
2. **Structured Form Intake** (`POST /api/v1/cases/manual`)
3. **Case Dashboard & Filters** (`GET /api/v1/cases`)
4. **Status Management** (`PATCH /api/v1/cases/{id}/status`)
5. **Clarification Loop** (`PATCH /api/v1/cases/{id}/clarify`)
6. **Case Timeline / Events** (`GET /api/v1/cases/{id}/events`)
7. **Health and AI runtime visibility** (`GET /api/v1/health`)

## Tech Stack
1. Frontend: Streamlit
2. Backend: FastAPI + Uvicorn
3. Database: SQLite (SQLAlchemy ORM)
4. AI Layer: GLM (`ilmu-glm-5.1`) with deterministic fallback parsers
5. Language: Python

## Project Structure
```text
Source Code/
├─ frontend/
│  └─ app.py
├─ backend/
│  ├─ main.py
│  ├─ models.py
│  ├─ schemas.py
│  └─ database.py
├─ ai_engine/
│  └─ glm_client.py
├─ run.py
├─ start.py
├─ stockflow.db
└─ UMHackathon_Testing_Analysis_Documentation_Preliminary.md
```

## Local Setup
1. Create/activate virtual environment (if not already active)
   - Windows:
     `.\.venv\Scripts\activate`
2. Install dependencies:
   `python -m pip install fastapi uvicorn streamlit sqlalchemy requests pydantic`
3. Optional (for PDF text extraction utilities used in documentation workflow):
   `python -m pip install pypdf`

## Run the System
### Option A - Start both services together
```bash
python start.py
```

### Option B - Start separately
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
python -m streamlit run frontend/app.py
```

Frontend URL: `http://127.0.0.1:8501`  
Backend API: `http://127.0.0.1:8000`

## User Manual (All-in-one)
### 1. What this system is
StockFlow AI is a web system for supplier invoice discrepancy operations.  
It converts typed input into a structured, trackable workflow case.

Main pages:
1. New Case
2. Manage Cases
3. Why This System

### 2. Daily usage flow
1. Open **New Case**.
2. Choose one intake method:
   - Smart Text Intake (fast, flexible)
   - Structured Form Intake (high precision)
3. Submit once.
4. Open **Manage Cases** to:
   - update status
   - complete missing fields
   - review timeline events

### 3. Status meaning
1. `NEW` - case created
2. `PENDING_INFO` - required details missing
3. `ROUTED` - ready for handling
4. `RESOLVED` - case closed

### 4. Quick input tips
1. Always include supplier and invoice number.
2. Add exact product name.
3. Provide expected and actual quantity.
4. Use duplicate override only for truly separate incidents.

### 5. Benefits vs manual-only workflow
Even though users type input, this is different from normal manual process:
1. One-time intake instead of repeated retyping across chat/spreadsheets.
2. Consistent classification, urgency, and routing recommendation.
3. Immediate missing-field detection and clarification workflow.
4. Duplicate case prevention before queue pollution.
5. Timeline-based traceability for audit and review.

## API Quick Reference
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Service + AI mode health |
| GET | `/api/v1/cases` | List all cases |
| POST | `/api/v1/analyze` | Create case from unstructured text |
| POST | `/api/v1/cases/manual` | Create case from structured input |
| PATCH | `/api/v1/cases/{id}/status` | Update case status |
| PATCH | `/api/v1/cases/{id}/clarify` | Clarify/fix missing fields |
| GET | `/api/v1/cases/{id}/events` | View case timeline |

## Status Lifecycle
1. `NEW` - newly created
2. `PENDING_INFO` - required fields missing
3. `ROUTED` - ready for operational handling
4. `RESOLVED` - closed

## Submission Documents
1. Product Requirement Documentation (PRD)
2. System Analysis Documentation (SAD)
3. **Testing Analysis Documentation** (`UMHackathon_Testing_Analysis_Documentation_Preliminary.md`)

## Notes
1. Configure `GLM_API_KEY` to enable live GLM calls.
2. Without `GLM_API_KEY`, system runs deterministic fallback mode for reliability.
