# Centralised Document Tracking and Routing System (CDTRS)

**CDTRS** is an enterprise-grade desktop document workflow, routing, and lifecycle tracking system built with **Python**, **PySide6 (Qt 6 Widgets)**, **FastAPI**, **PostgreSQL**, and **PaddleOCR**. 

It provides an end-to-end operational pipeline for intake, executive review, departmental delegation, execution tracking, and audit logging across administrative organizations.

---

## 1. Project Overview

In large administrative and defense organizations, official communications, policy directives, inter-departmental notices, and procurement sanctions move across multiple administrative tiers. Physical handling or ad-hoc emails often result in lost accountability, missed deadlines, and lack of traceability.

CDTRS solves this by establishing a unified, role-based desktop interface backed by a centralized REST & WebSocket server with real-time lifecycle tracking, deadline monitoring, PaddleOCR text extraction, and advisory routing intelligence.

### Primary User Roles:
- **Director Secretary (DS):** Handles document intake (scans, emails, manual dispatches), metadata extraction (PaddleOCR + Regex rule heuristics), executive routing to the Director, departmental routing to HODs or direct staff, action reminders, and final document closure.
- **The Director:** Performs executive reviews, examines progress follow-ups, records administrative directives and remarks, and returns documents to the DS for execution.
- **Head of Department (HOD):** Manages departmental workload (Finance, Procurement, Administration, etc.), delegates actionable documents to specific department employees, monitors task progress, and records department remarks.
- **Department Employee:** Receives direct task assignments, manages assigned deliverables, uploads attachments, and submits structured progress reports.

---

## 2. Current Project Status

The CDTRS system is fully developed, tested, and integrated across all architectural tiers:

- **Desktop UI & Theming (`frontend/`):** Complete PySide6 graphical interface with custom QSS stylesheet (`theme.qss`), KPI metric tiles, interactive data tables, and operational action cards.
- **Pluggable Repository Architecture:** Supports both **Live REST API Mode** (connecting to the local or cloud FastAPI backend) and **Mock Mode** (in-memory demonstration dataset).
- **Authentication & Role-Based Shell:** Central login window with JWT bearer token session management, role-based navigation sidebars, and clean user error dialogs.
- **Document Intake & PaddleOCR Engine (`OCR/`):** Automated extraction of document references, titles, sources, priorities, and deadlines from PDFs and images using PaddleOCR and rule-based NLP heuristics.
- **Advisory Routing Intelligence:** Context-aware suggestion banner detecting explicit delegation targets in Director remarks without unauthorized auto-routing.
- **Departmental Delegation & Progress Workflow:** Full task assignment workflow, 2-step progress updates, and multipart file attachment handling with 20 MB upload limits.
- **Deadlines & Action Reminders:** High-priority tracking, 7-day cutoff filters, overdue warnings, and downstream reminder dispatch.
- **Workflow History & Audit Trail:** Chronological document-centric timeline recording all lifecycle actions, actors, timestamps, and remarks.
- **Live Real-Time Events:** WebSocket event stream (`/api/v1/ws`) broadcasting state changes across connected desktop clients.

---

## 3. Architecture

CDTRS is built on a clean **layered repository architecture** ensuring strict separation of concerns between user interface, business logic, domain modeling, and data transport.

```text
┌─────────────────────────────────────────────────────────────┐
│                    UI & Presentation Layer                  │
│       ui/ (LoginWindow, MainWindow, Sidebar)                │
│       pages/ (Dashboard, Inbox, Intake, Documents, History) │
│       components/ (DocumentViewer, Tables, Dialogs)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service / Domain Layer                  │
│   services/ (auth, document, routing, ocr, workflow, etc.)  │
│   models/   (DocumentModel, UserModel, Enums, Serialization)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository Abstraction Layer              │
│                     repositories/base.py                    │
│                  repositories/provider.py                   │
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│  [API Mode]                  │  [Mock Mode]                 │
│  repositories/api_repository │  repositories/mock_repository│
│             │                │              │               │
│             ▼                │              ▼               │
│  api/client.py               │   In-Memory Golden Dataset   │
│             │                │   (Zero Network Needed)      │
│             ▼                │                              │
│  FastAPI Backend             │                              │
│  (http://127.0.0.1:8000/api) │                              │
└─────────────┬────────────────┴──────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    OCR & Backend Services                   │
│   OCR/      (PaddleOCR, PyMuPDF, Rule Heuristics Engine)    │
│   backend/  (FastAPI, SQLAlchemy ORM, PostgreSQL Database)  │
└─────────────────────────────────────────────────────────────┘
```

