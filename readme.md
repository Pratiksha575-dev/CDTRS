# CDTRS Frontend – Project Status & Development README

## 1. Project Overview

**CDTRS (Centralised Document Tracking and Routing System)** is a role-based document management and workflow system.

The frontend is being developed using:

- Python
- PySide6 / Qt Widgets
- QSS

The backend and database are being developed separately by the teammate. The current frontend uses mock data and service-layer placeholders so that real backend/OCR integration can be added later.

The system is designed for four main roles:

- Master
- Director
- HOD
- Employee

The application uses **one common role-based interface**, rather than separate applications for every role.

---

## 2. Current Frontend Structure

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
│   └── history_table.py
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

### Main responsibilities

- `main.py` – starts the application.
- `ui/login.py` – login and authentication.
- `ui/main_window.py` – main window, role-based navigation and page routing.
- `ui/sidebar.py` – role-based sidebar.
- `pages/` – complete application pages for different workflow stages.
- `components/` – reusable document, table, viewer and history components.
- `services/` – authentication, document, OCR, routing, workflow and API logic.
- `data/mock_data.py` – temporary mock documents and workflow data.
- `theme.qss` – application styling.

---

# 3. Completed So Far

## Authentication & Navigation

- Login screen
- Role-based login
- Master and Director dashboards
- Logout
- Role-based sidebar
- Page navigation using `QStackedWidget`

## Master Module

The following pages are implemented:

### Dashboard
Role-aware Master dashboard.

### Inbox
Displays incoming documents and provides a **Process Document** action.

### Document Intake
Implemented:

- Document selection
- PDF / PNG / JPG / JPEG support
- Document preview area
- Document information form
- Source/mode selection
- Deadline and remarks fields
- OCR extracted-text section
- Routing suggestion
- Department/employee/confidence display
- Accept Routing
- Save & Forward to Director

### Documents
Implemented:

- Document table
- Status filtering
- Department filtering
- Source filtering
- Clear filters
- View Document

### Document Viewer
Reusable viewer containing:

- Document title/reference
- Document preview area
- Document information
- Workflow history
- Role-based viewer support

### Priority / Deadlines
Implemented:

- Priority/deadline listing
- Filters
- View document
- Reminder-related mock actions

### History / Audit
Implemented:

- System-wide activity history
- User/action filtering
- Document references
- Workflow activity information

---

# 4. Master → Director Workflow

The most important cross-role workflow currently works:

```text
Master
   ↓
Master Inbox
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
Workflow Service
   ↓
Document state updated
   ↓
Director
   ↓
Director Inbox
   ↓
Forwarded document appears
```

This confirms that the frontend can already represent a document moving from one role to another.

---

# 5. Director Module – Current Status

Currently implemented:

- Director login
- Director dashboard
- Director Inbox
- Reception of documents forwarded by Master
- Shared Document Viewer foundation

### Still required

Director needs the actual review workflow:

```text
Director Inbox
      ↓
Open Document
      ↓
Review
      ↓
Add Director Remark
      ↓
Decision
      ↓
Next Workflow Stage
```

The exact decision actions must follow the project/SRS requirements and backend workflow.

---

# 6. HOD & Employee – Pending

These modules have not yet been completed.

### HOD

Planned:

- HOD Dashboard
- HOD Inbox
- Document review
- Remarks
- Employee assignment
- Workflow/status updates
- History

### Employee

Planned:

- Employee Dashboard
- Assigned documents/tasks
- Document viewing
- Work/update actions
- Completion/submission
- History

---

# 7. OCR & Document Processing

OCR is **not yet actually integrated**.

The frontend already contains an OCR service hook and an Extracted Text section.

Intended workflow:

```text
Incoming PDF/Image
       ↓
OCR
       ↓
Extracted Text
       ↓
Metadata / information extraction
       ↓
Master reviews
       ↓
Save
       ↓
Database
```

Actual OCR engine/service and extraction logic are still pending.

---

# 8. Document Sources

The system is intended to handle documents arriving through multiple sources, such as:

- Outlook / Email
- Intranet
- Fax
- Physical/scanned documents

The frontend is designed around **one unified document workflow**, regardless of source.

The source is stored/displayed as document metadata.

Actual Outlook, intranet, fax and ingestion integrations are pending backend implementation.

---

# 9. Routing

Routing is currently a mock/service placeholder.

