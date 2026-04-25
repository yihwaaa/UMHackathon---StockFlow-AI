# StockFlow AI

## Pitch Video
[Watch the pitch video here](https://youtu.be/replace-with-your-final-pitch-link)

## UMHackathon Project Information
| Field | Detail |
|---|---|
| Competition | UMHackathon 2026 (Preliminary Round) |
| Domain | Domain 1: AI Systems & Agentic Workflow Automation |
| Project Name | StockFlow AI |
| System Title | AI Store Operations Copilot for Stock Discrepancy & Supplier Invoice Processing |
| Team Name | Jet2Holiday |
| Team Member | HIEW YI HWA |
| Repository | https://github.com/yihwaaa/UMHackathon---StockFlow-AI |
| Prepared For | UMHackathon 2026 Preliminary Round |

## Problem Statement
Retail stores still handle invoice-stock discrepancies through manual notes, spreadsheets, and chat follow-ups.  
This causes repeated key-in, inconsistent escalation, slow resolution, and weak traceability.

StockFlow AI addresses this with a stateful AI workflow system where GLM acts as the reasoning core for classification, extraction, and workflow recommendation.

## Solution Overview
StockFlow AI converts structured or unstructured discrepancy input into actionable workflow cases with:
1. issue type classification
2. urgency detection
3. required field extraction
4. missing-information handling
5. next-action recommendation
6. state tracking from intake to closure
7. timeline event logging for auditability

## Why This Is Better Than Manual-Only Process
Even if users still type input, workflow logic is automated after intake:
1. One-time intake instead of repetitive retyping in multiple tools.
2. Standardized routing suggestions (manager, finance, operations).
3. Immediate missing-field detection with guided clarification.
4. Duplicate-case prevention before queue pollution.
5. Timeline traceability for review and audit.

## Core Features
1. **Smart Text Intake** (`POST /api/v1/analyze`)
2. **Structured Form Intake** (`POST /api/v1/cases/manual`)
3. **Case Dashboard** (`GET /api/v1/cases`)
4. **Status Update** (`PATCH /api/v1/cases/{id}/status`)
5. **Clarification Loop** (`PATCH /api/v1/cases/{id}/clarify`)
6. **Case Timeline Events** (`GET /api/v1/cases/{id}/events`)
7. **Runtime Health & AI Mode** (`GET /api/v1/health`)

## System Architecture (High-Level)
1. **Frontend (Streamlit)**  
   User intake, case management, clarification, and timeline UI.
2. **Backend (FastAPI)**  
   Orchestration layer for validation, routing, lifecycle transitions, and API endpoints.
3. **AI Engine (GLM + deterministic fallback)**  
   Structured extraction, classification, and missing-field detection behavior.
4. **Database (SQLite + SQLAlchemy)**  
   Stores case data and case-event logs.

## Technology Stack
1. Frontend: Streamlit
2. Backend: FastAPI + Uvicorn
3. Database: SQLite (SQLAlchemy ORM)
4. AI Layer: GLM (`ilmu-glm-5.1`) + deterministic fallback
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
├─ UMHackathon Product Requirement Documentation.docx
├─ UMHackathon System Analysis Documentation.docx
└─ UMHackathon Quality Assurance Testing Documentation.docx
```

## Setup
From project root:

```powershell
.\.venv\Scripts\activate
python -m pip install fastapi uvicorn streamlit sqlalchemy requests pydantic
```

## Run
### Option A: Start both services
```powershell
python start.py
```

### Option B: Start separately
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
python -m streamlit run frontend/app.py
```

Frontend: `http://127.0.0.1:8501`  
Backend: `http://127.0.0.1:8000`

## Environment Variables
Set API key in environment (do not commit keys into code/files):

```powershell
$env:GLM_API_KEY="your_real_key_here"
```

Verification:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```
`glm_configured: true` means backend detected your key.

## API Quick Reference
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | API health, model and AI mode |
| GET | `/api/v1/cases` | List cases |
| POST | `/api/v1/analyze` | Create case from unstructured text |
| POST | `/api/v1/cases/manual` | Create case from structured form |
| PATCH | `/api/v1/cases/{id}/status` | Update case status |
| PATCH | `/api/v1/cases/{id}/clarify` | Clarify missing fields / fix values |
| GET | `/api/v1/cases/{id}/events` | Retrieve case timeline |

## User Manual (Integrated)
### 1. Daily Flow
1. Open **New Case**.
2. Choose **Smart Text Intake** or **Structured Form Intake**.
3. Submit once.
4. Open **Manage Cases** to update status, clarify missing fields, and review timeline.

### 2. Status Meaning
1. `NEW` - case created
2. `PENDING_INFO` - required information missing
3. `ROUTED` - ready for operational handling
4. `RESOLVED` - closed

### 3. Best Input Practice
1. Always include supplier and invoice number.
2. Include exact product name.
3. Include expected and actual quantity.
4. Use duplicate override only when it is truly a separate incident.

## Submission Documents
1. Product Requirement Documentation (PRD)  
   `UMHackathon Product Requirement Documentation.docx`
2. System Analysis Documentation (SAD)  
   `UMHackathon System Analysis Documentation.docx`
3. Quality Assurance Testing Documentation (QATD)  
   `UMHackathon Quality Assurance Testing Documentation.docx`
4. Official Event References  
   `UMHackathon2026 Official Handbook.docx`, `UMHackathon2026 Judging Criteria.docx`

## Maintainer
- **HIEW YI HWA** (Team Jet2Holiday)  
- GitHub: https://github.com/yihwaaa