### Why This Separation Matters:
- **Repository-Agnostic UI:** UI components and services communicate exclusively with the `BaseRepository` interface. Switching between live API mode and local offline Mock mode requires zero changes to UI or business logic.
- **Robust Adapter Pattern:** `APIRepository` cleanly handles REST serialization, multipart uploads, route code translation, and backend aliases without leaking backend implementation details into the presentation layer.

---

## 4. Project Directory Structure

```text
CDTRS/
├── backend/                       # FastAPI backend server & database engine
│   ├── crud.py                    # Database queries, mutations & routing logic
│   ├── database.py                # SQLAlchemy engine, session maker & connection pool
│   ├── main.py                    # REST API endpoints, WebSockets & file handlers
│   ├── models.py                  # 17 SQLAlchemy ORM models & relational mappings
│   ├── schemas.py                 # Pydantic v2 validation & serialization schemas
│   ├── seed.py                    # Database table initialization & default user seeder
│   ├── clear_documents.py         # Reset database test documents script
│   ├── requirements.txt           # Backend Python dependencies
│   ├── .env                       # Backend environment configuration
│   └── readme.md                  # Comprehensive backend technical reference
│
├── frontend/                      # PySide6 desktop application
│   ├── api/                       # REST API client & networking
│   │   ├── client.py              # HTTP client with Windows SSL support (pip_system_certs)
│   │   ├── endpoints.py           # Centralized REST route constants (/api/v1/...)
│   │   └── exceptions.py          # Structured API error hierarchy
│   ├── components/                # Reusable PySide6 UI widgets
│   │   ├── document_info.py       # Metadata information panel
│   │   ├── document_preview.py    # Document content & attachment preview (PDF/Images)
│   │   ├── document_table.py      # Standard registered documents table
│   │   ├── document_viewer.py     # Document viewer with actions & routing banner
│   │   ├── priority_badge.py      # High/Medium/Low colored status badges
│   │   ├── routing_dialogs.py     # Route to Director, HOD, and Staff dialogs
│   │   └── state_widgets.py       # Empty state & loading illustrations
│   ├── config/                    # Configuration management
│   │   └── settings.py            # Environment variable parsing & settings dataclass
│   ├── models/                    # Typed domain models & Enums
│   │   ├── attachment.py          # DocumentAttachment domain model
│   │   ├── document.py            # DocumentModel domain model
│   │   ├── enums.py               # RoleEnum, DocumentStatusEnum, PriorityEnum, etc.
│   │   ├── progress_update.py     # ProgressUpdateModel domain model
│   │   ├── user.py                # UserModel domain model
│   │   ├── work_assignment.py     # WorkAssignmentModel domain model
│   │   └── workflow_event.py      # WorkflowEventModel audit event model
│   ├── pages/                     # Application pages
│   │   ├── dashboard.py           # Role-specific operational dashboards
│   │   ├── director_inbox.py      # Director executive review queue
│   │   ├── director_reviewed.py   # Director reviewed documents archive
│   │   ├── document_intake.py     # Registration & OCR text extraction form
│   │   ├── documents.py           # Central searchable repository with filters
│   │   ├── employee_tasks.py      # Employee active tasks & progress submissions
│   │   ├── history.py             # System audit trail & chronological timeline
│   │   ├── hod_inbox.py           # Departmental tasks & staff delegation
│   │   └── inbox.py               # DS raw incoming dispatches queue
│   ├── repositories/              # Data access adapters
│   │   ├── api_repository.py      # Live REST API implementation
│   │   ├── base.py                # BaseRepository abstract interface
│   │   ├── mock_repository.py     # Standalone in-memory golden reference repository
│   │   └── provider.py            # Singleton repository factory
│   ├── services/                  # Business logic services
│   │   ├── auth_service.py        # Login, logout & session state
│   │   ├── document_service.py    # Document querying & creation
│   │   ├── event_bus.py           # Reactive signal event bus
│   │   ├── notification_service.py# Deadline reminders & user notifications
│   │   ├── ocr_service.py         # Text extraction & NLP suggestion heuristics
│   │   ├── progress_service.py    # Progress updates & deliverables
│   │   ├── routing_service.py     # Routing directives & NLP remark analysis
│   │   └── workflow_service.py    # Workflow transitions & audit logs
│   ├── styles/                    # Visual design & theming
│   │   └── theme.qss              # Master stylesheet (colors, typography, cards)
│   ├── ui/                        # Application window shells
│   │   ├── login.py               # Secure login window with error dialogs
│   │   ├── main_window.py         # Main window container with dynamic stack
│   │   └── sidebar.py             # Role-specialized navigation sidebar
│   ├── main.py                    # Frontend executable entry point
│   ├── requirements.txt           # Frontend Python dependencies
│   └── .env                       # Frontend active configuration
│
├── OCR/                           # PaddleOCR & Rule Heuristics Pipeline
│   ├── ocr.py                     # PaddleOCR wrapper & PDF/Image text extractor
│   ├── rules.py                   # Regex & rule-based metadata extraction engine
│   ├── main.py                    # Combined OCR pipeline runner
│   └── smoke_test.py              # OCR verification test script
│
├── scratch/                       # Test & verification suites
├── main.py                        # Root launcher (launches frontend application)
├── requirements.txt               # Unified project dependencies
├── SETUP_GUIDE.md                 # Complete Windows setup & multi-PC deployment guide
└── README.md                      # This technical documentation
```

