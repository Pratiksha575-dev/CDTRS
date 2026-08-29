# CDTRS V2 — Complete Setup Guide for New Computers & Final Changes Summary
**Date:** 26 August 2026  
**Author / Identifier:** PZ_26/08  
**Repository:** CDTRS-master

---

## 1. Quick Start: Running on Any New PC (Zero Friction)

If you download the repository as a **Git ZIP** on a new office computer or test machine, follow these steps:

### Prerequisites:
1. **Python 3.10+** installed (check 'Add python.exe to PATH' during installation).
2. **PostgreSQL** installed and running.
3. Install Python dependencies:
   `ash
   pip install -r requirements.txt
   `

---

### 🚀 3-Step Setup on a New Computer:

#### Step 1: Create Backend Environment File
Open PowerShell in the project root:
`powershell
cd backend
copy .env.example .env
`
*(Verify your local PostgreSQL password in ackend/.env if different from default postgres:fctd).*

#### Step 2: Initialize & Seed Database (Zero Dummy Documents)
`powershell
python seed.py
`
This automatically:
- Creates all required PostgreSQL tables.
- Seeds 6 official departments.
- Seeds 9 staff accounts with email identities.
- Leaves the document queue completely fresh (0 dummy documents).

#### Step 3: Launch Backend & Desktop Frontend

* **Terminal 1 (Backend Server):**
  `powershell
  cd backend
  python -m uvicorn main:app --reload
  `

* **Terminal 2 (Desktop Application):**
  `powershell
  cd frontend
  python main.py
  `

---

## 2. Microsoft Outlook Mailbox Integration on a New PC

### ⚡ Method A: Zero-Login (Easiest for Office Demos)
If you include the file ackend/mail/.token_cache.json in your ZIP or folder copy:
- **No login, no code, and no phone verification will EVER be prompted on that computer!**
- The backend automatically uses the cached OAuth2 token and keeps it refreshed rolling in the background.

### 🔑 Method B: 1-Time 10-Second Microsoft Device Code
If running from a clean git clone without the token file:
1. Open PowerShell and run:
   `powershell
   python backend/mail/auth_personal.py
   `
2. Open https://microsoft.com/devicelogin (on the PC or on your phone), enter the 8-letter code, and click **Accept**.
3. Done! The token is saved permanently on that computer.

### 🏢 Method C: Enterprise / Production Deployment (Microsoft 365 / Azure Entra ID)
When deploying in the real institution for the official mailbox:
1. Open ackend/.env and fill the organizational Azure credentials:
   `env
   OUTLOOK_AUTH_MODE=organizational
   OUTLOOK_TENANT_ID=<azure-tenant-guid>
   OUTLOOK_CLIENT_ID=<azure-client-id>
   OUTLOOK_CLIENT_SECRET=<azure-client-secret>
   OUTLOOK_MAILBOX=ds.office@cdtrs.gov.in
   `
2. The server connects 24/7 in the background with zero user interaction.

---

## 3. Available Staff Accounts & Default Passwords

| Username | Full Name | Role | Department | Default Password | Configured Email |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ds_user** | Director Secretary | DS | Administration | cdtrs@ds | pratiksha.cdtrs@outlook.com |
| **director** | The Director | DIRECTOR | Directorate | cdtrs@director | pratikshazodge575@gmail.com |
| **hod_finance** | Head of Finance | HOD | Finance | cdtrs@hod | pratikshazodge575@gmail.com |
| **hod_procurement** | Head of Procurement | HOD | Procurement | cdtrs@hod | pratikshazodge575@gmail.com |
| **hod_tech** | Head of Technical | HOD | Technical | cdtrs@emp | pratikshazodge575@gmail.com |
| **hod_hr** | Head of HR | HOD | Human Resources | cdtrs@emp | pratikshazodge575@gmail.com |
| **emp_rahul** | Rahul Sharma | EMPLOYEE | Finance | cdtrs@emp | pratikshazodge575@gmail.com |
| **emp_priya** | Priya Verma | EMPLOYEE | Procurement | cdtrs@emp | pratikshazodge575@gmail.com |
| **emp_anil** | Anil Kumar | EMPLOYEE | Technical | cdtrs@emp | pratikshazodge575@gmail.com |

---

## 4. File-by-File Summary of All Changes (PZ_26/08)

