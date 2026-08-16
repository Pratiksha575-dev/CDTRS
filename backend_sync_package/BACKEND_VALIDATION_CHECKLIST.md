# Backend Validation & Verification Checklist

This checklist provides the backend developer with a step-by-step verification protocol to validate that the PostgreSQL database and FastAPI endpoints match the frontend specification.

---

## 1. Authentication & Security Verification
- [ ] **DS Login**: `POST /auth/login` with `username: "ds"`, `password: "1234"` returns `200 OK` with role `"Director Secretary"`.
- [ ] **Director Login**: `POST /auth/login` with `username: "director"`, `password: "1234"` returns `200 OK` with role `"Director"`.
- [ ] **Finance HOD Login**: `POST /auth/login` with `username: "hod_finance"`, `password: "1234"` returns `200 OK` with role `"HOD"`, `department_id: 1`.
- [ ] **Employee Login**: `POST /auth/login` with `username: "emp_rahul"`, `password: "1234"` returns `200 OK` with role `"Employee"`, `department_id: 1`.
- [ ] **Invalid Credentials**: `POST /auth/login` with invalid password returns `401 Unauthorized` (does NOT throw 500 error).

---

## 2. Canonical Initial State Verification
- [ ] **Total Documents Count**:
  ```sql
  SELECT COUNT(*) FROM documents; -- MUST BE EXACTLY 5
  SELECT COUNT(DISTINCT reference_no) FROM documents; -- MUST BE EXACTLY 5
  ```
- [ ] **All in DS Inbox**:
  ```sql
  SELECT COUNT(*) FROM documents WHERE current_stage = 'DS' AND status = 'Received'; -- MUST BE 5
  ```
- [ ] **Zero Initial Routing / Assignment**:
  ```sql
  SELECT COUNT(*) FROM documents WHERE target_department_id IS NOT NULL OR assigned_employee_id IS NOT NULL; -- MUST BE 0
  ```
- [ ] **Clean Initial Audit History**:
  ```sql
  SELECT COUNT(*) FROM workflow_history; -- MUST BE EXACTLY 5 (1 Ingestion event per document)
  ```

---

## 3. Document 1 Normal Multi-Hop Workflow Test
- [ ] **Step 1 (Route to Director)**:
  - `POST /documents/1/route` with `route_type: "DS_TO_DIRECTOR"`.
  - Document 1 stage becomes `"DIRECTOR"`, status becomes `"Under Director Review"`.
  - `SELECT COUNT(*) FROM documents;` remains **5**.
- [ ] **Step 2 (Director Remark)**:
  - `PATCH /documents/1/director-remark` with text `"Directive approved."`.
  - `director_remark` is saved.
- [ ] **Step 3 (Return to DS)**:
  - `POST /documents/1/return-to-ds`.
  - Document 1 stage becomes `"DS"`, status becomes `"Director Review Completed"`.
- [ ] **Step 4 (DS Routes to Procurement HOD)**:
  - `POST /documents/1/route` with `route_type: "DS_TO_HOD"`, `to_department_id: 2`.
  - Document 1 stage becomes `"HOD"`, status becomes `"Under HOD Processing"`.
  - Document 1 is visible to Procurement HOD (`hod_proc`).
- [ ] **Step 5 (HOD Assigns Priya Verma)**:
  - `POST /documents/1/assign` with `assigned_to_id: 201`.
  - Document 1 stage becomes `"EMPLOYEE"`, status becomes `"Assigned for Execution"`.
  - Document 1 appears in Priya Verma's (`emp_priya`) tasks.
- [ ] **Step 6 (Employee Progress)**:
  - `POST /documents/1/progress` with `description: "Completed compliance check."`.
  - Document 1 status becomes `"Progress Updated"`.
- [ ] **Step 7 (DS Follow-up)**:
  - `POST /documents/1/follow-up`.
  - Document 1 stage becomes `"DIRECTOR"`.
- [ ] **Step 8 (Director Endorsement & Return)**:
  - `POST /documents/1/return-to-ds`.
  - Document 1 stage becomes `"DS"`, status becomes `"Director Review Completed"`.
- [ ] **Step 9 (DS Closure)**:
  - `POST /documents/1/close`.
  - Document 1 stage becomes `"CLOSED"`, status becomes `"Closed"`.
- [ ] **Zero Duplication Verification**:
  ```sql
  SELECT COUNT(*) FROM documents; -- MUST STILL BE EXACTLY 5
  SELECT COUNT(DISTINCT reference_no) FROM documents; -- MUST BE EXACTLY 5
  ```

---

## 4. Document 4 Pre-Reviewed Bypass Test
- [ ] **Initial Check**: Document 4 has `has_prior_director_remark = TRUE` and `director_remark` populated.
- [ ] **Direct Route Execution**:
  - `POST /documents/4/route` with `route_type: "DS_TO_EMPLOYEE"`, `to_user_id: 101`, `to_department_id: 1`.
  - Stage immediately becomes `"EMPLOYEE"`, status becomes `"Assigned for Execution"`.
  - Director review is bypassed.
  - Document 4 is visible in Rahul Sharma's task queue (`GET /documents` as `emp_rahul`).
  - Document 4 is visible in Director's Reviewed Documents archive (`GET /documents` as `director`).

---

## 5. Document 5 Urgent / Deadline Tracking Test
- [ ] **Deadline Check**: Document 5 has `priority = 'High'` and `deadline` set to future date.
- [ ] **Route to IT**:
  - `POST /documents/5/route` with `route_type: "DS_TO_HOD"`, `to_department_id: 5`.
  - Document 5 appears in IT HOD's (`hod_it`) inbox.

---

## 6. Action Reminder Verification
- [ ] **When Assigned to Employee**:
  - `POST /documents/3/remind` dispatches reminder exclusively to Rahul Sharma (ID: 101).
  - Notification row is inserted in `notifications` for `user_id = 101`.
  - `Action Reminder Sent` audit event is logged in `workflow_history`.
- [ ] **When Assigned to Department Only**:
  - `POST /documents/5/remind` dispatches reminder to IT HOD (ID: 7).
  - Notification row is inserted in `notifications` for `user_id = 7`.
- [ ] **When Closed**:
  - Attempting to send reminder on closed Document 1 is rejected or returns `None`.

---

## 7. Audit History Continuity Test
- [ ] Run query for Document 1 history:
  ```sql
  SELECT id, action, from_role, to_role, performed_by, created_at
  FROM workflow_history
  WHERE document_id = 1
  ORDER BY created_at ASC;
  ```
  - Verifies that all 9 events exist in chronological sequence without gaps.
