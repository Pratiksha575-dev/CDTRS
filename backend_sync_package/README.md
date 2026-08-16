# CDTRS Backend Synchronization Package (Golden Reference)

## 📌 Executive Overview

This package contains the **complete, authoritative backend synchronization specification** for the **Centralized Document Tracking and Routing System (CDTRS)**.

The CDTRS desktop application (PySide6) has reached a fully functional, stabilized frontend state running against `MockRepository`. The `MockRepository` implementation embodies all business logic, role-based workflows, delegation models, notification/reminder routing, audit history tracking, and document lifecycle stages required by the system.

**The goal of this package is to enable the backend developer to build, seed, and expose a PostgreSQL database and FastAPI REST API that behaves identically to `MockRepository`, allowing seamless frontend-backend integration without requiring UI or workflow refactoring.**

---

## 📂 Package Directory Structure

```text
backend_sync_package/
│
├── README.md                          # Package overview and guide map (this document)
├── BACKEND_SYNC_GUIDE.md              # Master guide for backend architecture & state sync
├── CANONICAL_USERS.md                 # Complete user directory (DS, Director, 5 HODs, 25 Employees)
├── CANONICAL_DEPARTMENTS.md           # Exact 5 departments, IDs, HOD mappings, and employee rosters
├── CANONICAL_DOCUMENTS.md             # The 5 canonical demonstration documents & initial state
├── CANONICAL_WORKFLOW.md              # Complete state machine, transitions, actions, & bypass logic
├── CANONICAL_AUDIT_HISTORY.md         # Document-centric audit event taxonomy & persistence rules
├── CANONICAL_ASSIGNMENTS.md           # HOD delegation & direct employee assignment rules
├── CANONICAL_REMINDERS.md             # Action reminder resolution engine & recipient targeting
├── CANONICAL_ATTACHMENTS_OCR.md       # Multi-file attachment schema, OCR extraction & intake models
├── API_CONTRACT_REQUIREMENTS.md       # Exact REST API endpoints, schemas, parameters, & responses
├── MOCK_VS_BACKEND_MAPPING.md         # Field-by-field database, API, and frontend model mapping
├── BACKEND_VALIDATION_CHECKLIST.md    # Step-by-step verification checklist for backend readiness
└── DATABASE_SEED_DATA.json            # Machine-readable JSON seed data for PostgreSQL
```

---

## 🎯 How to Use This Package

1. **Database Schema & Seeding**:
   - Review [CANONICAL_DEPARTMENTS.md](CANONICAL_DEPARTMENTS.md) and [CANONICAL_USERS.md](CANONICAL_USERS.md) to set up foreign keys and seed accounts.
   - Use [DATABASE_SEED_DATA.json](DATABASE_SEED_DATA.json) to seed PostgreSQL with the initial 5 demonstration documents and initial audit records.
2. **Workflow & State Machine Implementation**:
   - Follow [CANONICAL_WORKFLOW.md](CANONICAL_WORKFLOW.md) and [CANONICAL_ASSIGNMENTS.md](CANONICAL_ASSIGNMENTS.md) to implement routing transitions, stage updates, and ownership handoffs.
   - Pay special attention to the **Pre-Reviewed Director Remark Bypass** flow in Document 4.
3. **API Implementation**:
   - Follow [API_CONTRACT_REQUIREMENTS.md](API_CONTRACT_REQUIREMENTS.md) to implement or align all REST endpoints with the exact payload and response structures expected by the frontend.
4. **Discrepancy Resolution**:
   - Refer to [MOCK_VS_BACKEND_MAPPING.md](MOCK_VS_BACKEND_MAPPING.md) to resolve column naming differences (e.g., `doc_id` vs `id`, `d_id` vs `department_id`, `priority` color codes vs string labels).
5. **Quality Assurance & Verification**:
   - Execute the test suite outlined in [BACKEND_VALIDATION_CHECKLIST.md](BACKEND_VALIDATION_CHECKLIST.md) to verify authentication, zero-duplication invariants, reminder routing, and audit logs.

---

## 🔒 Core Data Invariants

1. **Zero Document Duplication**: Every document in the system has exactly **one canonical record** identified by a unique integer `id` and unique `reference_no` (e.g. `CDTRS-2026-0001`). Workflow transitions (`DS` → `DIRECTOR` → `HOD` → `EMPLOYEE` → `CLOSED`) **must mutate the existing record in place**, appending audit history events rather than inserting new document records.
2. **Initial State (DS Inbox)**: At initial startup, exactly **5 demonstration documents** exist. All 5 start in stage `DS` with status `Received`, unassigned (`assigned_employee_id = None`), and unrouted (`target_department_id = None`).
3. **Deterministic Reminder Target**: When an action reminder is dispatched, it targets the assigned employee if assigned; otherwise, the HOD of the target department; never both.
