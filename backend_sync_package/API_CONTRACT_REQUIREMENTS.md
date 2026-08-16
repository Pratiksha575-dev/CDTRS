# REST API Contract Requirements

This document defines the complete REST API specification expected by the CDTRS frontend.

---

## 1. Authentication & Session

### `POST /auth/login` (or `/login`)
- **Description**: Authenticates user credentials and returns session token + user profile.
- **Request Body**:
  ```json
  {
    "username": "ds",
    "password": "password"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "ds",
      "full_name": "Director Secretary",
      "role": "Director Secretary",
      "email": "ds@organization.gov.in",
      "department_id": null,
      "department_name": null,
      "is_active": true
    }
  }
  ```
- **Error Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Invalid username or password"
  }
  ```

### `GET /auth/me`
- **Description**: Returns profile for currently authenticated bearer token.
- **Headers**: `Authorization: Bearer <token>`
- **Success Response (200 OK)**: User JSON object.

---

## 2. Organization Directory

### `GET /departments`
- **Success Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Finance",
      "code": "FIN",
      "is_active": true
    }
  ]
  ```

### `GET /departments/{dept_id}/employees`
- **Success Response (200 OK)**:
  ```json
  [
    {
      "id": 101,
      "username": "emp_rahul",
      "full_name": "Rahul Sharma",
      "role": "Employee",
      "department_id": 1,
      "department_name": "Finance",
      "designation": "Senior Accounts Officer"
    }
  ]
  ```

### `GET /users`
- **Query Parameters**: `role` *(optional)*, `department_id` *(optional)*
- **Success Response (200 OK)**: Array of User objects.

---

## 3. Document Lifecycle & Intake

### `GET /documents/inbox`
- **Description**: Returns dispatches in the raw intake queue awaiting formal registration.
- **Success Response (200 OK)**: Array of Document objects.

### `DELETE /documents/inbox/{item_id}`
- **Description**: Removes an item from the intake queue after registration.
- **Success Response (200 OK / 204 No Content)**: `{"status": "deleted"}`

### `GET /documents`
- **Query Parameters**:
  - `status` *(optional)*: Filter by status string.
  - `department` *(optional)*: Filter by department name.
  - `source` *(optional)*: Filter by sender/source string.
  - `search` *(optional)*: Full-text search on title, reference number, sender.
- **Role Scoping Rules**:
  - `HOD`: Returns only documents where `target_department_id` matches HOD's department and stage is `HOD`, `EMPLOYEE`, or `CLOSED`.
  - `Employee`: Returns only documents where `assigned_employee_id` matches employee's ID.
  - `DS` / `Director`: Returns all documents.
- **Success Response (200 OK)**: Array of Document objects.

### `GET /documents/{document_id}`
- **Success Response (200 OK)**: Full Document JSON object.

### `POST /documents`
- **Description**: Registers a new document or updates an existing intake document.
- **Request Body (JSON or Multipart Form)**:
  ```json
  {
    "id": 1,
    "reference_no": "CDTRS-2026-0001",
    "title": "National Higher Education Accreditation & Governance Compliance Directive",
    "date": "2026-08-16 09:30 AM",
    "mode": "Outlook / Government Mail",
    "source": "Ministry of Higher Education",
    "priority": "Medium",
    "deadline": null,
    "status": "Received",
    "current_stage": "DS",
    "suggested_department_id": null,
    "suggested_employee_id": null,
    "file_path": "data/incoming/government_mail/accreditation_compliance_directive.pdf"
  }
  ```
- **Success Response (201 Created / 200 OK)**: Created/Updated Document object.

### `POST /documents/{document_id}/close`
- **Description**: DS finalizes and closes a completed document.
- **Request Body**: `{"remarks": "Document finalized and closed."}`
- **Success Response (200 OK)**: Updated Document with `current_stage: "CLOSED"`, `status: "Closed"`.

---

## 4. Routing & State Machine Endpoints

