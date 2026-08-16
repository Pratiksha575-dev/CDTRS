# Canonical Reminder & Notification Engine

This document defines the resolution rules, recipient targeting, and notification dispatching behavior for document action reminders.

---

## 1. Reminder Recipient Resolution Engine

The frontend uses a deterministic resolution algorithm (`NotificationService.resolve_reminder_recipient`) to determine the single authoritative downstream recipient for an action reminder.

```text
                                [ Document Reminder Triggered ]
                                               |
                                               v
                                    Is Document CLOSED?
                                         /           \
                                       YES            NO
                                       /               \
                       [ No Reminder Allowed ]          v
                                                Is Employee Assigned?
                                                (assigned_employee_id)
                                                    /            \
                                                  YES             NO
                                                  /                \
                       [ Recipient: EMPLOYEE ]                      v
                       (User ID: assigned_employee_id)   Is Department Assigned?
                                                         (target_department_id)
                                                             /            \
                                                           YES             NO
                                                           /                \
                                    [ Recipient: HOD ]           [ No Recipient / Disabled ]
                                    (User ID of Dept HOD)
```

---

## 2. Definitive Business Rules

### Rule 1: Employee Assigned (`assigned_employee_id != None`)
- **Recipient**: Exclusively the assigned employee.
- **Recipient Role**: `"Employee"`.
- **HOD Behavior**: The reminder is **not** sent to the HOD (avoids spamming managers for delegated tasks).
- **Example**: If Document 3 is assigned to Rahul Sharma (ID: 101), the reminder is delivered directly to Rahul Sharma's user notification feed.

### Rule 2: Department Assigned, No Employee (`target_department_id != None` and `assigned_employee_id == None`)
- **Recipient**: The Head of Department (HOD) for that specific department.
- **Recipient Role**: `"HOD"`.
- **Example**: If Document 5 is routed to IT (Dept ID: 5) but not yet delegated to a staff member, the reminder is delivered to IT HOD (ID: 7).

### Rule 3: Unassigned / Unrouted Document (`target_department_id == None`)
- **Resolution**: `None`.
- **UI Behavior**: "Send Action Reminder" button is disabled.

### Rule 4: Closed Document (`current_stage == "CLOSED"` or `status == "Closed"`)
- **Resolution**: `None`.
- **UI Behavior**: Reminders are prohibited on finalized/closed records.

---

## 3. Database Schema: `notifications`

```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(doc_id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);
```

### JSON / API Representation:
```json
{
  "id": 1,
  "user_id": 101,
  "document_id": 3,
  "document_reference": "CDTRS-2026-0003",
  "title": "Action Reminder",
  "message": "Action Reminder: Pending action required for document CDTRS-2026-0003 (Statutory Vendor Tax Clearance & Procurement Verification).",
  "is_read": false,
  "created_at": "2026-08-16 11:30"
}
```

---

## 4. Endpoints Expected
1. `GET /notifications` (Query params: `user_id`, `unread_only=true|false`)
2. `PATCH /notifications/{notification_id}/read` (Marks notification as read)
3. `POST /documents/{document_id}/remind` (Dispatches an action reminder, creates a notification for the resolved recipient, and logs an `Action Reminder Sent` audit event).
