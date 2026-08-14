# CDTRS – Working Context

I am continuing development of my **CDTRS (Centralised Document Tracking and Routing System)** project.

## 1. Project

**Frontend:** Python + PySide6 / Qt Widgets + QSS  
**Backend/database:** Developed separately by my teammate. Frontend currently uses mock data/services and will later integrate with the real backend.

**Roles:**
- Master
- Director
- HOD
- Employee

### Architecture — IMPORTANT

This is **ONE role-based application**, not separate applications for each role.

```text
Login
  ↓
MainWindow(role)
  ↓
Role-based Sidebar
  ↓
Reusable Pages + Components
  ↓
Service Layer
  ↓
Backend/API
```

Do **not** redesign this architecture unnecessarily.

---

# 2. Project Structure

```text
CDTRS/
│
├── main.py
│
├── ui/
│   ├── login.py
│   ├── main_window.py
│   └── sidebar.py
│
├── pages/
│   ├── dashboard.py
│   ├── inbox.py
│   ├── document_intake.py
│   ├── documents.py
│   ├── priority.py
│   ├── history.py
│   └── director_inbox.py
│
├── components/
│   ├── document_table.py
│   ├── document_viewer.py
│   ├── document_preview.py
│   ├── document_info.py
│   ├── workflow_history.py
│   ├── history_table.py
│   └── priority_badge.py
│
├── services/
│   ├── auth_service.py
│   ├── document_service.py
│   ├── ocr_service.py
│   ├── routing_service.py
│   ├── workflow_service.py
│   └── api_client.py
│
├── data/
│   └── mock_data.py
│
└── theme.qss
```

The actual current project may differ slightly. **Never assume a file exists or contains something unless I provide it.**

### Main file responsibilities

| File | Purpose |
|---|---|
| `main.py` | Starts application |
| `ui/login.py` | Login/authentication |
| `ui/main_window.py` | Main window, QStackedWidget, navigation, viewer |
| `ui/sidebar.py` | Role-based sidebar |
| `pages/dashboard.py` | Role-aware dashboard |
| `pages/inbox.py` | Master incoming documents |
| `pages/document_intake.py` | Process document, OCR, routing, forwarding |
| `pages/documents.py` | Documents list/filter/view |
| `pages/priority.py` | Priority/deadline management |
| `pages/history.py` | System-wide history/audit |
| `pages/director_inbox.py` | Documents forwarded to Director |
| `components/document_table.py` | Reusable document table |
| `components/document_viewer.py` | Reusable document viewer |
| `components/document_preview.py` | PDF/image preview |
| `components/document_info.py` | Document metadata |
| `components/workflow_history.py` | History for selected document |
| `services/auth_service.py` | Authentication |
| `services/document_service.py` | Document handling |
| `services/ocr_service.py` | OCR hook |
| `services/routing_service.py` | Routing hook |
| `services/workflow_service.py` | Workflow transitions |
| `services/api_client.py` | Backend API communication |
| `data/mock_data.py` | Mock documents/history |
| `theme.qss` | Application styling |

---

# 3. Current Working Features

## Authentication

- Login
- Role detection
- Logout → Login
- Username and role passed to `MainWindow`

## Navigation

- Role-based Sidebar
- `QStackedWidget`
- Master/Director Inbox routing
- Reusable page structure

## Master

Completed at UI/mock level:

- Dashboard
- Inbox
- Document Intake
- Documents
- Priority / Deadlines
- History / Audit

## Director

Currently implemented:

- Dashboard
- Director Inbox
- Forwarded document reception

## Document Intake

Implemented:

- PDF selection
- PNG/JPG/JPEG selection
- Metadata fields
- OCR section/hook
- Routing suggestion
- Accept Routing
- Save & Forward to Director

## Documents

Implemented:

- Document table
- Status filter
- Department filter
- Source filter
- Clear filters
- View Document
- Document Viewer
- Document-specific workflow history

## Priority / Deadlines

Implemented at mock level:

- Priority filtering
- Status filtering
- View document
- Reminder mock actions

## History / Audit

Implemented at mock level:

- System-wide activity history
- User/action filters
- Document reference
- Workflow details

---

# 4. VERIFIED MASTER → DIRECTOR WORKFLOW

This is currently working and **must not be broken**.

