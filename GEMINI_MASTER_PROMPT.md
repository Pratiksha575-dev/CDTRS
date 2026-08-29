# 🧠 CDTRS MASTER ARCHITECTURE & AI PROMPT GUIDE
**Centralized Document Tracking and Routing System (CDTRS v2.0)**

---

## 📌 Executive Summary & System Philosophy

**CDTRS** is an enterprise-grade document workflow automation system built for institutional and government governance. It digitizes physical file movement, paper registers, and email daks by providing real-time tracking, intelligent OCR text extraction, automated departmental routing suggestions, and strict role-based execution hierarchies.

### Key Architectural Pillars:
1. **Zero Data Loss & Strict Auditability**: Every document movement, assignment, remark, and status transition is recorded in immutable audit logs.
2. **Dual-Mode Operation**: The PySide6 desktop client seamlessly operates in **Live API Mode** (FastAPI backend + SQLite/PostgreSQL + WebSockets) with automatic failover to **Mock Mode** for offline UI development.
3. **Honest Document Intelligence**:
   - **Digital PDFs**: Extracted in `<50ms` using PyMuPDF / `pypdf` with 100% character fidelity.
   - **Scanned Images / Papers**: Preprocessed with OpenCV and rasterized via PaddleOCR / Tesseract.
   - **Strict Honesty Rule**: If OCR fails or is unreadable, it is honestly marked as `FAILED` with `0.0%` confidence and clean error diagnostics. No fake metadata or default department guesses are ever injected.
4. **Non-Hardcoded Employee Matching**: A suggested employee is ONLY populated if that employee's name appears verbatim in the document text or Director directive. Otherwise, it remains `Not Specified (Open for Assignment)`.
5. **Zero-Touch Startup Seeding**: The backend automatically initializes missing database tables and populates canonical baseline data on startup without requiring manual setup scripts.

---

## 🏢 Organization Structure & Default Accounts

The organization hierarchy is streamlined into **3 Canonical Departments** with **6 Staff Employees** (2 per department):

```
CDTRS Organization Structure:
├── 💰 Finance Department (Code: FIN)
│   ├── HOD: hod_finance (Head of Finance)
│   ├── Staff 1: Rahul Sharma (Accounts Officer) — emp_rahul [EMP-FIN-001]
│   └── Staff 2: Sunil Gupta (Senior Accountant) — emp_sunil [EMP-FIN-002]
├── 👥 HR Department (Code: HR)
│   ├── HOD: hod_hr (Head of Human Resources)
│   ├── Staff 1: Sneha Deshmukh (HR Officer) — emp_sneha [EMP-HR-001]
│   └── Staff 2: Pooja Nair (Establishment Specialist) — emp_pooja [EMP-HR-002]
└── 💻 Technical Department (Code: TECH)
    ├── HOD: hod_tech (Head of Technical & IT)
    ├── Staff 1: Anil Kumar (Systems Engineer) — emp_anil [EMP-TECH-001]
    └── Staff 2: Vikram Malhotra (Network & IT Admin) — emp_vikram [EMP-TECH-002]
```

### 🔑 System User Accounts & Credentials:
| Username | Role | Assigned Department | Default Password | Primary Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| `ds_user` | **DS** *(Director Secretary)* | Executive Ingestion | `cdtrs@ds` | Document intake, manual upload, Outlook sync, initial routing |
| `director` | **DIRECTOR** | Executive Directorate | `cdtrs@director` | Executive review, directive entry, department/staff assignment |
| `hod_finance` | **HOD** | Finance | `cdtrs@hod` | Finance queue management, work assignment to Finance staff |
| `hod_hr` | **HOD** | HR | `cdtrs@hod` | HR queue management, work assignment to HR staff |
| `hod_tech` | **HOD** | Technical | `cdtrs@hod` | Technical queue management, work assignment to Tech staff |
| `emp_rahul` | **EMPLOYEE** | Finance | `cdtrs@emp` | Task execution, progress updates, completion reporting |
| `emp_sunil` | **EMPLOYEE** | Finance | `cdtrs@emp` | Task execution, progress updates, completion reporting |
| `emp_sneha` | **EMPLOYEE** | HR | `cdtrs@emp` | Task execution, progress updates, completion reporting |
| `emp_pooja` | **EMPLOYEE** | HR | `cdtrs@emp` | Task execution, progress updates, completion reporting |
| `emp_anil` | **EMPLOYEE** | Technical | `cdtrs@emp` | Task execution, progress updates, completion reporting |
| `emp_vikram` | **EMPLOYEE** | Technical | `cdtrs@emp` | Task execution, progress updates, completion reporting |

---

## 📂 Repository File & Directory Map

