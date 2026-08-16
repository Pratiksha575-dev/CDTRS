# Centralised Document Tracking and Routing System (CDTRS)

**CDTRS** is an enterprise-grade desktop document workflow, routing, and lifecycle tracking system built with **Python**, **PySide6 (Qt 6 Widgets)**, and modern layered architecture. 

It provides an end-to-end operational pipeline for intake, executive review, departmental delegation, execution tracking, and audit logging across administrative organizations.

---

## 1. Project Overview

In large organizations, official communications, policy directives, inter-departmental notices, and procurement sanctions move across multiple administrative tiers. Physical handling or ad-hoc emails often result in lost accountability, missed deadlines, and lack of traceability.

CDTRS solves this by establishing a unified, role-based desktop interface with real-time lifecycle tracking, deadline monitoring, and clear delegation paths.

### Primary User Roles:
- **Director Secretary (DS):** Handles document intake (scans, emails, dispatches), metadata extraction (OCR/NLP hints), executive routing to the Director, departmental routing to HODs or staff, action reminders, and final document closure.
- **The Director:** Performs executive reviews, reviews follow-ups, records administrative instructions/remarks, and returns documents to the DS for execution.
- **Head of Department (HOD):** Manages departmental workload, delegates actionable documents to specific department employees, monitors task progress, and submits progress updates.
- **Department Employee:** Receives direct task assignments, manages assigned deliverables, uploads attachments, and submits structured progress reports.

---

## 2. Current Project Status

The CDTRS desktop frontend is fully developed, tested, and integrated:

- **Desktop UI & Theming:** Complete PySide6 graphical interface with custom QSS typography, KPI metric tiles, and operational action cards.
- **Pluggable Repository Architecture:** Supports both **Live REST API Mode** (connecting to the FastAPI cloud backend) and **Mock Mode** (in-memory demonstration dataset).
- **Authentication & Role-Based Shell:** Central login window with JWT session management, role-based sidebars, and clean user error dialogs.
- **Document Intake & OCR Intelligence:** Dual intake pipeline (queue dispatches or physical file uploads) with OCR text extraction, pre-reviewed directive detection, and automated department/employee suggestions.
- **Advisory Routing Intelligence:** Context-aware suggestion banner that detects explicit delegation targets in Director remarks without unauthorized auto-routing.
- **Departmental Delegation & Progress Workflow:** Full task assignment workflow, 2-step progress updates, and multipart file attachment handling.
- **Deadlines & Action Reminders:** High-priority tracking, 7-day cutoff filters, overdue warnings, and downstream reminder dispatch.
- **Workflow History & Audit Trail:** Chronological document-centric timeline recording all lifecycle actions, actors, timestamps, and remarks.

---

## 3. Architecture

CDTRS is built on a clean **layered repository architecture** ensuring strict separation of concerns between user interface, business logic, domain modeling, and data transport.

```text
┌─────────────────────────────────────────────────────────────┐
│                    UI & Presentation Layer                  │
│       ui/ (LoginWindow, MainWindow, Sidebar)                │
│       pages/ (Dashboard, Inbox, Intake, Documents, History)  │
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
│  FastAPI Cloud Backend       │                              │
│  (https://cdtrs.onrender.com)│                              │
└──────────────────────────────┴──────────────────────────────┘
```

### Why This Separation Matters:
- **Repository-Agnostic UI:** UI components and services communicate exclusively with the `BaseRepository` interface. Switching between live cloud API mode and local offline Mock mode requires zero changes to the UI or business logic.
- **Robust Adapter Pattern:** `APIRepository` cleanly handles REST serialization, multipart uploads, route code translation, and backend aliases without leaking backend implementation details into the presentation layer.

---

## 4. Frontend Structure

