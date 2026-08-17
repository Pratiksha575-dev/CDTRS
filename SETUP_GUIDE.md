# CDTRS — Complete Windows Setup & Multi-PC Deployment Guide

Comprehensive guide for setting up, configuring, and executing the **CDTRS (Centralised Document Tracking and Routing System)** across single and multi-machine network environments.

---

## 1. Project Directory Structure

The project is cleanly divided into decoupled **`frontend/`** (PySide6 Desktop Application) and **`backend/`** (FastAPI REST Server & PostgreSQL / SQLite Engine) modules:

```text
CDTRS/
├── backend/                             # FastAPI Backend Service
│   ├── main.py                          # FastAPI Application Server & Route Endpoints
│   ├── models.py                        # SQLAlchemy Database Models & Relationships
│   ├── crud.py                          # Workflow Engine, Event Logging & State Operations
│   ├── schemas.py                       # Pydantic Validation & Serialization Schemas
│   ├── database.py                      # Database Engine, Session Maker & Base
│   ├── seed.py                          # Database Table Creation & User Seeding Script
│   ├── clear_documents.py               # Clean Slate Test Database Reset Script
│   ├── requirements.txt                 # Backend Python Dependencies
│   ├── .env.example                     # Backend Environment Variable Template
│   └── .env                             # Active Backend Configuration
│
├── frontend/                            # PySide6 Desktop Application
│   ├── main.py                          # Desktop Application Executable Entry Point
│   ├── api/                             # REST API Client, Endpoints & Network Handlers
│   ├── components/                      # Reusable UI Widgets (Table, Document Viewer, Dialogs)
│   ├── config/                          # Settings & Automatic .env Environment Resolver
│   ├── models/                          # Typed Domain Models, Dataclasses & Enums
│   ├── pages/                           # Role-Specific Dashboard & Workflow Pages
│   ├── repositories/                    # Repository Pattern (APIRepository & MockRepository)
│   ├── services/                        # Business Logic (Auth, Routing, OCR, Notifications)
│   ├── styles/                          # Global QSS Theme Stylesheet (theme.qss)
│   ├── ui/                              # Application Shell Window, Login Window & Sidebar
│   ├── requirements.txt                 # Frontend Python Dependencies
│   ├── .env.example                     # Frontend Environment Variable Template
│   └── .env                             # Active Frontend Configuration
│
├── main.py                              # Root Application Launcher (Delegates to frontend)
├── requirements.txt                     # Unified Dependencies
└── SETUP_GUIDE.md                       # This Setup & Multi-PC Deployment Guide
```

---

## 2. Prerequisites

Ensure the following are installed on your machine:
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python **3.10+** (Ensure *"Add python.exe to PATH"* was checked during installation).
- **Database:** PostgreSQL (or SQLite fallback).

---

## 3. Quick Setup (Single Local PC)

Follow these steps to run both Backend and Frontend on the same machine:

### Step 1: Open PowerShell and Create Virtual Environment
```powershell
# Navigate to the project root directory
cd "C:\path\to\CDTRS"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

> **PowerShell Script Policy Note:** If you get a script execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### Step 2: Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 3: Initialize Database & Seed Default Accounts
```powershell
# Creates all PostgreSQL tables and seeds default user accounts
python backend/seed.py
```

### Step 4: Start Backend Server (Terminal 1)
```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
*Your FastAPI backend is now running at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs`.*

### Step 5: Launch Desktop Frontend (Terminal 2)
In a second PowerShell window:
```powershell
# Navigate to project and activate virtual environment
cd "C:\path\to\CDTRS"
.\.venv\Scripts\Activate.ps1

# Launch Desktop App
python frontend/main.py
```
*(You can also run `python main.py` from the root directory).*

---

## 4. Connecting to a Different Backend Server / Another PC on LAN

To run the **Backend on PC A (Server)** and connect the **Frontend from PC B (Client PC)** across your local Wi-Fi or Office Network:

```mermaid
flowchart LR
    subgraph Server_PC ["PC A — Server (IP: 192.168.1.50)"]
        DB[(PostgreSQL)]
        API["FastAPI Backend (Port 8000)"]
        DB --> API
    end

    subgraph Client_PC ["PC B — Client PC"]
        App["PySide6 Desktop App"]
        Env[".env: CDTRS_API_URL=http://192.168.1.50:8000/api/v1"]
        Env --> App
    end

    App -- "HTTP REST Requests" --> API