```
CDTRS-master-main/
├── backend/                        # FastAPI REST API, Database & Workflows
│   ├── database.py                 # SQLAlchemy engine, SessionLocal & Base
│   ├── models.py                   # ORM models (Document, User, Department, Employee, OCR, etc.)
│   ├── schemas.py                  # Pydantic v2 validation & response models
│   ├── crud.py                     # Business logic, OCR trigger, AI routing, seeding, audit trails
│   ├── main.py                     # FastAPI application endpoints, lifespan startup hook, WebSockets
│   ├── seed.py                     # Database initialization & clean reset utility (`--reset`)
│   ├── auth/                       # JWT token creation, OAuth2 password hashing
│   └── mail/                       # Microsoft Graph / Outlook & Government Mail sync services
├── frontend/                       # PySide6 (Qt6) Desktop Application
│   ├── main.py                     # Application bootstrap, theme loader, login window
│   ├── config.py                   # API endpoints, feature flags, UI constants
│   ├── api_client.py               # HTTP client with JWT session management
│   ├── components/                 # Reusable Qt widgets & views
│   │   ├── document_viewer.py      # Master multi-tab document viewer & action dialogs
│   │   ├── ocr_dialog.py           # OCR text extraction splash animation dialog
│   │   ├── navigation_bar.py       # Role-aware sidebar navigation
│   │   └── notification_widget.py  # Toast & real-time notification popups
│   ├── pages/                      # Role-specific screens & dashboards
│   │   ├── document_intake.py      # DS Ingestion screen (Manual Upload, Scan, Outlook Sync)
│   │   ├── ds_dashboard.py         # Director Secretary triage & routing dashboard
│   │   ├── director_dashboard.py   # Director executive review & decision dashboard
│   │   ├── hod_dashboard.py        # HOD assignment & department workload dashboard
│   │   ├── employee_dashboard.py   # Employee personal inbox & execution dashboard
│   │   └── analytics_dashboard.py  # SLA compliance, bottlenecks & department analytics
│   ├── repositories/               # Data access abstraction layer
│   │   ├── base_repository.py      # Abstract interface for API / Mock repository
│   │   ├── api_repository.py       # Live REST API implementation
│   │   └── mock_repository.py      # In-memory mock repository for offline development
│   └── services/                   # Frontend domain services
│       ├── document_service.py     # Document creation, retrieval, and status management
│       ├── routing_service.py      # Dynamic department & employee routing service
│       ├── ocr_service.py          # Client-side OCR worker & intake pre-processing
│       └── websocket_service.py    # Background thread for live WebSocket event listening
├── OCR/                            # Dedicated Intelligence & Extraction Engine
│   ├── ocr.py                      # DocumentOCR class (PyMuPDF digital + PaddleOCR neural)
│   ├── rules.py                    # Department keywords, scoring weights, regex field patterns
│   └── paddle_patch.py             # Environment compatibility patch for PaddleOCR v3.x
├── uploads/                        # Uploaded original attachments & scanned PDFs
├── docs/                           # Documentation, SRS, and workflow diagrams
├── requirements.txt                # Pinned production Python dependencies
└── GEMINI_MASTER_PROMPT.md         # This Master AI Context & Architecture Guide
```

---

## 🔄 End-to-End Operational Lifecycle

### 1. Ingestion Phase (`DocumentIntakePage`):
* DS selects a file (`.pdf`, `.docx`, `.png`, `.jpg`).
* `OCRSplashDialog` runs client-side OCR via `frontend/services/ocr_service.py`.
* PyMuPDF extracts digital text; scanned images invoke PaddleOCR.
* The raw text is passed to regex patterns to extract reference numbers, dates, subjects, and sender.
* The intake form auto-populates; DS reviews and submits to `POST /api/v1/intake/manual-upload`.

### 2. Backend Registration & Storage (`backend/main.py`):
* Stores attachment in `uploads/{YEAR}/{DOC_ID}/{FILENAME}` with SHA-256 checksum.
* Creates `models.Document` with status `RECEIVED` and stage `DIRECTOR_SECRETARY`.
* Triggers `crud.trigger_ocr_processing(db, doc_id, intake_ocr_text=ocr_text)`:
  - If OCR succeeds: `ocr_status = COMPLETED`, unified confidence (e.g. `96%`), persists structured fields.
  - If OCR fails: `ocr_status = FAILED`, `confidence = 0.0`, error message saved, no fake metadata.
* Invokes `crud.generate_routing_suggestion(db, doc_id)`:
  - Matches OCR text keywords against `Finance`, `HR`, and `Technical`.
  - Checks if an employee's full name is mentioned verbatim.
  - Generates `models.RoutingSuggestion` and broadcasts WebSocket event `DOCUMENT_CREATED`.

### 3. Review & Routing Phase (`DirectorDashboard` / `HODDashboard`):
* **Normal Workflow**: Document routes to Director -> Director adds remarks -> Routes to HOD -> HOD assigns to specific Staff -> Staff updates progress -> HOD approves -> Director closes.
* **Direct Directive Bypass**: If document already contains a verified Director instruction, DS can bypass Director review directly to the department HOD or assigned Staff.

---

## 🚀 How to Run, Test & Reset

### 1. Reset Database & Uploads to Clean Baseline (0 Documents):
```powershell
python backend/seed.py --reset
```

### 2. Launch Backend API Server (Port 8000):
```powershell
uvicorn backend.main:app --reload --port 8000
```
* Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`

### 3. Launch Frontend Desktop App:
```powershell
python frontend/main.py
```

### 4. Run Test PDF Generation & OCR Verification:
```powershell
python scratch/generate_3_pdfs.py
```

---

## ⚠️ Strict Coding Invariants for AI Agents

When making future modifications to this codebase, you **MUST** adhere to the following architectural rules:

1. **NO Default Employee Hardcoding**:
   - Never auto-assign default employees (e.g. Rahul Sharma) when a department is selected.
   - `suggested_employee` must remain `None` (`Not Assigned`) unless the employee's name was explicitly detected in the document text.
2. **Strict & Honest Error Handling**:
   - Never fake `COMPLETED` status or manufacture fake confidence (e.g. 96%) when OCR extraction fails.
   - On error: status must be `FAILED`, confidence `0.0` / `—`, and raw text must display the genuine error message.
3. **Canonical 3 Departments Only**:
   - The system strictly operates with `Finance`, `HR`, and `Technical`. Never re-introduce `Procurement` or `Maintenance`.
4. **Dynamic Frontend Dropdowns**:
   - Dropdowns must query `repo.get_departments()` and `repo.get_users()` directly from the live database.
5. **Bidirectional Foreign Keys**:
   - Always keep `User.employee_id` and `Employee.user_id` synchronized when creating or updating staff records.