The current UI supports:

- Suggest Routing
- Department
- Employee
- Confidence
- Accept Routing

Future routing will use document/OCR information to suggest the appropriate department/employee through the actual backend/service.

---

# 10. Database & Backend Integration

The frontend has a service/API structure prepared for backend integration.

Current API client uses:

```text
http://127.0.0.1:8000
```

with generic GET/POST/PATCH support.

Most current data is still mock data.

### Pending backend integration

Replace mock implementations with actual backend calls for:

- Authentication
- Documents
- Inbox
- Workflow transitions
- Assignments
- History/Audit
- OCR
- File storage
- Notifications

The frontend should communicate through the service/API layer rather than directly accessing the database.

---

# 11. Current Mock Data Issue

There is currently some inconsistency between mock document structures.

For example, one part may use:

```python
{"id": 1, "title": "Budget Approval Request"}
```

while another uses:

```python
{"reference": "CDTRS-2026-001", "subject": "Budget Approval Request"}
```

A temporary matching mechanism was added so the Master → Director workflow can work.

This should be cleaned up during backend integration by using **one canonical document ID/reference** across the entire system.

The same document should be shared by:

```text
Inbox
Document Intake
Documents
Priority
Document Viewer
Workflow History
Director Inbox
HOD
Employee
Database
```

---

# 12. Workflow History

Two levels of history are currently represented.

### Document Workflow History

Shown inside the Document Viewer.

It represents the history of **that selected document only**.

Example:

```text
Document received
Master processed
Routing accepted
Forwarded to Director
Director reviewed
...
```

### System History / Audit

Shown in the History page.

It represents activities across multiple documents/users and can be filtered.

Eventually both should use the backend's workflow/audit data.

---

# 13. Current Technical Limitations

The following are still mock or incomplete:

- Real database persistence
- Real OCR
- Real document storage
- Real PDF/image preview
- Real routing logic
- Real notifications/reminders
- Outlook/intranet/fax ingestion
- Director decision workflow
- HOD workflow
- Employee workflow
- Final end-to-end testing

Mock workflow state currently exists in application memory, so it is not persistent across application restarts.

---

# 14. Recommended Next Development Steps

Development should continue in this order:

### Phase 1 – Director

1. Complete Director Inbox
2. Open forwarded document
3. Director review UI
4. Director remark
5. Correct decision actions according to SRS
6. Update workflow history
7. Forward to next stage

### Phase 2 – HOD

1. HOD Dashboard
2. HOD Inbox
3. Review
4. Remarks
5. Assignment to Employee
6. Workflow updates

### Phase 3 – Employee

1. Employee Dashboard
2. My Tasks
3. Document view
4. Work/update
5. Completion
6. History

### Phase 4 – Data Model

Unify the document and workflow models so the entire application uses one canonical document identity.

### Phase 5 – Backend Integration

Connect the existing service layer to the teammate's actual backend/database.

### Phase 6 – OCR & External Services

Integrate:

- OCR
- File storage
- PDF/image preview
- Outlook/intranet/fax ingestion
- Notifications/reminders

### Phase 7 – Final Testing

Test the complete workflow:

```text
Document Received
      ↓
Master
      ↓
Director
      ↓
HOD
      ↓
Employee
      ↓
Completion
      ↓
History / Audit
```

---

# 15. Overall Current Status

```text
Authentication & Navigation     ✅ Complete
Master UI                       ✅ Mostly Complete
Document Intake                 ✅ UI Complete / Services Mock
Documents & Viewer              ✅ Complete at Mock Level
Priority / Deadlines             ✅ UI Complete / Actions Mock
History / Audit                 ✅ UI Complete / Data Mock
Master → Director Workflow      ✅ Working
Director Review                 🔄 Next
HOD Workflow                    ⏳ Pending
Employee Workflow               ⏳ Pending
Database Integration            ⏳ Pending
OCR Integration                 ⏳ Pending
External Ingestion              ⏳ Pending
Notifications                   ⏳ Pending
Final Testing                   ⏳ Pending
```

## Current Project State

The frontend foundation and primary Master workflow are established. The application can already demonstrate a document being received by Master, processed, routed and forwarded to Director.

The immediate goal is to complete the **Director → HOD → Employee workflow**, then replace mock services with the teammate's real backend/database and integrate OCR, document storage and external document sources.
