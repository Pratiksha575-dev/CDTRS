# CDTRS — Windows Quick Setup & Execution Guide

This guide walks you through downloading, setting up, and running the **CDTRS (Centralised Document Tracking and Routing System)** desktop application on any Windows 10 / 11 PC.

---

## 1. Requirements

Before starting, ensure you have:
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python **3.10**, **3.11**, **3.12**, or **3.13** installed from [python.org](https://www.python.org/downloads/) *(Ensure **"Add python.exe to PATH"** was checked during installation)*.
- **Git:** *(Optional)* Only needed if cloning via Git. Not required if downloading as a ZIP.
- **Internet Connection:** Required for installing dependencies and for connecting to the deployed Render backend API.
- **Database:** **No local PostgreSQL installation is required.** By default, the application connects directly to the live deployed cloud backend on Render.

---

## 2. Download from GitHub as ZIP

1. Open the CDTRS GitHub repository in your web browser.
2. Click the green **`<> Code`** button at the top-right of the repository page.
3. Click **`Download ZIP`**.
4. Right-click the downloaded `.zip` file and select **Extract All...**.
5. Choose a destination folder (e.g., `C:\Users\<YourUsername>\Desktop\CDTRS`).
6. Open the extracted folder and verify that you are in the **root project directory** (the folder containing `main.py`).

### Expected Project Directory Structure
```text
CDTRS/
├── api/                   # REST API client, endpoint definitions & exceptions
├── backend/               # FastAPI backend source & schemas
├── components/            # Reusable PySide6 UI widgets (table, viewer, badges)
├── config/                # Centralized settings & environment resolution
├── data/                  # Canonical incoming files and sample documents
├── models/                # Typed domain models, enums & serialization
├── pages/                 # Role-specific application pages & views
├── repositories/          # Repository abstraction (APIRepository & MockRepository)
├── scratch/               # Automated regression & integration test scripts
├── services/              # Business logic (auth, routing, OCR, workflow, notifications)
├── styles/                # Global QSS styling (theme.qss)
├── ui/                    # Login window, main shell window, and sidebar
├── .gitignore             # Git ignore rules for clean repository sharing
├── main.py                # Main application executable entry point
├── README.md              # Complete technical architecture & project documentation
├── requirements.txt       # Project dependencies
└── SETUP_GUIDE.md         # This setup guide
```

> **Important:** Avoid nested folder structures (e.g., `CDTRS-main/CDTRS-main/`). Make sure your terminal is opened in the directory containing `main.py`.

---

## 3. Create Virtual Environment

Open **PowerShell** in the project directory and run:

```powershell
# 1. Verify Python is installed and accessible
python --version

# 2. Create an isolated virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

> **PowerShell Execution Policy Alternative:**  
> If PowerShell shows an execution policy error (*"running scripts is disabled on this system"*), you can either:
> - **Option A (Recommended):** Bypass for current terminal:
>   ```powershell
>   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
>   .\.venv\Scripts\Activate.ps1
>   ```
> - **Option B:** Run commands directly using the virtual environment interpreter without activating:
>   ```powershell
>   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
>   .\.venv\Scripts\python.exe main.py
>   ```

---

## 4. Install Dependencies

With the virtual environment active, run:

```powershell
# 1. Upgrade pip to the latest version
python -m pip install --upgrade pip

# 2. Install all required dependencies
python -m pip install -r requirements.txt
```

### Verification Command
Run this one-line command to verify all core dependencies are installed correctly:
```powershell
python -c "import PySide6, requests, pip_system_certs; print('✓ All CDTRS core dependencies loaded successfully!')"
```

---

## 5. Configuration

Configuration is managed in [config/settings.py](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/config/settings.py) and reads environment variables with automatic defaults.

### Default Mode: Live Cloud API Mode
Out of the box, CDTRS is configured to connect to the deployed backend on Render:
- **Data Source:** `api`
- **Backend API URL:** `https://cdtrs.onrender.com/api/v1`

You do not need to configure anything if you want to use the live backend.

### Setting Configuration via PowerShell (Optional)
If you wish to explicitly set environment variables in your current PowerShell session:

```powershell
# Connect to Render Cloud Backend
$env:CDTRS_DATA_SOURCE="api"
$env:CDTRS_API_URL="https://cdtrs.onrender.com/api/v1"
```

---

## 6. Run the Application

Start the CDTRS desktop application by running:

```powershell
python main.py
```
*(Or if not activated: `.\.venv\Scripts\python.exe main.py`)*

---

## 7. First Run Checklist & Test Credentials

Use this checklist on your first run:

- [ ] **Application Starts:** The desktop application launches and displays the login screen.
- [ ] **Login Screen Appears:** Clean executive UI with Username and Password fields.
- [ ] **API Connection Verification:**
  - Login as **Director Secretary (DS)**:
    - **Username:** `ds_user`
    - **Password:** `cdtrs@ds`
- [ ] **Error Handling:** Entering an incorrect password displays a clean error dialog without crashing.
- [ ] **Main Window Opens:** Successful login opens the role-based main shell with sidebar and header.
- [ ] **Dashboard Loads:** KPI metric tiles and operational Action Required cards populate.
- [ ] **Documents / Inboxes Load:** Central Documents repository and Intake Inbox display registered workflow items.
- [ ] **Logout Works:** Clicking **Logout** cleans up the user session and safely returns to the login screen.

### Development Test Accounts (API Mode)
| Role | Username | Password | Purpose |
|:---|:---|:---|:---|
| **Director Secretary (DS)** | `ds_user` | `cdtrs@ds` | Document intake, routing to Director/HOD/Employee |
| **The Director** | `director` | `cdtrs@director` | Executive reviews, remarks & return-to-DS |
| **Finance HOD** | `hod_finance` | `cdtrs@hod` | Departmental task assignment & oversight |
| **Procurement HOD** | `hod_procurement` | `cdtrs@hod` | Procurement task assignment |
| **Finance Employee** | `emp_rahul` | `cdtrs@emp` | Task execution & progress updates (Rahul Sharma) |
| **Procurement Employee** | `emp_priya` | `cdtrs@emp` | Task execution & progress updates (Priya Verma) |

*(These accounts are pre-seeded development test accounts on the live Render test database).*

---

## 8. Common Windows Errors & Troubleshooting

### 1. `'python' is not recognized as an internal or external command`
- **Cause:** Python was not added to the Windows system `PATH`.
- **Fix:** Re-run the Python installer, select **Modify**, and check **"Add Python to environment variables"**. Alternatively, use the full path to `python.exe` (e.g. `C:\Users\<User>\AppData\Local\Programs\Python\Python313\python.exe`).

### 2. PowerShell Script Activation Blocked
- **Error:** `File ...\Activate.ps1 cannot be loaded because running scripts is disabled on this system.`
- **Fix:** Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell window, then retry `.\.venv\Scripts\Activate.ps1`.

### 3. Missing Module (`ModuleNotFoundError: No module named 'PySide6'`)
- **Cause:** Command was executed outside the virtual environment.
- **Fix:** Ensure the virtual environment is activated (`(.venv)` appears before your prompt) or run explicitly via `.\.venv\Scripts\python.exe main.py`.

### 4. Wrong Working Directory (`FileNotFoundError: styles/theme.qss`)
- **Cause:** Terminal is opened in a parent folder or nested subfolder.
- **Fix:** Make sure you `cd` into the folder that directly contains `main.py` and `styles/`.

### 5. Render Backend Free-Tier Cold Start Delay
- **Symptom:** Initial login takes 30–50 seconds or times out on the very first attempt.
- **Cause:** Render free-tier instances sleep after inactivity and take ~45 seconds to spin up on the first request.
- **Fix:** Wait 30 seconds and retry login. Subsequent requests will be fast and responsive.

### 6. SSL / Certificate Issues on Corporate / University Windows Networks
- **Fix:** The project automatically imports `pip_system_certs` in [api/client.py](file:///c:/Users/Pratiksha/OneDrive/Desktop/CDTRS%20-%20Copy/api/client.py) to use the native Windows Certificate Store, resolving corporate firewall/proxy SSL intercept issues automatically.

---

## 9. Mock Mode (Offline Development & Testing)

You can run the entire frontend workflow in **Mock Mode** without requiring an internet connection or backend API.

### Starting in Mock Mode:
```powershell
# Set mode to mock for the current PowerShell session
$env:CDTRS_DATA_SOURCE="mock"

# Run application
python main.py
```

### Mock Mode Test Credentials:
In Mock Mode, any non-empty password (such as `1234` or `admin`) works for all mock accounts:
- **DS:** `ds` *(or `master`)* / password: `1234`
- **Director:** `director` / password: `1234`
- **Finance HOD:** `hod_finance` / password: `1234`
- **Procurement HOD:** `hod_proc` / password: `1234`
- **Finance Employee (Rahul Sharma):** `emp_rahul` / password: `1234`

### Returning to API Mode:
```powershell
$env:CDTRS_DATA_SOURCE="api"
$env:CDTRS_API_URL="https://cdtrs.onrender.com/api/v1"
python main.py
```

> **Note:** Environment variables set via `$env:VAR=...` apply only to that specific PowerShell window session.

---

## 10. Project Structure & Responsibilities

| Directory / File | Description |
|:---|:---|
| `main.py` | Application entry point: initializes `QApplication`, loads `theme.qss`, and displays `LoginWindow`. |
| `api/` | REST API HTTP client (`client.py`), endpoint routing constants (`endpoints.py`), and error hierarchy (`exceptions.py`). |
| `components/` | Reusable Qt UI components: `document_table.py`, `document_viewer.py`, `document_preview.py`, `document_info.py`, `routing_dialogs.py`, `priority_badge.py`, `state_widgets.py`. |
| `config/` | Central configuration dataclass (`settings.py`) with environment variable parsing. |
| `models/` | Core data domain models (`DocumentModel`, `UserModel`, `WorkAssignmentModel`, `ProgressUpdateModel`, `WorkflowEventModel`, `AttachmentModel`) and enums (`RoleEnum`, `DocumentStatusEnum`, `WorkflowStageEnum`, `PriorityEnum`). |
| `pages/` | Primary role-based screen controllers: `dashboard.py`, `inbox.py`, `document_intake.py`, `documents.py`, `history.py`, `director_inbox.py`, `director_reviewed.py`, `hod_inbox.py`, `employee_tasks.py`. |
| `repositories/` | Decoupled data layer implementing `BaseRepository`: `APIRepository` (REST API) and `MockRepository` (in-memory demonstration dataset). |
| `services/` | Business service layer (`auth_service`, `document_service`, `routing_service`, `ocr_service`, `workflow_service`, `progress_service`, `notification_service`, `event_bus`). |
| `styles/` | Global stylesheet `theme.qss` defining color palette, typography, buttons, inputs, and cards. |
| `ui/` | Top-level window containers: `login.py`, `main_window.py`, and `sidebar.py`. |
| `scratch/` | Test suites and validation scripts. |

---

## 11. Important: Do Not Zip or Commit Virtual Environments

When sharing the project or creating a ZIP package for distribution:

- **DO NOT include:**
  - `.venv/` or `venv/`
  - `__pycache__/` folders or `*.pyc` files
  - `.env` local environment files
  - `.vscode/` or `.idea/` editor configurations
  - Local log files or temporary test artifacts
- The recipient should always create their own fresh `.venv` using `requirements.txt` as described in this guide.

---

## 12. Automated Test Verification

To run the automated test suite locally to verify application health:

```powershell
# Run the 5-Document Canonical Dataset Golden Workflow Test:
python scratch/test_canonical_5_dataset.py

# Run UI Pages & Dashboard Regression Test:
python scratch/test_ui_pages_canonical.py

# Run Feature & Filter Verification Test:
python scratch/test_user_requested_fixes.py
```
*(All automated tests run cleanly and report 100% PASS).*