### `POST /documents/{document_id}/route`
- **Description**: Executes a formal DS routing decision.
- **Request Body**:
  ```json
  {
    "route_type": "DS_TO_DIRECTOR",
    "to_user_id": 2,
    "to_department_id": null,
    "remarks": "Forwarded for Executive Review"
  }
  ```
- **Allowed `route_type` values**:
  - `DS_TO_DIRECTOR` (Moves stage to `DIRECTOR`, status to `Under Director Review`)
  - `DIRECTOR_TO_DS` (Moves stage to `DS`, status to `Director Review Completed`)
  - `DS_TO_HOD` (Moves stage to `HOD`, status to `Under HOD Processing`)
  - `DS_TO_EMPLOYEE` (Moves stage to `EMPLOYEE`, status to `Assigned for Execution`)
  - `DS_TO_DIRECTOR_FOLLOWUP` (Moves stage to `DIRECTOR`, status to `Under Director Review`)
- **Success Response (200 OK)**: Updated Document object.

### `PATCH /documents/{document_id}/director-remark`
- **Description**: Director records formal directive/remark.
- **Request Body**:
  ```json
  {
    "director_remark": "Accreditation directive approved. Proceed with compliance."
  }
  ```
- **Success Response (200 OK)**: Updated Document object.

### `POST /documents/{document_id}/return-to-ds`
- **Description**: Director concludes review and returns document to DS.
- **Request Body**: `{"remarks": "Returned to DS"}`
- **Success Response (200 OK)**: Updated Document with `current_stage: "DS"`, `status: "Director Review Completed"`.

### `POST /documents/{document_id}/follow-up`
- **Description**: DS escalates completed progress to Director for final endorsement.
- **Request Body**: `{"remarks": "Forwarding progress update for endorsement."}`
- **Success Response (200 OK)**: Updated Document with `current_stage: "DIRECTOR"`, `status: "Under Director Review"`.

---

## 5. Delegation & Work Assignments

### `POST /documents/{document_id}/assign`
- **Description**: HOD delegates work on a document to a departmental employee.
- **Request Body**:
  ```json
  {
    "assigned_to_id": 201,
    "instructions": "Execute compliance verification against statutory guidelines."
  }
  ```
- **Success Response (200 OK)**: WorkAssignment JSON object. (Updates Document `current_stage: "EMPLOYEE"`, `status: "Assigned for Execution"`).

### `GET /documents/{document_id}/assignments`
- **Success Response (200 OK)**: Array of WorkAssignment objects.

---

## 6. Progress Updates & Supporting Files

### `POST /documents/{document_id}/progress`
- **Description**: Employee submits free-text progress notes and optional supporting file.
- **Request Body (Multipart Form or JSON)**:
  ```json
  {
    "description": "Compliance verification completed. Annexure certificate attached.",
    "file_path": "data/progress/compliance_certificate.pdf"
  }
  ```
- **Success Response (201 Created)**: ProgressUpdate JSON object. (Updates Document `status: "Progress Updated"`).

### `GET /documents/{document_id}/progress`
- **Success Response (200 OK)**: Array of ProgressUpdate objects.

---

## 7. Audit History

### `GET /documents/{document_id}/history`
- **Description**: Returns full chronological audit timeline for the specified document.
- **Success Response (200 OK)**: Array of WorkflowEvent objects sorted ascending by timestamp.

---

## 8. Reminders & Notifications

### `GET /notifications`
- **Query Parameters**: `user_id` *(optional)*, `unread_only` *(optional, default false)*
- **Success Response (200 OK)**: Array of Notification objects.

### `PATCH /notifications/{notification_id}/read`
- **Success Response (200 OK)**: `{"status": "marked_as_read"}`

### `POST /documents/{document_id}/remind`
- **Description**: Dispatches an action reminder to the resolved recipient and records an audit event.
- **Request Body**: `{"message": "Custom reminder text (optional)"}`
- **Success Response (200 OK)**:
  ```json
  {
    "recipient_type": "EMPLOYEE",
    "user_id": 101,
    "user_name": "Rahul Sharma",
    "role": "Employee",
    "department_name": "Finance",
    "document_id": 3,
    "document_reference": "CDTRS-2026-0003"
  }
  ```