```text
Master
  ↓
Inbox
  ↓
Process Document
  ↓
Document Intake
  ↓
Routing
  ↓
Accept Routing
  ↓
Save & Forward to Director
  ↓
WorkflowService
  ↓
Document state updated
  ↓
Director
  ↓
Inbox
  ↓
Forwarded document appears
```

This has already been debugged and tested successfully.

---

# 5. Important Mock-Data Issue

Some mock Inbox documents currently look like:

```python
{
    "id": 1,
    "title": "Budget Approval Request"
}
```

while canonical documents may look like:

```python
{
    "reference": "CDTRS-2026-001",
    "subject": "Budget Approval Request"
}
```

A temporary matching mechanism exists in `WorkflowService`.

This is only a mock workaround.

### Future requirement

When integrating the real backend, use **one canonical document ID/reference everywhere**.

The same logical document must be used across:

```text
Inbox
Document Intake
Documents
Priority
Viewer
Workflow History
Director Inbox
HOD Inbox
Employee Tasks
Database
```

Do not create more hardcoded mappings such as:

```text
id 1 → CDTRS-2026-001
```

---

# 6. Document Viewer

`DocumentViewer` is reusable.

It should contain:

- Document title
- Reference
- Document preview
- Document information
- Workflow history
- Role-specific actions

Use:

```python
DocumentViewer(document, role)
```

rather than creating separate viewers for every role.

### History distinction

**Document Viewer:**
> History of the selected document only.

**History/Audit page:**
> System-wide activity across documents.

---

# 7. Document Intake

Current UI includes:

### Document

- Preview
- Select Document

Supported frontend file selection:

```text
PDF
PNG
JPG
JPEG
```

### Document Information

- Title
- Date
- Mode
- Source
- Deadline
- Remarks

Modes currently include:

```text
Email
Intranet
Fax
Scanned
Other
```

### OCR

Contains an extracted-text area.

OCR is currently only a service hook/mock.

Future:

```text
File
 ↓
OCR
 ↓
Extracted Text
 ↓
Metadata extraction
 ↓
Master reviews
 ↓
Save
 ↓
Backend/database
```

Do not assume OCR results should be permanently saved before user confirmation.

---

# 8. Routing

Current routing is mocked.

UI contains:

- Suggest Routing
- Department
- Employee
- Confidence
- Accept Routing

Future:

```text
OCR text + metadata
 ↓
Routing service/backend
 ↓
Department
 ↓
Employee
 ↓
Confidence
 ↓
Master review/acceptance
```

Do not invent the final routing algorithm.

---

# 9. Backend Integration

A generic API client exists.

Current base URL:

```text
http://127.0.0.1:8000
```

It provides generic GET/POST/PATCH helpers.

The actual backend is being developed by my teammate.

## VERY IMPORTANT

**Never invent backend endpoints, database fields, request structures, or response structures.**

If backend integration is required and the API contract is unknown, tell me exactly which backend file/API schema I need to get from my teammate.

Preferred architecture:

```text
UI
 ↓
Service
 ↓
API Client
 ↓
Backend
 ↓
Database
```

Do not connect UI directly to the database.

When real backend integration starts, replace mock service implementations rather than unnecessarily rewriting all pages.

---

# 10. External Document Sources

Documents may eventually arrive through:

- Outlook/email
- Intranet
- Fax
- Physical/scanned copies

Do NOT create completely separate frontend workflows for each source.

Preferred architecture:

```text
Outlook / Intranet / Fax / Physical
              ↓
       Backend ingestion
              ↓
       Unified document
              ↓
        Master Inbox
```

The UI should simply display the document source.

---

# 11. Current Limitations

Not finished yet:

1. Director review workflow
2. Director remarks
3. Director decision/actions
4. HOD workflow
5. Employee workflow
6. Real database/backend integration
7. Real OCR
8. Real PDF/image preview and storage
9. Real notifications/reminders
10. Final end-to-end testing

The mock workflow state is also in memory, so it resets when the application restarts.

---

# 12. Known Technical Debt

### Mock document identity

Inbox and canonical `DOCUMENTS` currently have slightly different structures.

This must be unified during backend integration.

### OCR

Currently mocked/hooked into UI.

### Routing

Currently mocked.

