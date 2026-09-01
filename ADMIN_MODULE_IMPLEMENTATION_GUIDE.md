# CDTRS: Administrator Module Architecture, UI Design & Implementation Guide

> **SRS Reference Compliance**: Fulfills **FR-7.1**, **FR-7.6** (User/Role/Department Management), **FR-5.5 / BR-6** (Configurable Priority Thresholds), **FR-6.7** (Reminder Email Template Editor), **NFR-SEC.4 / FR-7.8** (System-wide Audit Logs), and **BR-3** (Administrative Oversight).

---

## 🎨 1. Administrator Interface Design & Layout

When an Administrator logs in (`username: admin`), the system renders a dedicated **Administrator Suite** with 4 tabs styled in clean enterprise navy/slate (`theme.qss`):

```text
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│  🛡️ CDTRS SYSTEM ADMINISTRATION                                [ Admin: sysadmin ] [Logout]│
├──────────────┬────────────────────────────────────────────────────────────────────────────┤
│ 👥 Users &    │ [🔍 Search User... ] [Filter Role ▼] [Filter Dept ▼]    [+ Add New User]    │
│    Roles     │ ────────────────────────────────────────────────────────────────────────── │
│              │ Username   | Full Name      | Role     | Department | Status   | Actions    │
│ 🏢 Depts &   │ ds_user    | Dir Secretary  | DS       | Central    | Active   | [Edit][Pwd]│
│    Mapping   │ director   | Ex. Director   | DIRECTOR | Executive  | Active   | [Edit][Pwd]│
│              │ hod_fin    | Dr. Sharma     | HOD      | Finance    | Active   | [Edit][Pwd]│
│ ⚙️ System    │ emp_rahul  | Rahul Sharma   | EMPLOYEE | Finance    | Active   | [Edit][Pwd]│
│    Settings  │ ────────────────────────────────────────────────────────────────────────── │
│              │ Total Accounts: 12 • Active: 12 • Suspended: 0                             │
│ 📜 Audit &   ├────────────────────────────────────────────────────────────────────────────┤
│    Security  │ [ ⚙️ CONFIGURATION PREVIEW: Priority Thresholds & Email Templates ]        │
└──────────────┴────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 2. Complete Prompt for Gemini / AI Assistant

You can copy and paste the prompt below into Gemini to implement the Administrator module:

```markdown
# TASK: Implement Administrator Suite (User/Dept Management, Settings, Audit Logs) in CDTRS

You are working on the CDTRS (Centralised Document Tracking and Routing System) codebase.
Based on the SRS specifications (FR-7.6, FR-5.5, FR-6.7, NFR-SEC.4), implement the complete Administrator Module.

The Administrator must be able to:
1. Manage users (Create, Edit, Deactivate, Reset Passwords, Assign Roles & Departments).
2. Manage departments (Create, Edit, Assign HOD).
3. Configure Priority & Deadline Color Thresholds (Red, Orange, Yellow, Green days) dynamically.
4. Configure the Reminder Email Template dynamically without changing code.
5. Inspect system-wide audit and activity logs.

Please implement the following changes step-by-step:

---

### Step 1: Backend Database Models (`backend/models.py`)

1. Update `UserRole` Enum in `backend/models.py`:
```python
class UserRole(str, enum.Enum):
    ADMIN     = "ADMIN"
    DS        = "DS"
    DIRECTOR  = "DIRECTOR"
    HOD       = "HOD"
    HOD_PA    = "HOD_PA"
    EMPLOYEE  = "EMPLOYEE"
    READ_ONLY = "READ_ONLY"
```

