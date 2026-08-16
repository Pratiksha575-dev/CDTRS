# Canonical Workflow & State Transitions

This document defines the complete state machine, routing paths, role authorities, and lifecycle transitions in the CDTRS system.

---

## 1. Primary Lifecycle State Diagram

```text
       [ Incoming Dispatch / Scanned Intake ]
                         |
                         v
       +------------------------------------+
       |          STAGE: DS                 | <-----------------------+
       |   Status: Received                 |                         |
       +------------------------------------+                         |
             |                         |                              |
 (Normal Workflow)           (Pre-Reviewed Bypass)                    |
             |                         |                              |
             v                         |                              |
+--------------------------+           |                              |
|     STAGE: DIRECTOR      |           |                              |
| Status: Under Review     |           |                              |
+--------------------------+           |                              |
             |                         |                              |
   (Director Remark Added)             |                              |
   (Returned to DS)                    |                              |
             |                         |                              |
             v                         |                              |
+--------------------------+           |                              |
|       STAGE: DS          |           |                              |
| Status: Review Completed |           |                              |
+--------------------------+           |                              |
             |                         |                              |
             +------------+------------+                              |
                          |                                           |
             (DS Routes to Department / HOD)                          |
                          |                                           |
                          v                                           |
       +------------------------------------+                         |
       |          STAGE: HOD                |                         |
       |   Status: Under HOD Processing     |                         |
       +------------------------------------+                         |
                          |                                           |
            (HOD Delegates to Employee)                               |
                          |                                           |
                          v                                           |
       +------------------------------------+                         |
       |         STAGE: EMPLOYEE            |                         |
       |   Status: Assigned for Execution   |                         |
       +------------------------------------+                         |
                          |                                           |
             (Employee Submits Progress)                              |
                          |                                           |
                          v                                           |
       +------------------------------------+                         |
       |         STAGE: EMPLOYEE            |                         |
       |   Status: Progress Updated         |                         |
       +------------------------------------+                         |
                          |                                           |
            (DS Forwards Follow-up Review)                            |
                          |                                           |
                          v                                           |
       +------------------------------------+                         |
       |         STAGE: DIRECTOR            |                         |
       |   Status: Under Review             |                         |
       +------------------------------------+                         |
                          |                                           |
            (Director Endorses & Returns)                             |
                          +-------------------------------------------+
                          |
                  (DS Closes Document)
                          |
                          v
       +------------------------------------+
       |          STAGE: CLOSED             |
       |   Status: Closed                   |
       +------------------------------------+
```

---

## 2. Complete State Transition Matrix

| Step | Action Name | Performed By | Endpoint / Method | Stage Before | Status Before | Stage After | Status After | Current Owner | Dept / Emp Affected | Audit Event Logged |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | **Document Intake** | DS (`ds`) | `POST /documents` | *None* | *None* | `DS` | `Received` | DS (1) | *None* | `Document Ingested` |
| **2** | **Route to Director** | DS (`ds`) | `POST /documents/{id}/route` (`DS_TO_DIRECTOR`) | `DS` | `Received` / `Director Review Completed` | `DIRECTOR` | `Under Director Review` | Director (2) | *None* | `Routed to Director` |
| **3** | **Save Director Remark** | Director (`director`) | `PATCH /documents/{id}/director-remark` | `DIRECTOR` | `Under Director Review` | `DIRECTOR` | `Under Director Review` | Director (2) | Sets `director_remark` | `Director Remark Recorded` |
| **4** | **Return to DS** | Director (`director`) | `POST /documents/{id}/return-to-ds` | `DIRECTOR` | `Under Director Review` | `DS` | `Director Review Completed` | DS (1) | *None* | `Returned to DS` |
| **5** | **Route to HOD** | DS (`ds`) | `POST /documents/{id}/route` (`DS_TO_HOD`) | `DS` | `Director Review Completed` / `Received` | `HOD` | `Under HOD Processing` | HOD of Target Dept | Sets `target_department_id` | `Routed to HOD` |
| **6** | **Direct Route to Employee** | DS (`ds`) | `POST /documents/{id}/route` (`DS_TO_EMPLOYEE`) | `DS` | `Received` / `Director Review Completed` | `EMPLOYEE` | `Assigned for Execution` | Assigned Employee | Sets `target_department_id` & `assigned_employee_id` | `Directly Assigned to Staff` |
| **7** | **Assign Employee (HOD)** | HOD (`hod_*`) | `POST /documents/{id}/assign` | `HOD` | `Under HOD Processing` | `EMPLOYEE` | `Assigned for Execution` | Assigned Employee | Sets `assigned_employee_id` | `Assigned to Employee` |
| **8** | **Submit Progress Note** | Employee (`emp_*`) | `POST /documents/{id}/progress` | `EMPLOYEE` | `Assigned for Execution` / `In Progress` | `EMPLOYEE` | `Progress Updated` | Assigned Employee | Appends `progress_updates` & optional `attachments` | `Progress Updated` |
| **9** | **Forward Follow-up to Director** | DS (`ds`) | `POST /documents/{id}/follow-up` | `DS` / `EMPLOYEE` / `HOD` | `Progress Updated` | `DIRECTOR` | `Under Director Review` | Director (2) | *None* | `Follow-up Sent to Director` |
| **10** | **Close Document** | DS (`ds`) | `POST /documents/{id}/close` | `DS` / `EMPLOYEE` | `Director Review Completed` / `Progress Updated` | `CLOSED` | `Closed` | DS (1) | Document archived | `Document Closed` |

---

## 3. Special Workflow Case: Pre-Reviewed Director Remark Bypass

### The Use Case:
Certain documents (like physical letters, government scans, or memos signed offline) already have a handwritten or formal approval/directive from the Director before they reach the DS intake desk (e.g. **Document 4**).

### Execution Flow:
1. **Intake / OCR Extraction**:
   - The scanner/OCR extracts `has_prior_director_remark = True` and the text of the directive:
     *"Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."*
2. **Intake UI & Document Viewer**:
   - The UI displays the amber alert card: **"⚡ Director Remark Detected: Direct routing bypass available."**
3. **DS Action**:
   - DS clicks **"Direct Route to Rahul Sharma (Finance)"**.
   - Endpoint called: `POST /documents/4/route` with `route_type: "DS_TO_EMPLOYEE"`, `to_user_id: 101`, `to_department_id: 1`.
4. **State Transition**:
   - `current_stage` transitions directly to `"EMPLOYEE"`.
   - `status` transitions directly to `"Assigned for Execution"`.
   - `director_remark` is preserved.
   - **Director review is bypassed**, saving unnecessary routing roundtrips.
5. **Visibility**:
   - The document appears in **Director's Reviewed Documents** archive (`status != "Received"` and `director_remark IS NOT NULL`).
   - The document appears in **Rahul Sharma's My Tasks** table.
