# CDTRS — Complete Windows Setup & Multi-PC Deployment Guide

Comprehensive guide for setting up, configuring, and executing the **CDTRS (Centralised Document Tracking and Routing System)** across single and multi-machine network environments.

---

## 1. Project Directory Structure

The project is divided into decoupled **`frontend/`** (PySide6 Desktop Application), **`backend/`** (FastAPI REST Server & PostgreSQL Engine), and **`OCR/`** (PaddleOCR & Rule Heuristics Engine) modules:

```text
CDTRS/
├── backend/                             # FastAPI Backend Service
│   ├── main.py                          # FastAPI Application Server, REST Endpoints & WebSockets
│   ├── models.py                        # SQLAlchemy Database Models (17 Tables & Enums)
│   ├── crud.py                          # Workflow Engine, Event Logging & Routing Logic
│   ├── schemas.py                       # Pydantic Validation & Serialization Schemas
│   ├── database.py                      # Database Engine, Session Maker & Connection Pool
│   ├── seed.py                          # Database Table Creation & User Seeding Script
│   ├── clear_documents.py               # Clean Slate Test Database Reset Script
│   ├── requirements.txt                 # Backend Python Dependencies
│   ├── .env                             # Active Backend Configuration
│   └── readme.md                        # Comprehensive Backend Documentation
│
├── frontend/                            # PySide6 Desktop Application
│   ├── main.py                          # Desktop Application Executable Entry Point
│   ├── api/                             # REST API Client, Endpoints & Network Handlers
│   ├── components/                      # Reusable UI Widgets (Table, Document Viewer, Dialogs)
│   ├── config/                          # Settings & Automatic .env Resolver
│   ├── models/                          # Typed Domain Models, Dataclasses & Enums
│   ├── pages/                           # Role-Specific Dashboard & Workflow Pages
│   ├── repositories/                    # Repository Pattern (APIRepository & MockRepository)
│   ├── services/                        # Business Logic (Auth, Routing, OCR, Notifications)
│   ├── styles/                          # Global QSS Theme Stylesheet (theme.qss)
│   ├── ui/                              # Application Shell Window, Login Window & Sidebar
│   ├── requirements.txt                 # Frontend Python Dependencies
│   └── .env                             # Active Frontend Configuration
│
├── OCR/                                 # PaddleOCR & Rule Extraction Pipeline
│   ├── ocr.py                           # PaddleOCR Engine & PDF / Image Text Extractor
│   ├── rules.py                         # Regex & Rule-Based Metadata Extractor
│   ├── main.py                          # OCR Extraction Runner & Heuristics
│   └── smoke_test.py                    # Verification Test Script for OCR
│
├── scratch/                             # Verification & Automated Test Suites
├── main.py                              # Root Application Launcher (Delegates to frontend)
├── requirements.txt                     # Unified Dependencies (Frontend + Backend + OCR)
├── SETUP_GUIDE.md                       # This Setup & Multi-PC Deployment Guide
└── readme.md                            # Complete Technical & Architectural Documentation
```

---

## 2. Prerequisites

Ensure the following are installed on your machine:
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python **3.10+** (Ensure *"Add python.exe to PATH"* was checked during installation).
- **Database:** PostgreSQL 14–16 installed locally or accessible via network.
- **Git / Terminal:** PowerShell or Windows Terminal.

---

## 3. Quick Setup (Single Local PC)

Follow these steps to run both Backend and Frontend on the same machine:

### Step 1: Open PowerShell and Create Virtual Environment
```powershell
# Navigate to the project root directory
cd "c:\CDTRS-master"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

> **PowerShell Script Policy Note:** If you encounter a script execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### Step 2: Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 3: Configure Environment Files & Database
1. **Create Backend `.env` file:**
   In the root or backend directory, copy the template:
   ```powershell
   # In c:\CDTRS-master:
   copy backend\.env.example backend\.env
   ```
   Open [`backend/.env`](file:///c:/CDTRS-master/backend/.env) and verify your PostgreSQL credentials:
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:nmrl@localhost:5432/cdtrs
   ```

