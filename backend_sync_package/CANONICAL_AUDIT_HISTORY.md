# Canonical Audit History & Event Taxonomy

This document specifies the exact structure, event types, actor roles, and persistence rules for the document audit trail.

---

## 1. Audit Event Data Model

Each event in the audit trail is linked to a single document via `document_id` and represents an immutable chronological event.

### Database Table: `workflow_history`
```sql
CREATE TABLE workflow_history (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    from_role VARCHAR(50),
    to_role VARCHAR(50),
    remarks TEXT,
    details TEXT,
    performed_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);
```

### JSON / API Representation:
```json
{
  "id": 1,
  "document_id": 1,
  "action": "Routed to Director",
  "from_role": "DS",
  "to_role": "Director",
  "remarks": "Forwarded for Executive Review",
  "details": null,
  "performed_by": 1,
  "performed_by_name": "Director Secretary",
  "created_at": "2026-08-16 09:30"
}
```

---

## 2. Complete Event Action Taxonomy

| Action Identifier | Triggering Operation | Performed By | `from_role` | `to_role` | Standard Remark Format |
|:---|:---|:---:|:---:|:---:|:---|
| `Document Ingested` | Document registered at intake desk | DS (ID: 1) | `DS` | *None* | `"Document {ref_no} registered into repository."` |
| `Routed to Director` | DS routes document to Director | DS (ID: 1) | `DS` | `Director` | `"Forwarded for Executive Review"` or custom note |
| `Director Remark Recorded` | Director inputs directive | Director (ID: 2) | `Director` | `Director` | `"Directive: \"{remark_text}\""` |
| `Returned to DS` | Director completes review | Director (ID: 2) | `Director` | `DS` | `"Director review completed. Returned to DS for operational dispatch."` |
| `Routed to HOD` | DS routes to Department HOD | DS (ID: 1) | `DS` | `HOD` | `"Routed to {department_name} HOD for execution."` |
| `Directly Assigned to Staff` | DS bypasses HOD and routes to staff | DS (ID: 1) | `DS` | `Employee` | `"Directly assigned to {employee_name} ({department_name})."` |
| `Assigned to Employee` | HOD delegates task to team member | HOD (ID: 3-7) | `HOD` | `Employee` | `"Assigned to {employee_name}: {instructions}"` |
| `Progress Updated` | Employee submits note or attachment | Employee (101-505) | `Employee` | `Employee` | `"Progress submitted by {employee_name}: \"{description}\""` |
| `Follow-up Sent to Director` | DS escalates completed progress to Director | DS (ID: 1) | `DS` | `Director` | `"Follow-up progress forwarded for Director endorsement."` |
| `Document Closed` | DS marks document finalized | DS (ID: 1) | `DS` | *None* | `"Document finalized and closed by Director Secretary."` |
| `Action Reminder Sent` | DS dispatches reminder notice | DS (ID: 1) | `DS` | `HOD` or `Employee` | `"Reminder dispatched to {user_name} ({role})."` |

---

## 3. History Persistence Invariant
- **Single Continuous Stream**: A document retains its entire history from ingestion to closure.
- **No Fragmentation**: Transitioning across stages (`DS` → `DIRECTOR` → `HOD` → `EMPLOYEE` → `CLOSED`) must **never wipe, truncate, or duplicate history records**.
- **Immutable Timestamps**: History records must never be modified or deleted during standard workflow execution.
