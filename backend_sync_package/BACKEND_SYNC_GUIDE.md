# CDTRS Master Backend Synchronization Guide

## 1. System Architecture & Integration Model

The Centralized Document Tracking and Routing System (CDTRS) is built on a decoupled architecture:

```text
+-----------------------------------------------------------------------------------+
|                                CDTRS FRONTEND                                     |
|  PySide6 Desktop Application (Pages, Tables, KPI Dashboards, Document Viewer)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              SERVICE LAYER                                        |
|  DocumentService, RoutingService, AssignmentService, NotificationService, etc.    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            REPOSITORY PROVIDER                                    |
|   repositories.provider.get_repository() -> MockRepository / APIRepository        |
+-----------------------------------------------------------------------------------+
          |                                                       |
          | (Dev / Golden Reference)                              | (Production API)
          v                                                       v
+-----------------------+                               +---------------------------+
|    MockRepository     |                               |      APIRepository        |
|  In-memory data store |                               |    HTTP REST Client       |
+-----------------------+                               +---------------------------+
                                                                  |
                                                                  v  JSON / HTTP
                                                        +---------------------------+
                                                        |      FastAPI BACKEND      |
                                                        +---------------------------+
                                                                  |  SQLAlchemy
                                                                  v
                                                        +---------------------------+
                                                        |    PostgreSQL DATABASE    |
                                                        +---------------------------+
```

### The Role of MockRepository
`MockRepository` serves as the **Golden Reference Specification** for:
- Role permissions and inbox filtering.
- State transitions (`current_stage`, `status`, `current_owner_id`).
- Workflow audit history generation.
- Reminder recipient resolution.
- OCR metadata inference.
- Attachment relationships.

The backend API and database must replicate the exact data schemas, state machine behaviors, and response formats defined in `MockRepository`.

---

## 2. Canonical Initial State (The 5 Demonstration Documents)

At initial system deployment / startup, exactly **5 demonstration documents** must exist in the database.

All 5 documents initially start in the **DS Inbox**:
- `current_stage` = `"DS"`
- `status` = `"Received"`
- `current_owner_id` = `1` (`"Director Secretary"`)
- `target_department_id` = `None` (No formal routing has taken place)
- `assigned_employee_id` = `None` (No formal assignment has taken place)

### The 5 Purposeful Document Personas:
1. **Document 1 (`CDTRS-2026-0001`) — Fresh / Normal Workflow**:
   - Blank slate. No suggested department, no suggested employee, no prior remarks, no deadline.
   - Purpose: Demonstrates the full multi-hop normal workflow: DS → Director Review → DS → HOD Routing → Employee Assignment → Progress Submission → Follow-up to Director → DS Closure.
2. **Document 2 (`CDTRS-2026-0002`) — Department Suggestion**:
   - High priority with a suggestion for `Finance`.
   - Purpose: Demonstrates DS accepting/overriding department routing suggestions and routing to the Finance HOD.
3. **Document 3 (`CDTRS-2026-0003`) — Department + Employee Suggestion**:
   - High priority with suggestions for `Finance` and employee `Rahul Sharma`.
   - Purpose: Demonstrates direct routing to an identified employee and action reminder dispatching.
4. **Document 4 (`CDTRS-2026-0004`) — Pre-Reviewed / Director Remark Bypass**:
   - Physical / scanned dispatch with a pre-existing Director remark: *"Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."*
   - Purpose: Demonstrates the **Director Review Bypass** flow where DS can route directly to the designated employee/department without sending to the Director first.
5. **Document 5 (`CDTRS-2026-0005`) — Urgent / Deadline Tracking**:
   - High priority with a strict target deadline (+7 days from current date).
   - Purpose: Demonstrates deadline filters, overdue badges, and Technical (IT) HOD routing.

---

## 3. The Core Data Identity Invariant

> [!IMPORTANT]
> **There must be exactly ONE registered database record per document reference.**

- When Document 1 (`CDTRS-2026-0001`) transitions from `DS` to `DIRECTOR`, the backend **must execute an `UPDATE` on the existing row in the `documents` table**.
- It must **NEVER execute an `INSERT`** of a new document row for state changes.
- At all times:
  ```sql
  SELECT COUNT(*) FROM documents; -- MUST BE 5 initially
  SELECT COUNT(DISTINCT reference_no) FROM documents; -- MUST EQUAL COUNT(*)
  ```

---

## 4. Digital Incoming Queue vs. Registered Documents

The system separates incoming dispatches into two logical states:

1. **Digital Incoming Queue (`_inbox_documents`)**:
   - Represents incoming communications (raw emails, faxes, portal dispatches) that have arrived at the intake desk but have not yet been registered or processed.
   - Accessed via `GET /documents/inbox`.
2. **Registered Workflow Documents (`_documents`)**:
   - Represents canonical documents active in the tracking workflow.
   - Accessed via `GET /documents`.
3. **Intake Processing**:
   - When DS processes an incoming item via `POST /documents`, the document is registered in the `documents` table and **purged from the incoming inbox queue** (`DELETE /documents/inbox/{id}`).

---

## 5. Audit History & Event Append Model

Audit history is strictly additive. Every lifecycle action appends a row to the `workflow_history` table:

```sql
INSERT INTO workflow_history (document_id, action, from_role, to_role, remarks, performed_by, created_at)
VALUES (1, 'Routed to Director', 'DS', 'Director', 'Forwarded for Executive Review', 1, NOW());
```

A document's full lifecycle timeline is retrieved via `GET /documents/{document_id}/history` and rendered chronologically in the UI audit log.