---

## 5. Backend Integration

In **API Mode** (`CDTRS_DATA_SOURCE=api`), the desktop application connects to the FastAPI backend service:

- **Local Backend URL:** `http://127.0.0.1:8000/api/v1`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **WebSocket URL:** `ws://127.0.0.1:8000/api/v1/ws`

### Adapter Responsibilities in `APIRepository`:
1. **Dynamic Route Construction:** Automatically handles standard REST paths without path duplication.
2. **Payload Normalization:** Translates camelCase/snake_case and frontend keys to backend schemas (`assigned_to_user_id`, `submitted_by_user_id`, `uploaded_by_user_id`).
3. **Multipart Uploads:** Supports binary file uploads with MIME-type inference and 20 MB size limits.
4. **2-Step Progress Handling:** Submits progress metadata via `POST /documents/{id}/progress` and uploads accompanying deliverable attachments via `POST /documents/{id}/attachments`.
5. **Windows Native SSL Trust:** Uses `pip_system_certs` to inherit Windows native certificate stores, avoiding SSL errors in enterprise environments.

---

## 6. Mock Mode (Offline Development & Testing)

In **Mock Mode** (`CDTRS_DATA_SOURCE=mock`), the application runs entirely in-memory using `MockRepository`.

- **No backend or database connection required.**
- Provides a canonical **5-document demonstration dataset** reflecting diverse workflow states (blank-slate intake, department suggestions, direct staff suggestions, pre-reviewed directives, and urgent deadlines).
- Serves as the behavioral benchmark for frontend testing and UI validation.

---

## 7. User Roles & Workflow

```text
                        ┌──────────────────────────────┐
                        │   Incoming Dispatch / Upload │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │    Director Secretary (DS)   │
                        │    • Intakes & OCR Indexes   │
                        └──────┬────────────────┬──────┘
                               │                │ (If pre-reviewed or direct)
        (Standard Executive)   │                │
                               ▼                │
                 ┌───────────────────────────┐  │
                 │   The Director Review     │  │
                 │   • Enters Director Remark│  │
                 │   • Returns to DS         │  │
                 └─────────────┬─────────────┘  │
                               │                │
                               ▼                │
                 ┌───────────────────────────┐  │
                 │   DS Routes to Dept/Staff │◄─┘
                 └─────────────┬─────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  Head of Department (HOD)   │  │  Direct Employee Assignment │
│  • Delegates to Employee    │  │  • Directly Assigned by DS  │
└──────────────┬──────────────┘  └──────────────┬──────────────┘
               │                                │
               └───────────────┬────────────────┘
                               ▼
                ┌─────────────────────────────┐
                │   Employee Task Execution   │
                │   • Works on deliverable    │
                │   • Submits Progress Update │
                │   • Uploads Attachment      │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │   Progress Follow-up Review │
                │   (DS / Director if needed) │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │      Document Closure       │
                │      • Lifecycle Completed  │
                └─────────────────────────────┘
```

### Advisory Suggestion Banner:
When a document returns to the DS from Director review:
- If the Director remark **explicitly delegates** to a department or staff member (e.g. *"Route to Finance"* or *"Assign to Rahul Sharma"*), the **Yellow Advisory Banner** appears with detected destinations and a one-click direct routing shortcut.
- If the Director writes a **general review** comment without naming a department or employee (e.g. *"Reviewed and approved"*), the yellow banner is suppressed and standard DS options are displayed.

---

## 8. Authentication & Pre-Seeded Accounts