All modified and newly created files contain # PZ_26/08 marker comments:

| File Path | Status | Key Changes Made (PZ_26/08) | Architectural Purpose |
| :--- | :--- | :--- | :--- |
| ackend/mail/base.py | **Created** | Abstract BaseMailProvider interface + typed DTOs (IncomingEmailDTO, OutgoingEmailDTO, EmailAttachmentDTO). | Extensible provider contract for Outlook & Government Mail. |
| ackend/mail/outlook_provider.py | **Created** | Dual-mode Microsoft Graph API v1.0 provider (Device Code for testing + Client Credentials for Entra ID). | Secure Microsoft Graph mail ingestion and /sendMail dispatch. |
| ackend/mail/service.py | **Created** | Central MailService domain orchestrator with duplicate suppression, SHA-256 hashing, and attachment forwarding. | End-to-end mail workflow and attachment management. |
| ackend/mail/auth_personal.py | **Created** | Microsoft OAuth 2.0 Device Code CLI authenticator with automatic token caching. | One-time 10-second personal Outlook setup with zero Azure setup. |
| ackend/mail/__init__.py | **Created** | Symbol exports for mail subsystem. | Clean modular packaging. |
| ackend/models.py | **Modified** | Added email, outlook_email, gov_email, preferred_mail_channel to User and Employee; made Attachment.document_id nullable. | Database schema support for pre-intake storage and staff emails. |
| ackend/schemas.py | **Modified** | Added OutlookSyncResponse, ReminderSendRequest, ReminderSendResponse. | Typed Pydantic serialization for API endpoints. |
| ackend/crud.py | **Modified** | Added process_intake_to_document() attachment re-linking; send_document_reminder() dynamic recipient routing; clean seeding (0 dummy docs). | Core domain and database operations. |
| ackend/main.py | **Modified** | Added /api/v1/intake/sync-outlook and /api/v1/documents/{id}/remind; periodic background auto-sync lifespan. | Real-time continuous server auto-sync and REST endpoints. |
| ackend/seed.py | **Modified** | Updated seed runner to initialize clean database with departments and user logins only. | Production-ready fresh database seeding. |
| ackend/.env.example | **Modified** | Added complete Dual-Mode Outlook configuration variables and clear comments. | Copy-paste configuration template for new setups. |
| rontend/api/endpoints.py | **Modified** | Added INTAKE_SYNC_OUTLOOK and DOCUMENT_REMIND. | API endpoint constants. |
| rontend/models/user.py | **Modified** | Added email attributes to client-side UserModel. | Client user representation. |
| rontend/repositories/base.py | **Modified** | Added abstract sync_outlook() and send_document_reminder() definitions. | Repository interface contract. |
| rontend/repositories/api_repository.py | **Modified** | Implemented sync_outlook() and send_document_reminder() REST API calls. | Live backend communication. |
| rontend/repositories/mock_repository.py | **Modified** | Implemented mock fallbacks for standalone/offline operation. | Offline testing support. |
| rontend/services/notification_service.py | **Modified** | Connected send_action_reminder() to repository dispatch. | Frontend notification service. |
| rontend/pages/inbox.py | **Modified** | Added periodic background auto-sync timer (30s), live sync status badge (🟢 Auto-Synced), and manual Sync button. | Real-time DS inbox queue. |
| rontend/components/document_viewer.py | **Modified** | Enhanced _ds_send_reminder() to display recipient role, resolved email, and delivery status. | Interactive DS action reminder feedback. |
| rontend/components/document_preview.py | **Modified** | Upgraded to hardware-accelerated **QPdfView / QPdfDocument** renderer with zoom, fit, and page controls. | Native in-app PDF preview on any client machine. |

---

## 5. Key Verification Highlights

1. **Server-Relative Storage**: Attachments are stored as ./uploads/<year>/intake_<msg_id>/<filename>. No hardcoded local PC paths (C:\Users\...) exist.
2. **Network Preview/Download**: Any client PC on the LAN can view and download documents streamed from the server API.
3. **Outgoing Attachments**: Reminders dispatched via Microsoft Graph /sendMail include the document's original PDF file as a real email attachment.
4. **Idempotent Ingestion**: Syncing duplicate emails is suppressed using external_message_id and SHA-256 checksums.