```text
CDTRS/
├── api/                       # REST API client & networking
│   ├── client.py              # HTTP client with Windows SSL support (pip_system_certs)
│   ├── endpoints.py           # Centralized REST route constants (/api/v1/...)
│   └── exceptions.py          # Structured API error hierarchy
│
├── backend/                   # FastAPI backend source code & schemas
│   ├── crud.py                # Database operations & routing intelligence
│   ├── database.py            # SQLAlchemy database engine & session maker
│   ├── main.py                # FastAPI endpoints & middleware
│   ├── models.py              # SQLAlchemy database ORM models
│   └── schemas.py             # Pydantic request/response schemas
│
├── components/                # Reusable PySide6 UI widgets
│   ├── document_info.py       # Metadata information panel
│   ├── document_preview.py    # Document content & attachment preview
│   ├── document_table.py      # Standard registered documents table
│   ├── document_viewer.py     # Document viewer with actions & routing banner
│   ├── priority_badge.py      # High/Medium/Low colored status badges
│   ├── routing_dialogs.py     # Route to Director, HOD, and Staff dialogs
│   └── state_widgets.py       # Empty state & loading illustrations
│
├── config/                    # Configuration management
│   └── settings.py            # Environment variable parsing & settings dataclass
│
├── models/                    # Data models & Enums
│   ├── attachment.py          # DocumentAttachment domain model
│   ├── document.py            # DocumentModel domain model
│   ├── enums.py               # RoleEnum, DocumentStatusEnum, PriorityEnum, etc.
│   ├── progress_update.py     # ProgressUpdateModel domain model
│   ├── user.py                # UserModel domain model
│   ├── work_assignment.py     # WorkAssignmentModel domain model
│   └── workflow_event.py      # WorkflowEventModel audit event model
│
├── pages/                     # Application pages
│   ├── dashboard.py           # Role-specific operational dashboards
│   ├── director_inbox.py      # Director executive review queue
│   ├── director_reviewed.py   # Director reviewed documents archive
│   ├── document_intake.py     # Registration & OCR text extraction form
│   ├── documents.py           # Central searchable repository with filters
│   ├── employee_tasks.py      # Employee active tasks & progress submissions
│   ├── history.py             # System audit trail & chronological timeline
│   ├── hod_inbox.py           # Departmental tasks & staff delegation
│   └── inbox.py               # DS raw incoming dispatches queue
│
├── repositories/              # Data access adapters
│   ├── api_repository.py      # Live REST API implementation
│   ├── base.py                # BaseRepository abstract interface
│   ├── mock_repository.py     # Standalone in-memory golden reference repository
│   └── provider.py            # Singleton repository factory
│
├── services/                  # Business logic services
│   ├── auth_service.py        # Login, logout & session state
│   ├── document_service.py    # Document querying & creation
│   ├── event_bus.py           # Reactive signal event bus
│   ├── notification_service.py# Deadline reminders & user notifications
│   ├── ocr_service.py         # Text extraction & NLP suggestion heuristics
│   ├── progress_service.py    # Progress updates & deliverables
│   ├── routing_service.py     # Routing directives & NLP remark analysis
│   └── workflow_service.py    # Workflow transitions & audit logs
│
├── styles/                    # Visual design & theming
│   └── theme.qss              # Master stylesheet (colors, typography, cards)
│
├── ui/                        # Application window shells
│   ├── login.py               # Secure login window with error dialogs
│   ├── main_window.py         # Main window container with dynamic stack
│   └── sidebar.py             # Role-specialized navigation sidebar
│
├── scratch/                   # Automated test scripts & verification suites
├── main.py                    # Application launch entry point
├── requirements.txt           # Python package requirements
├── SETUP_GUIDE.md             # Complete step-by-step Windows setup guide
└── README.md                  # This technical overview document
```

---

## 5. Backend Integration

In **API Mode** (`CDTRS_DATA_SOURCE=api`), the desktop application connects to the deployed FastAPI cloud backend:

- **Live Render Backend URL:** `https://cdtrs.onrender.com/api/v1`
- **Health Check Endpoint:** `https://cdtrs.onrender.com/health`

### Adapter Responsibilities in `APIRepository`:
1. **Dynamic Route Construction:** Automatically handles standard REST paths without path duplication.
2. **Payload Normalization:** Translates camelCase/snake_case and frontend keys to backend schemas (`assigned_to_user_id`, `submitted_by_user_id`, `uploaded_by_user_id`).
3. **Multipart Uploads:** Supports binary file uploads with MIME-type inference (`application/pdf`, `image/png`, `application/msword`).
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

## 8. Authentication

- **Session Management:** Centralized in `services.auth_service`.
- **JWT Storage:** Access tokens stored securely in memory for API requests.
- **Error Dialogs:** Invalid credentials or network connection failures produce clean `QMessageBox` popups without crashing.
- **Safe Session Cleanup:** Logging out clears the current user session and disconnects background event handlers before returning to the login window.

---

## 9. Document Management Features