- **Session Management:** Centralized in [`frontend/services/auth_service.py`](file:///c:/CDTRS-master/frontend/services/auth_service.py).
- **JWT Storage:** Access tokens stored securely in memory for API requests.
- **Error Dialogs:** Invalid credentials or network connection failures produce clean `QMessageBox` popups without crashing.

| Role | Department | Username | Default Password | Primary Responsibilities |
|---|---|---|---|---|
| **Director Secretary (DS)** | Administration | `ds_user` | `cdtrs@ds` | Document Ingestion, Initial Routing, Department Delegation, Closure |
| **Director** | Executive | `director` | `cdtrs@director` | Executive Review, Strategic Directives, Returning Remarks |
| **Head of Department (HOD)** | Finance | `hod_finance` | `cdtrs@hod` | Departmental Intake, Task Assignment to Staff |
| **Head of Department (HOD)** | Procurement | `hod_procurement` | `cdtrs@hod` | Departmental Intake, Procurement Delegation |
| **Employee** | Finance | `emp_rahul` | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |
| **Employee** | Procurement | `emp_priya` | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |

---

## 9. Configuration Reference

Configuration is managed via environment variables in [`frontend/config/settings.py`](file:///c:/CDTRS-master/frontend/config/settings.py) and [`backend/.env`](file:///c:/CDTRS-master/backend/.env):

### Frontend Settings (`frontend/.env`):
| Variable | Default Value | Description |
|:---|:---|:---|
| `CDTRS_DATA_SOURCE` | `api` | Data provider mode: `api` (live backend) or `mock` (in-memory) |
| `CDTRS_API_URL` | `http://127.0.0.1:8000/api/v1` | Base URL for REST API communication |
| `CDTRS_API_TIMEOUT` | `15.0` | HTTP request timeout in seconds |
| `CDTRS_APP_NAME` | `CDTRS` | Application title display |
| `CDTRS_APP_VERSION` | `2.0.0` | Application version string |

### Backend Settings (`backend/.env`):
| Variable | Default Value | Description |
|:---|:---|:---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:nmrl@localhost:5432/cdtrs` | PostgreSQL connection string |
| `HOST` | `0.0.0.0` | Host IP binding (`0.0.0.0` for LAN access) |
| `PORT` | `8000` | Port for FastAPI HTTP server |
| `SECRET_KEY` | `cdtrs-super-secret-key-change-in-production-2026` | Secret for signing JWT access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT token lifetime in minutes |
| `MAX_FILE_SIZE` | `20971520` | Maximum file upload size in bytes (20 MB) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## 10. Quick Installation & Launch

For full step-by-step installation instructions including multi-PC deployment across LAN, please refer to:
👉 **[SETUP_GUIDE.md](file:///c:/CDTRS-master/SETUP_GUIDE.md)**

### Quick Start (PowerShell):

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Initialize database & seed test users
python backend/seed.py

# 4. Start Backend Server (Terminal 1)
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 5. Launch Desktop Frontend (Terminal 2)
cd c:\CDTRS-master
.\.venv\Scripts\Activate.ps1
python main.py
```

---

## 11. Testing & Verification

Automated test suites are located in the `scratch/` directory and `OCR/` module:

```powershell
# 1. Verify PaddleOCR engine & Rule heuristics:
python OCR/smoke_test.py

# 2. Verify Canonical 5-Document Dataset & Full Workflow Lifecycles:
python scratch/test_canonical_5_dataset.py

# 3. Verify UI Pages Rendering & Dashboard Assertions:
python scratch/test_ui_pages_canonical.py

# 4. Verify Filters, History & Remark Intelligence Classification:
python scratch/test_user_requested_fixes.py

# 5. Verify Live REST API Adapter:
python scratch/test_api_adapter_integration.py
```

---

## 12. Documentation Map

- **[README.md](file:///c:/CDTRS-master/README.md):** Complete project architecture, workflow overview, and technical reference.
- **[SETUP_GUIDE.md](file:///c:/CDTRS-master/SETUP_GUIDE.md):** Step-by-step Windows setup, multi-PC LAN deployment, and troubleshooting.
- **[DATA_MANAGEMENT_GUIDE.md](file:///c:/CDTRS-master/DATA_MANAGEMENT_GUIDE.md):** Comprehensive real organizational data ingestion, CSV imports, and database management guide.
- **[backend/readme.md](file:///c:/CDTRS-master/backend/readme.md):** Complete backend API specification, Swagger usage, and database schema documentation.
- **[requirements.txt](file:///c:/CDTRS-master/requirements.txt):** Unified Python dependencies for frontend, backend, and OCR modules.
