# CDTRS – Comprehensive Master System Context & Gemini Guide
*Last Updated: 31-08-2026*

---

## 1. Executive Summary & Project Purpose
**CDTRS (Centralised Document Tracking and Routing System)** is an enterprise desktop and server application designed for government/corporate executive offices (Director Secretary, Executive Director, Department HODs, and Assigned Execution Staff).

It provides:
- **Multi-Channel Document Ingestion**: Ingests incoming communications via Microsoft 365 Cloud Graph API, Intranet IMAP/SMTP LAN mail, and manual file uploads.
- **Intelligent Neural OCR**: Extracts textual content, layout, bounding boxes, metadata, and script classifications using PaddleOCR-v3 / PyMuPDF.
- **Advisory Department Routing**: Suggests department and personnel assignments with confidence scoring based on content analysis and prior Director directives.
- **Multi-Department & Delegation Workflows**: Supports single or multi-department assignments, HOD-to-employee task delegation, progress updates with proof attachments, and HOD validation gates.
- **Complete Audit Trail & Immutability**: Full document lifecycle history, optimistic concurrency control, and action escalation reminders.

---

## 2. Technical Stack & Architecture

```text
[ Outlook M365 (Graph API) / Intranet Mail (IMAP/SMTP) / Manual PDF/Img ]
                                 │
                                 ▼
                     [ FastAPI Backend / SQLite DB ]
                     ├── Models (SQLAlchemy ORM + OCC)
                     ├── Neural OCR & Rule Engine (PaddleOCR)
                     ├── Mail Dispatcher & Safety Sandbox
                     └── Dynamic JSON/Excel Seeding
                                 ▲
                                 │ REST APIs + Live WebSockets
                                 ▼
                   [ PySide6 / Qt Desktop Client ]
                     ├── MainWindow & Role-Scoped Sidebar
                     ├── Document Intake & Intelligence Viewer
                     ├── Role Inboxes (DS, Director, HOD, Staff)
                     └── Real-Time Notification Center
```

- **Frontend**: Python 3.10+ • PySide6 (Qt for Python) • Custom responsive QSS theme (`theme.qss`).
- **Backend**: FastAPI • SQLAlchemy ORM • SQLite / PostgreSQL • Pydantic v2 schemas • JWT Authentication • WebSockets.
- **OCR Engine**: PaddleOCR V3 (Neural) with LayoutXLM pipeline and PyMuPDF digital fallback.
- **Mail Engine**: Dual-Channel Provider (Microsoft Graph API for Cloud + IMAP/SMTP for Air-gapped LAN/NIC mail).

---

## 3. Canonical Roles & Permissions

| Role | Code | Primary Responsibilities & UI Features |
|---|---|---|
| **Director Secretary** | `DS` | Document intake queue, OCR validation, initial routing to Director, multi-department dispatch, reminder triggers, final lifecycle closure. |
| **Executive Director** | `DIRECTOR` | Executive review queue, remark annotation, directive guidance, follow-up reviews, performance dashboard. |
| **Head of Department** | `HOD` | Department inbox, task delegation to subordinate staff, HOD validation gating, reminder escalation. |
| **Assigned Employee** | `EMPLOYEE` | Execution task list, progress reporting (percentage, narrative note, proof attachment upload), direct or HOD-gated submission. |

---

## 4. Key Database Entities & Relationships

- **`Document` (`documents`)**: Core lifecycle entity storing `reference_no` (e.g. `CDTRS-2026-0001`), `status`, `current_stage`, `director_remark`, `hod_remark`, `priority`, `deadline`, and optimistic concurrency `version`.
- **`DocumentOCR` (`document_ocr`)**: Stores full raw extracted text, `ocr_engine`, numerical confidence (e.g. `0.9800`), `pages_extracted`, and extraction status.
- **`DocumentAssignment` / `WorkAssignment`**: Stores multi-department routing targets, assigned employee ID, forwarded HOD remark/directives, and `requires_hod_validation` boolean flag.
- **`ProgressUpdate` (`progress_updates`)**: Stores employee progress percentage (0–100%), remarks, validation status (`DIRECT_TO_DS`, `PENDING_HOD_REVIEW`, `HOD_APPROVED`), and submitted proof files.
- **`WorkflowHistory` (`workflow_history`)**: Immutable log recording every transition, user actor, source/destination roles, and timestamp.
- **`Attachment` (`attachments`)**: Stores file metadata, storage paths, and SHA-256 integrity checksums.

---

## 5. Dual Mail & Testing Safety Sandbox

### Mail Channel Configuration (`backend/.env`):
- **`MAIL_CHANNEL=outlook`**: Microsoft 365 Cloud Graph API integration.
- **`MAIL_CHANNEL=intranet`**: Air-gapped LAN / NIC IMAP/SMTP mail server.

### Safe Live Testing Sandbox:
- **`OVERRIDE_TEST_RECIPIENT_EMAIL="pratikshazodge575@gmail.com"`**: Intercepts all outgoing notification/reminder emails across all roles and redirects them safely to the developer's test mailbox. Real staff receive 0 emails during testing. Set to `none` to enable production routing.

---

## 6. Dynamic Seeding & Employee Data Ingestion

- **Central Seed File**: [`backend/data/seed_data.json`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/data/seed_data.json) stores canonical departments and user credentials.
- **Excel / CSV Importer**:
  ```bash
  python backend/import_employees.py employee_roster.xlsx --seed-db
  ```
  Automatically parses employee columns, registers new departments, updates `seed_data.json`, and syncs the database.
- **Database Seeder**:
  ```bash
  python backend/seed.py [--reset]
  ```

---

## 7. Recent Verified UI/UX Improvements (August 2026)

1. **Document Intelligence & OCR Card**: Updated in [`document_viewer.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/frontend/components/document_viewer.py) to display real-time technical extraction diagnostics (Target File, Size, Engine, Status, Confidence %, and Character/Line volume) matching terminal output.
2. **Clean Sidebar**: Transparent user badge background styling eliminated white box artifacts across all roles.
3. **Employee Tasks Cleaned**: Column 5 mapped to "HOD Remark", and task assignment dialog automatically forwards the main HOD remark without redundant text inputs.
4. **Director Review Queue**: Merged "Reviewed Documents" into the main Director Review Queue filter dropdown (`"Reviewed & Returned to DS"`).
5. **Dashboard Performance**: Eliminated blocking loops in Director KPI cards for smooth instant rendering.

---

## 8. Golden Rules for Future Development

1. **Preserve Architecture**: Single role-based application, dynamic role-scoped navigation, reusable viewer and table components.
2. **Preserve Database Concurrency**: Always check optimistic concurrency `version` when updating document status.
3. **Preserve Safe Mail Sandbox**: Never hardcode real recipient addresses without honoring `OVERRIDE_TEST_RECIPIENT_EMAIL`.
4. **Keep UI Decoupled**: UI components interact through services (`frontend/services/`) and API repositories (`frontend/repositories/`).
