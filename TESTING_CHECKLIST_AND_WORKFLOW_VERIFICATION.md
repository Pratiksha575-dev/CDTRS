# CDTRS Upgrades: Manual Verification & Testing Checklist

Follow this step-by-step checklist to test and verify all the new upgrades in your local CDTRS application.

---

## 🚀 Pre-requisite: Clean Database Setup

Run this single command in your terminal to ensure clean tables, all 15 official departments, and test accounts are ready:

```bash
python backend/seed.py --reset
```

Then start the backend and frontend:
- **Terminal 1 (Backend)**: `uvicorn main:app --reload --port 8000` (inside `backend/`)
- **Terminal 2 (Frontend)**: `python frontend/main.py`

---

## 🧪 Test Flow 1: Administrator Suite & System Configuration

### Login Credentials:
- **Username**: `admin`
- **Password**: `cdtrs@admin`

### Checklist:
- [ ] **Sidebar Navigation**: Confirm `Admin Suite` appears in the sidebar menu.
- [ ] **Tab 1: Users & Roles**:
  - [ ] Search for `tso_user`, `hod_pstd`, `emp_anil`. Verify their roles, employee codes, and managed departments display correctly.
  - [ ] Click **`+ Add New User`**: Create a test employee with role `EMPLOYEE` and department `PSTD`.
  - [ ] Click **`🔑 Pwd`** next to any user and verify password reset succeeds.
  - [ ] Click **`✏️ Edit`** next to an HOD and modify `managed_depts` (e.g. `PSTD, ESFS, CEC`).
- [ ] **Tab 2: Departments**:
  - [ ] Verify all **15 official departments** are listed (`PSTD`, `FCTD`, `DS`, `ESFS`, `CEC`, `CER`, `MBT`, `P&TC`, `PC`, `C&IT`, `MMG_STORES`, `TM`, `ADMIN`, `ACCT`, `MISC`).
  - [ ] Click **`+ Add Department`** to create a test division.
- [ ] **Tab 3: Priority & Email Config**:
  - [ ] Change Red Days ($\le 0$), Orange Days ($1-3$), Yellow Days ($4-7$).
  - [ ] Edit the reminder email subject/body template.
  - [ ] Click **`💾 Save Configuration Changes`** and verify the success notification.
- [ ] **Tab 4: Security & Audit Trail**:
  - [ ] Inspect the live table showing user creation, updates, and system events.

---

## 🧪 Test Flow 2: Multi-Department HOD Context Switching

### Login Credentials:
- **Username**: `hod_pstd`
- **Password**: `cdtrs@hod` (or `cdtrs@emp`)

### Checklist:
- [ ] **Sidebar Department Switcher**: Look at the top of the sidebar under the username. Verify a blue dropdown **`🏢 Active Department:`** is present showing `PSTD` and `ESFS`.
- [ ] **Toggle Context**:
  - [ ] Switch dropdown to `ESFS`. Verify the HOD Inbox and Dashboard reload dynamically for `ESFS`.
  - [ ] Switch back to `PSTD`. Verify the view updates to `PSTD`.
- [ ] **Department-Isolated Staff Assignment**:
  - [ ] Double-click any document in the queue (or click **`Open Document / Assign`**).
  - [ ] In the **`Assign To:`** dropdown, verify it strictly lists employees belonging to `PSTD` (`Anil Kumar [EMP-PSTD-001]`, `Vikram Malhotra [EMP-PSTD-002]`) and does **not** mix employees from other departments.

---

## 🧪 Test Flow 3: TSO (Technical Staff Officer) Integration

### Login Credentials:
- **Username**: `tso_user`
- **Password**: `cdtrs@tso` (or `cdtrs@emp`)

### Checklist:
- [ ] **Dashboard Structure**: Verify the TSO dashboard displays the **Employee-style cards** (*Active Tasks*, *Pending Execution*, *In Progress*, *Closed*) rather than HOD/Director approval workflows.
- [ ] **Sidebar Menu**: Verify menu has `Dashboard`, `My Tasks`, and `History / Audit`.
- [ ] **My Tasks Queue**: Verify TSO can open technical directives assigned by the Director or DS.
- [ ] **Direct Reporting to DS/Director**:
  - [ ] Double-click an assigned task $\rightarrow$ Submit progress note / technical review.
  - [ ] Confirm progress reports **directly to DS / Director** for clearance (bypassing HOD review queue).

---

## 🧪 Test Flow 4: DS Intake, OCR Director Remarks & Confirmation

### Login Credentials:
- **Username**: `ds_user`
- **Password**: `cdtrs@ds`

### Checklist:
- [ ] **Dynamic Department Dropdown**: In **`Document Processing`**, click the **`Suggested Dept:`** dropdown and verify all **15 official departments** appear.
- [ ] **Smart Staff Suggestions**: Click **`Suggested Staff:`** dropdown. Verify it displays:
  - Department HODs
  - **TSO** (`Technical Staff Officer [TSO - FCTD]`)
  - Department Employees
- [ ] **Director Remark OCR Auto-Detection**:
  - [ ] Upload or process a document containing prior Director notes.
  - [ ] Verify the **yellow warning card** (*"Prior Director Directive Detected in Source"*) appears automatically.
  - [ ] Verify the button text changes to *"Confirm & Route Directly to HOD / Staff"*.
- [ ] **Explicit Confirmation Prompt**:
  - [ ] Click the dispatch button.
  - [ ] Verify an explicit popup dialog asks:
    > *"Are you sure you want to dispatch this document? ... Reference: [REF] ... Route Target: [TARGET] ... Proceed with dispatch?"*
  - [ ] Click **Yes** to dispatch.

---

## 🧪 Test Flow 5: Employee Task Execution

### Login Credentials:
- **Username**: `emp_anil`
- **Password**: `cdtrs@emp`

### Checklist:
- [ ] **My Tasks Queue**: Verify tasks delegated by `hod_pstd` appear with reference, title, priority, deadline, and the forwarded HOD remark.
- [ ] **Double-Click Action**: Double-click any task to open the document viewer.
- [ ] **Progress Submission**: Submit a progress report and verify status transitions to `In Progress` / `Progress Updated`.

---

## Summary of Test Accounts Reference Table

| Role | Username | Password | Key Feature to Check |
|:---|:---|:---|:---|
| **ADMIN** | `admin` | `cdtrs@admin` | 4-Tab Admin Suite (Users, Depts, Settings, Audit) |
| **DS** | `ds_user` | `cdtrs@ds` | 15 Dept Dropdown, TSO in Staff, OCR Remark Banner, Confirmation Prompt |
| **DIRECTOR** | `director` | `cdtrs@director` | Executive Review Queue, Director Directives |
| **TSO** | `tso_user` | `cdtrs@tso` | Employee-style Dashboard, Direct DS/Director reporting |
| **MULTI-HOD** | `hod_pstd` | `cdtrs@hod` | Sidebar `Active Department:` Switcher (`PSTD` $\leftrightarrow$ `ESFS`), Department-isolated staff assignment |
| **EMPLOYEE** | `emp_anil` | `cdtrs@emp` | Task execution, double-click viewing, progress updates |