### Preview

Currently a placeholder until actual file storage/retrieval is connected.

### Notifications

Reminder actions are currently mock/UI actions.

### Qt warning

A warning has appeared:

```text
QFont::setPointSize: Point size <= 0 (-1)
```

It does not currently block the application. Fix later unless it becomes relevant.

---

# 13. NEXT DEVELOPMENT ORDER

Follow this order unless the SRS/backend requires something different:

```text
1. Director
2. HOD
3. Employee
4. Unify document/workflow data models
5. Backend/database integration
6. OCR integration
7. Real file storage/preview
8. Notifications
9. End-to-end testing
```

## Immediate task: Director Review

Expected general flow:

```text
Director Inbox
 ↓
Select forwarded document
 ↓
View Document
 ↓
Review
 ↓
Director Remark
 ↓
Decision
 ↓
Next workflow stage
```

Do NOT invent exact business actions.

Check the SRS/backend if needed before deciding between:

- Approve
- Reject
- Return
- Forward to HOD
- Other

---

# 14. FILE REQUEST RULE — VERY IMPORTANT

You do **NOT** have access to my local project.

If you need to inspect code:

1. Tell me exactly which files you need.
2. Ask me to paste them.
3. Read ALL provided files before making interconnected changes.
4. Treat the pasted code as the current source of truth.
5. Do not guess unseen code.
6. Ask only for the minimum files needed.

Example:

> Please paste:
> 1. `ui/main_window.py`
> 2. `pages/director_inbox.py`
> 3. `components/document_viewer.py`
> 4. `services/workflow_service.py`

Do not immediately generate code if you need to see the current files first.

---

# 15. Coding Rules

When working on this project:

- Preserve existing working functionality.
- Do not redesign the architecture unnecessarily.
- Make incremental changes.
- Do not rewrite unrelated files.
- Reuse existing components.
- Keep UI separate from services/backend.
- Do not create duplicate role-specific components without a real reason.
- Treat code I paste as the latest version.
- Do not assume older versions still exist.
- If I provide an error/traceback, diagnose the actual error first.
- Ask for missing files rather than guessing.

When I say **"give code"**:

1. Tell me which file to edit.
2. Give the complete code for that file.
3. Keep it compatible with the existing project.
4. Give me a simple test sequence afterward.

---

# 16. How I Want You To Work With Me

Work step-by-step:

```text
I give requirement
 ↓
You tell me which files you need
 ↓
I paste files
 ↓
You inspect them
 ↓
You explain the issue/plan briefly
 ↓
I ask for code
 ↓
You give complete changed file
 ↓
I test
 ↓
I report result/error
 ↓
You continue
```

Do not dump a huge solution immediately.

Do not make assumptions about files you have not seen.

Always preserve the verified:

```text
Master → Document Intake → Forward → Director Inbox
```

workflow.

---

# 17. Core Architecture Principle

The system should ultimately represent:

```text
                    ONE DOCUMENT
                         |
        +----------------+----------------+
        |                |                |
      Master          Director           HOD
        |                |                |
      Intake           Review          Assign
        |                |                |
        +----------------+----------------+
                         |
                     Employee
                         |
                    Completion
                         |
                  SAME DATABASE
                         |
                  WORKFLOW HISTORY
                         |
                     AUDIT LOG
```

The final system should be:

**one role-aware CDTRS application + reusable components + service layer + one consistent backend document/workflow model.**

Do not overcomplicate it.
Do not duplicate the application for every role.
Do not invent backend APIs.
Do not guess unseen code.
Do not break verified workflows.
4)Explain the various tools and methods used in cybercrime, including phishing, password cracking, keyloggers, viruses, worms, and SQL injection. How do these attacks impact individuals and organizations?
1. Define Cybercrime. Explain the origin and evolution of cybercrime.
2. Explain the relationship between Cybercrime and Information Security.
3. Explain the classification of cybercrime with suitable examples.
4. Explain the major types of cybercrime against individuals, organizations, and society.
5. Explain the Indian Information Technology Act, 2000 (ITA 2000) in relation to cybercrime.
6. Discuss the role of ITA 2000 in controlling and preventing cybercrime in India.
7. Explain cybercrime from a global perspective and discuss the major challenges in
combating cybercrime worldwide.