2. Add `SystemConfig` model to store dynamic settings:
```python
class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, index=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

---

### Step 2: Backend Schemas & CRUD (`backend/schemas.py`, `backend/crud.py`)

1. Add Schemas in `backend/schemas.py`:
   - `UserAdminCreate(username, full_name, role, department_id, email, outlook_email, gov_email, password)`
   - `UserAdminUpdate(full_name, role, department_id, email, outlook_email, gov_email, is_active)`
   - `PasswordResetRequest(new_password)`
   - `SystemConfigUpdate(configs: Dict[str, str])`
   - `DepartmentCreate(name, code)`

2. Add CRUD Methods in `backend/crud.py`:
   - `create_user_admin(db, user_data)`
   - `update_user_admin(db, user_id, user_data)`
   - `reset_user_password(db, user_id, new_password)`
   - `toggle_user_active_status(db, user_id, is_active)`
   - `get_system_configs(db) -> Dict[str, str]` (with defaults for thresholds & email templates)
   - `set_system_configs(db, configs: Dict[str, str])`
   - `get_audit_logs(db, limit=100, action_filter=None)`

---

### Step 3: Backend Admin API Router (`backend/routers/admin.py` or `backend/main.py`)

Create `/api/admin/` endpoints protected by `require_role(UserRole.ADMIN)`:
- `GET /api/admin/users`: List all users with department names and status.
- `POST /api/admin/users`: Create new user.
- `PUT /api/admin/users/{user_id}`: Update user role, department, details.
- `POST /api/admin/users/{user_id}/reset-password`: Reset password.
- `PATCH /api/admin/users/{user_id}/status`: Toggle active/inactive.
- `POST /api/admin/departments`: Add department.
- `GET /api/admin/configs`: Fetch current thresholds and email templates.
- `POST /api/admin/configs`: Save updated thresholds and email templates.
- `GET /api/admin/audit-logs`: Fetch system-wide activity logs.

---

### Step 4: Seed Data (`backend/data/seed_data.json`)

Add the default administrator account:
```json
{
  "system_users": [
    {
      "username": "admin",
      "role": "ADMIN",
      "full_name": "System Administrator",
      "email": "admin@cdtrs.gov.in",
      "outlook_email": "admin@outlook.com",
      "gov_email": "admin@nic.in",
      "department": null,
      "designation": "IT Systems Administrator",
      "default_password": "cdtrs@admin"
    }
  ]
}
```

---

### Step 5: Frontend Admin Page (`frontend/pages/admin_panel.py`)

Create `AdminPanelPage(QWidget)` containing a responsive `QTabWidget`:

#### Tab 1: User & Role Management
- Live Search Bar & Role Filter dropdown (`All Roles`, `DS`, `Director`, `HOD`, `Employee`, `Read-Only`).
- Table: `[Username, Full Name, Role, Department, Email, Status, Actions]`.
- Action buttons per row: `[✏️ Edit]` `[🔑 Reset Pwd]` `[🚫 Deactivate]`.
- Top Button: `[+ Add User]` opening a modal form dialog.

#### Tab 2: Department Management
- Table of departments with Code, Name, Designated HOD, and Staff Count.
- `[+ Add Department]` button and Edit dialog.

#### Tab 3: System Configuration & Thresholds (FR-5.5, FR-6.7)
- **Priority Threshold Editor**:
  - 🔴 Red: Overdue ($\le 0$ days remaining)
  - 🟠 Orange: Spinbox for Critical days (Default: `1 - 3` days)
  - 🟡 Yellow: Spinbox for Approaching days (Default: `4 - 7` days)
  - 🟢 Green: Standard ($> 7$ days)
- **Reminder Email Template Editor**:
  - Subject input: `[CDTRS REMINDER] Action Pending on {ref} - {title}`
  - Body text area: Multi-line template supporting `{ref}`, `{title}`, `{deadline}`, `{department}`, `{hod_name}`.
- `[💾 Save System Configurations]` button with visual feedback.

#### Tab 4: Security & Audit Trail (NFR-SEC.4)
- Filterable table displaying `[Timestamp, User, Role, Action Category, Details]`.
- Export audit logs button.

---

### Step 6: Frontend Sidebar & MainWindow Routing

1. In `frontend/ui/sidebar.py`:
   - For `role == UserRole.ADMIN`: Menu items = `["User Management", "Departments", "System Settings", "Audit Logs"]`.
2. In `frontend/ui/main_window.py`:
   - Instantiate `AdminPanelPage` and bind sidebar navigation.
```

---

## 🗂️ File Modification Summary

| Component | Files to Modify / Create | Purpose |
|---|---|---|
| **Models & Enums** | [`backend/models.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/models.py) | Add `ADMIN`, `HOD_PA`, `READ_ONLY` to `UserRole`; create `SystemConfig` table. |
| **API Endpoints** | [`backend/main.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/main.py), [`backend/schemas.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/schemas.py), [`backend/crud.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/crud.py) | Full CRUD for users, departments, config settings, and audit logs. |
| **Seed Data** | [`backend/data/seed_data.json`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/data/seed_data.json) | Seed default `admin` account (`password: cdtrs@admin`). |
| **Admin UI** | `frontend/pages/admin_panel.py` [NEW] | 4-tab administration suite (Users, Departments, Settings, Audit). |
| **Navigation** | [`frontend/ui/sidebar.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/frontend/ui/sidebar.py), [`frontend/ui/main_window.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/frontend/ui/main_window.py) | Add Admin role navigation & page registration. |