```

### On PC A (Server Running the Backend):

1. **Find PC A's Local IP Address:**
   In PowerShell on PC A, run:
   ```powershell
   ipconfig
   ```
   Look for the **IPv4 Address** under your active Wi-Fi or Ethernet adapter (e.g., `192.168.1.50`).

2. **Configure Backend `.env` on PC A:**
   In `backend/.env`:
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:fctd@localhost:5432/cdtrs
   HOST=0.0.0.0
   PORT=8000
   CORS_ORIGINS=*
   ```

3. **Start the Backend Server bound to `0.0.0.0`:**
   ```powershell
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Allow Port 8000 in Windows Firewall (if prompted):**
   When Windows Firewall prompts, click **"Allow Access"** on Private Networks, or run:
   ```powershell
   New-NetFirewallRule -DisplayName "CDTRS Backend Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

---

### On PC B (Client PC Running the Desktop App):

1. **Copy the `CDTRS/` folder or `frontend/` folder to PC B.**
2. **Install Frontend Dependencies on PC B:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r frontend/requirements.txt
   ```

3. **Update `frontend/.env` on PC B to point to PC A's IP:**
   Open `frontend/.env` and update `CDTRS_API_URL`:
   ```ini
   # Set to PC A's IP address:
   CDTRS_API_URL=http://192.168.1.50:8000/api/v1
   CDTRS_DATA_SOURCE=api
   ```

4. **Launch the Desktop App on PC B:**
   ```powershell
   python frontend/main.py
   ```
   The client app will connect seamlessly to the live backend running on PC A!

---

## 5. Environment Variables Reference

### Frontend Environment Variables (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `CDTRS_API_URL` | `http://127.0.0.1:8000/api/v1` | Base URL of the backend API service. Replace with remote/LAN IP as needed. |
| `CDTRS_DATA_SOURCE` | `api` | Data source mode: `api` for live backend, `mock` for offline in-memory demo. |
| `CDTRS_API_TIMEOUT` | `15.0` | Network request timeout in seconds. |

### Backend Environment Variables (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:fctd@localhost:5432/cdtrs` | SQLAlchemy PostgreSQL connection string. |
| `HOST` | `0.0.0.0` | Host IP binding (`0.0.0.0` allows LAN connections). |
| `PORT` | `8000` | Port for the FastAPI HTTP server. |
| `SECRET_KEY` | `cdtrs-super-secret-key-2026` | Cryptographic secret for signing JWT auth tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT access token session validity (in minutes). |
| `CORS_ORIGINS` | `*` | Allowed CORS origins for cross-origin client requests. |

---

## 6. Pre-Configured Test User Accounts

The database comes pre-seeded with canonical institutional accounts for all lifecycle roles:

| Username | Role | Default Password | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **`ds_user`** | Director Secretary (DS) | `cdtrs@ds` | Document Ingestion, Initial Routing, Department Delegation, Closure |
| **`director`** | Executive Director | `cdtrs@director` | Executive Review, Strategic Directives, Returning Remarks |
| **`hod_finance`** | Head of Finance | `cdtrs@hod` | Departmental Intake, Task Assignment to Staff |
| **`hod_procurement`** | Head of Procurement | `cdtrs@hod` | Departmental Intake, Procurement Delegation |
| **`emp_rahul`** | Employee (Finance Staff) | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |
| **`emp_priya`** | Employee (Procurement Staff) | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |

---

## 7. Useful Operational Commands

### Reset Database to 0 Documents (Clean Slate Testing):
```powershell
python backend/clear_documents.py
```
*Deletes all test documents and reset audit trails while preserving user accounts and department structures.*

### Re-Seed Initial Canonical Documents:
```powershell
python backend/seed.py
```

### Run Frontend in Standalone Offline Mock Mode:
In `frontend/.env`, set:
```ini
CDTRS_DATA_SOURCE=mock
```
Then run `python frontend/main.py`. The application will run entirely in memory with no backend or database requirement.

---

## 8. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Could not connect to server"** | Backend is not running or incorrect IP in `.env`. | Verify backend is running (`python -m uvicorn main:app`). Check that `CDTRS_API_URL` matches the backend host and port. |
| **"Connection Timed Out across LAN"** | Windows Firewall on the Server PC is blocking Port 8000. | On the Server PC, open Windows Firewall and create an Inbound Rule allowing TCP port `8000`. |
| **"psycopg2.OperationalError: connection to server failed"** | PostgreSQL service is stopped. | Open Windows Services (`services.msc`), find `postgresql-x64`, and click **Start**. |
| **"ModuleNotFoundError: No module named 'PySide6'"** | Virtual environment is not activated or dependencies missing. | Activate the virtual environment (`.\.venv\Scripts\Activate.ps1`) and run `pip install -r requirements.txt`. |
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload