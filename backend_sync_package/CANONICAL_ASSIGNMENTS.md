# Canonical Work Assignment & Delegation Model

This document specifies the mechanics of department routing, HOD delegation, and direct employee assignments in the CDTRS system.

---

## 1. Assignment Concepts & Distinctions

The system distinguishes between three distinct levels of assignment:

1. **Suggested / Inferred Assignment (Metadata only)**:
   - Extracted by OCR or intake heuristics (`suggested_department_id`, `suggested_employee_id`).
   - Does **not** change operational ownership. The document remains owned by `DS` in the `DS` stage until formally confirmed.
2. **Department / HOD Routing (DS Action)**:
   - DS assigns the document to a department (`target_department_id = dept_id`).
   - `current_stage` becomes `"HOD"`.
   - `status` becomes `"Under HOD Processing"`.
   - `current_owner_id` becomes the HOD's User ID.
   - `assigned_employee_id` is set to `None`.
   - The document appears in that specific HOD's inbox.
3. **Employee Delegation (HOD Action)**:
   - HOD assigns the document to a specific departmental employee (`assigned_employee_id = emp_id`).
   - `current_stage` becomes `"EMPLOYEE"`.
   - `status` becomes `"Assigned for Execution"`.
   - `current_owner_id` becomes the Employee's User ID.
   - A row is inserted into `work_assignments`.
   - The document appears in that employee's "My Tasks" queue.
4. **Direct Staff Routing (DS Action / Pre-Reviewed Bypass)**:
   - DS directly routes the document to an employee, bypassing the HOD.
   - `target_department_id` is set to the employee's department.
   - `assigned_employee_id` is set to `emp_id`.
   - `current_stage` becomes `"EMPLOYEE"`.
   - `status` becomes `"Assigned for Execution"`.
   - `current_owner_id` becomes the Employee's User ID.

---

## 2. Table: `work_assignments`

```sql
CREATE TABLE work_assignments (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    assigned_by_id INTEGER NOT NULL REFERENCES users(id),
    assigned_to_id INTEGER NOT NULL REFERENCES users(id),
    instructions TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);
```

### JSON / API Representation:
```json
{
  "id": 1,
  "document_id": 1,
  "assigned_by_id": 4,
  "assigned_by_name": "Procurement HOD",
  "assigned_to_id": 201,
  "assigned_to_name": "Priya Verma",
  "instructions": "Execute compliance verification against statutory guidelines.",
  "is_active": true,
  "created_at": "2026-08-16 11:15"
}
```

---

## 3. Operational Ownership Matrix

| Operational Event | `target_department_id` | `assigned_employee_id` | `current_stage` | `current_owner_id` | Document Appears In |
|:---|:---:|:---:|:---:|:---:|:---|
| **Intake Ingestion** | `None` | `None` | `DS` | User `1` (DS) | DS Documents Table |
| **Route to Director** | `None` | `None` | `DIRECTOR` | User `2` (Director) | Director Inbox |
| **Director Return to DS** | `None` | `None` | `DS` | User `1` (DS) | DS Documents Table |
| **DS Routes to Finance HOD** | `1` | `None` | `HOD` | User `3` (Finance HOD) | Finance HOD Inbox |
| **Finance HOD Assigns Rahul** | `1` | `101` | `EMPLOYEE` | User `101` (Rahul Sharma) | Rahul Sharma My Tasks |
| **DS Direct Route to Priya** | `2` | `201` | `EMPLOYEE` | User `201` (Priya Verma) | Priya Verma My Tasks |
| **Document Closed** | Retained | Retained | `CLOSED` | User `1` (DS) | Closed Archive |