2. **Create Frontend `.env` file:**
   ```powershell
   # In c:\CDTRS-master:
   copy frontend\.env.example frontend\.env
   ```
   Open [`frontend/.env`](file:///c:/CDTRS-master/frontend/.env) and confirm the backend URL:
   ```ini
   CDTRS_DATA_SOURCE=api
   CDTRS_API_URL=http://127.0.0.1:8000/api/v1
   ```

3. **Initialize the database schema and seed default user accounts:**
   Ensure PostgreSQL is running, then run:
   ```powershell
   python backend/seed.py
   ```

### Step 4: Start Backend Server (Terminal 1)
```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
*Your FastAPI backend is now running at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs` and WebSocket stream at `ws://127.0.0.1:8000/api/v1/ws`.*

### Step 5: Launch Desktop Frontend (Terminal 2)
In a second PowerShell window:
```powershell
# Navigate to project and activate virtual environment
cd "c:\CDTRS-master"
.\.venv\Scripts\Activate.ps1

# Launch Desktop App
python main.py
```
*(Alternatively, you can run `python frontend/main.py`).*

---

## 4. Connecting Across Local Network (Multi-PC LAN Deployment)

To run the **Backend on PC A (Server)** and connect the **Frontend from PC B (Client PC)** across your office Wi-Fi or local area network:

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

    App -- "REST API & WebSocket" --> API
```

### On PC A (Server Running the Backend):

1. **Find PC A's Local IP Address:**
   In PowerShell on PC A, run:
   ```powershell
   ipconfig
   ```
   Look for the **IPv4 Address** under your active Wi-Fi or Ethernet adapter (e.g. `192.168.1.50`).

2. **Configure Backend `.env` on PC A:**
   In [`backend/.env`](file:///c:/CDTRS-master/backend/.env):
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:nmrl@localhost:5432/cdtrs
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
   When Windows Firewall prompts, click **"Allow Access"** on Private Networks, or run in PowerShell (as Administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "CDTRS Backend Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

---

### On PC B (Client PC Running the Desktop App):

1. **Copy the `CDTRS` project folder to PC B.**
2. **Install Frontend Dependencies on PC B:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r frontend/requirements.txt
   ```

3. **Update `frontend/.env` on PC B to point to PC A's IP:**
   Open `frontend/.env` and update `CDTRS_API_URL`:
   ```ini
   CDTRS_API_URL=http://192.168.1.50:8000/api/v1
   CDTRS_DATA_SOURCE=api
   ```

4. **Launch the Desktop App on PC B:**
   ```powershell
   python main.py
   ```
   The client application will connect seamlessly to the live backend running on PC A.

---

## 5. Environment Variables Reference

### Frontend Environment Variables ([`frontend/.env`](file:///c:/CDTRS-master/frontend/.env))

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `CDTRS_API_URL` | `http://127.0.0.1:8000/api/v1` | Base URL of backend REST API service. Set to remote/LAN IP for network clients. |
| `CDTRS_DATA_SOURCE` | `api` | Data source mode: `api` for live backend, `mock` for offline in-memory demo. |
| `CDTRS_API_TIMEOUT` | `15.0` | Network request timeout in seconds. |
| `CDTRS_APP_NAME` | `CDTRS` | Application window title. |
| `CDTRS_APP_VERSION` | `2.0.0` | Application version string. |

### Backend Environment Variables ([`backend/.env`](file:///c:/CDTRS-master/backend/.env))

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:nmrl@localhost:5432/cdtrs` | SQLAlchemy PostgreSQL connection string. |
| `HOST` | `0.0.0.0` | Host IP binding (`0.0.0.0` allows LAN connections). |
| `PORT` | `8000` | Port for the FastAPI HTTP server. |
| `SECRET_KEY` | `cdtrs-super-secret-key-change-in-production-2026` | Cryptographic secret for signing JWT auth tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT access token session validity (in minutes). |
| `MAX_FILE_SIZE` | `20971520` | Max file upload limit in bytes (20 MB default). |
| `CORS_ORIGINS` | `*` | Allowed CORS origins for cross-origin client requests. |

---

## 6. Pre-Configured Test User Accounts

The database comes pre-seeded with canonical institutional accounts for all lifecycle roles:

| Username | Role | Department | Default Password | Primary Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **`ds_user`** | Director Secretary (DS) | Administration | `cdtrs@ds` | Document Ingestion, Initial Routing, Department Delegation, Closure |
| **`director`** | Executive Director | Executive | `cdtrs@director` | Executive Review, Strategic Directives, Returning Remarks |
| **`hod_finance`** | Head of Department | Finance | `cdtrs@hod` | Departmental Intake, Task Assignment to Staff |
| **`hod_procurement`** | Head of Department | Procurement | `cdtrs@hod` | Departmental Intake, Procurement Delegation |
| **`emp_rahul`** | Employee Staff | Finance | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |
| **`emp_priya`** | Employee Staff | Procurement | `cdtrs@emp` | Task Execution, Progress Report & Attachment Submission |

---

## 7. Useful Operational Commands

### Reset Database to 0 Documents (Clean Slate Testing):
```powershell
python backend/clear_documents.py
```
*Deletes all test documents and resets audit trails while preserving user accounts and department structures.*

### Re-Seed Initial Database & Users:
```powershell
python backend/seed.py
```

### Verify PaddleOCR Engine & Text Extraction:
```powershell
python OCR/smoke_test.py
```

### Ingest Real Institutional Data:
For a step-by-step guide on importing real organizational departments, staff accounts, and historical documents via Python scripts or CSV spreadsheets, refer to:
👉 **[DATA_MANAGEMENT_GUIDE.md](file:///c:/CDTRS-master/DATA_MANAGEMENT_GUIDE.md)**

### Run Frontend in Standalone Offline Mock Mode:
In `frontend/.env`, set:
```ini
CDTRS_DATA_SOURCE=mock
```
Then run `python main.py`. The application will run entirely in memory with no backend or database requirement.

---

## 8. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Could not connect to server"** | Backend is not running or incorrect IP in `.env`. | Verify backend is running (`python -m uvicorn main:app`). Check that `CDTRS_API_URL` matches the backend host and port. |
| **"Connection Timed Out across LAN"** | Windows Firewall on the Server PC is blocking Port 8000. | On the Server PC, open Windows Firewall and create an Inbound Rule allowing TCP port `8000`. |
| **"psycopg2.OperationalError: connection to server failed"** | PostgreSQL service is stopped or wrong password. | Open Windows Services (`services.msc`), find `postgresql-x64`, and start it. Verify username and password in `backend/.env`. |
| **"ModuleNotFoundError: No module named 'PySide6'"** | Virtual environment is not activated or dependencies missing. | Activate the virtual environment (`.\.venv\Scripts\Activate.ps1`) and run `pip install -r requirements.txt`. |
| **PaddleOCR / OneDNN Informational Messages** | Normal informational logging from PaddlePaddle backend. | These messages (`ReduceMeanCheckIfOneDNNSupport`, etc.) are normal CPU acceleration notices and do not indicate an error. |