- **DS Raw Inbox (`pages/inbox.py`):** Unprocessed incoming dispatches awaiting metadata registration.
- **Document Processing / Intake (`pages/document_intake.py`):** Structured form with file preview, OCR extraction, priority selection, deadline picker, and bypass checks.
- **Registered Documents Repository (`pages/documents.py`):** Search by keyword, filter by status, priority, department, or 7-day deadlines, and send action reminders.
- **Document Details Viewer (`components/document_viewer.py`):** Comprehensive view showing metadata, status badges, OCR text, remarks history, progress updates, attached files, and role-appropriate action buttons.
- **Workflow History & Audit Trail (`pages/history.py`):** Chronological timeline of all system events organized by document card with role filtering and full-text search.

---

## 10. Role-Specific Dashboards

- **Director Secretary:** Operational overview showing *New Incoming*, *Awaiting Director Review*, *Returned by Director*, *Under HOD Processing*, *Progress Updates*, and *Closed Documents*, along with actionable shortcut cards.
- **Director:** Executive overview showing *Awaiting Initial Review*, *Progress Follow-ups*, *Total Reviewed*, and *Critical Priority*.
- **HOD:** Departmental overview showing *Awaiting Employee Assignment*, *Assigned / In Progress*, *Progress Updates Received*, and *Critical Priority*.
- **Employee:** Personal workload overview showing *Active Assigned Tasks*, *New / Pending Progress*, and *Progress Updates Submitted*.

---

## 11. Configuration Reference

Configuration is managed via environment variables in [config/settings.py](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/config/settings.py):

| Variable | Default Value | Description |
|:---|:---|:---|
| `CDTRS_DATA_SOURCE` | `api` | Data provider mode: `api` (live backend) or `mock` (in-memory) |
| `CDTRS_API_URL` | `https://cdtrs.onrender.com/api/v1` | Base URL for REST API communication |
| `CDTRS_API_TIMEOUT` | `15.0` | HTTP request timeout in seconds |
| `CDTRS_APP_NAME` | `CDTRS` | Application title display |
| `CDTRS_APP_VERSION` | `2.0.0` | Application version string |

---

## 12. Quick Installation & Setup

For complete, step-by-step Windows installation instructions, please refer to:
👉 **[SETUP_GUIDE.md](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/SETUP_GUIDE.md)**

### Quick Start (PowerShell):
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Launch application
python main.py
```

---

## 13. Running the Application

The executable entry point for the desktop application is:
```powershell
python main.py
```

---

## 14. Testing & Verification

Automated test suites are located in the `scratch/` directory:

```powershell
# 1. Verify Canonical 5-Document Dataset & Full Workflow Lifecycles:
python scratch/test_canonical_5_dataset.py

# 2. Verify UI Pages Rendering & Dashboard Assertions:
python scratch/test_ui_pages_canonical.py

# 3. Verify Filters, History & Remark Intelligence Classification:
python scratch/test_user_requested_fixes.py

# 4. Verify Live REST API Adapter (22 API operations):
python scratch/test_api_adapter_integration.py
```

---

## 15. Dependencies

All third-party package requirements are specified in **[requirements.txt](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/requirements.txt)**:
- `PySide6` (GUI framework)
- `requests` (HTTP client)
- `pip_system_certs` (Windows SSL certificate trust)
- `python-dotenv` (Configuration)
- `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `python-jose`, `passlib`, `bcrypt`, `python-multipart` (Backend modeling & integration testing)

---

## 16. Development Principles

1. **Keep UI Layer Decoupled:** UI components must never make raw HTTP calls or query databases directly. All interactions go through `services` and `BaseRepository`.
2. **Preserve Mock Reference:** `MockRepository` is the golden behavioral standard. Always ensure mock mode tests pass alongside API mode tests.
3. **No Hardcoded Endpoints in Pages:** API routes are centralized in `api/endpoints.py`.
4. **Never Commit Virtual Environments:** `.venv/`, `__pycache__/`, and `.env` files are strictly excluded via `.gitignore`.

---

## 17. Recommended Development Workflow

1. Download/clone repository into a clean directory.
2. Set up virtual environment and install `requirements.txt`.
3. Test in **Mock Mode** (`$env:CDTRS_DATA_SOURCE="mock"`) for offline UI/workflow feature development.
4. Test in **API Mode** (`$env:CDTRS_DATA_SOURCE="api"`) against the Render backend.
5. Run the automated test suite before distributing updates.

---

## 18. Documentation Map

- **[README.md](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/README.md):** Complete project architecture, workflow overview, and technical reference.
- **[SETUP_GUIDE.md](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/SETUP_GUIDE.md):** Step-by-step Windows setup, installation, troubleshooting, and execution guide.
- **[requirements.txt](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/requirements.txt):** Python package dependencies.
