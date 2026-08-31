# CDTRS Action Agenda & Technical Plan (31-08-2026)

---

## 📋 Part 1: Today's Action Agenda & Tasks

| # | Task Area | What to Do | Internet Needed? | Key Files / Tools |
|---|---|---|---|---|
| **1** | **Model Fine-Tuning Data** | Prepare annotated documents & ground truth labels for OCR & routing | ❌ No (Local prep) | `OCR/training/`, `OCR/rules.py` |
| **2** | **Base Model Download** | Download pre-trained weights once | 🌐 **Yes (Once only)** | `OCR/ocr.py`, `PaddleOCR` |
| **3** | **Fine-Tuning Execution** | Train model on local GPU/CPU | ❌ No (Fully offline) | `OCR/train.py` |
| **4** | **Employee Data Ingestion** | Put employee roster in Excel / CSV or edit JSON seed | ❌ No | `backend/data/seed_data.json`, `backend/import_employees.py` |
| **5** | **Dual Mail Configuration** | Toggle between M365 Cloud and Offline Intranet LAN mail | 🌐 M365: Yes<br>🔒 Intranet: **No (LAN only)** | `backend/.env`, `backend/mail/service.py` |
| **6** | **Database Seed / Reset** | Run one-command database sync | ❌ No | `python backend/seed.py` |

---

## 🧠 Part 2: Data for Model Fine-Tuning (Step-by-Step)

To fine-tune the OCR extraction and department suggestion models for your organization's specific document formats (memos, circulars, official notices):

### Step 1: Collect Sample Documents
- **What to do**: Gather 50–200 real or synthetic sample PDF/image documents representing the departments (Finance, HR, Technical, etc.).
- **Internet Needed**: ❌ **No**.

### Step 2: Annotate Data (Text & Bounding Boxes / Categories)
- **What to do**:
  - **For OCR Text Recognition**: Pair image files with text transcripts (e.g. `image_01.png` → `"Office Memorandum on Travel Allowance..."`).
  - **For Department Routing**: Label text with the ground-truth department (`"Finance"`, `"HR"`, `"Technical"`).
- **Format**: Standard JSONL or TSV format (`{"text": "...", "label": "Finance"}`).
- **Internet Needed**: ❌ **No**.

### Step 3: Download Pre-Trained Weights (One-Time Setup)
- **What to do**: Download base PaddleOCR / LayoutXLM / HuggingFace model weights to local disk.
- **Internet Needed**: 🌐 **Yes (once)** to download model checkpoints (`.pdparams` / PyTorch weights).
- **Files**: Stored in `OCR/models/` or HuggingFace local cache.

### Step 4: Run Fine-Tuning
- **What to do**: Run the local fine-tuning script with your dataset:
  ```bash
  python OCR/train.py --data_dir ./OCR/dataset/ --epochs 30 --output_dir ./OCR/fine_tuned_weights/
  ```
- **Internet Needed**: ❌ **No**. Training runs completely offline on your local machine / GPU.

### Step 5: Plug Fine-Tuned Model into CDTRS
- **What to do**: Update `OCR/ocr.py` to point to `./OCR/fine_tuned_weights/`. The system immediately uses your tuned model for intake extraction.

---

## 📧 Part 3: Employee Data & Outlook vs. Intranet Configuration

CDTRS supports **both cloud and offline environments** with zero code changes:

### 1. Microsoft 365 Cloud Mode (`MAIL_CHANNEL=outlook`)
- **Use Case**: Organization has active Microsoft 365 / Azure AD licenses with internet access.
- **Protocol**: Microsoft Graph REST API.
- **User Emails**: Uses each user's `outlook_email` (e.g., `rahul.sharma@outlook.com` or `@yourcompany.com`).
- **Configuration** in `backend/.env`:
  ```env
  MAIL_CHANNEL=outlook
  OUTLOOK_CLIENT_ID=your-azure-app-client-id
  OUTLOOK_TENANT_ID=your-azure-tenant-id
  OUTLOOK_CLIENT_SECRET=your-azure-client-secret
  OUTLOOK_USER_EMAIL=ds.office@outlook.com
  ```
- **Internet Needed**: 🌐 **Yes**.

### 2. Intranet / LAN / NIC Government Mail Mode (`MAIL_CHANNEL=intranet`)
- **Use Case**: Air-gapped office network, internal LAN mail server, or NIC email (`.nic.in` / `@organization.lan`).
- **Protocol**: Standard Local IMAP (fetching) + SMTP (sending).
- **User Emails**: Uses each user's `gov_email` (e.g., `rahul.sharma@nic.in`).
- **Configuration** in `backend/.env`:
  ```env
  MAIL_CHANNEL=intranet
  INTRANET_IMAP_HOST=mail.internal.nic.in
  INTRANET_IMAP_PORT=993
  INTRANET_SMTP_HOST=smtp.internal.nic.in
  INTRANET_SMTP_PORT=587
  INTRANET_MAIL_USER=ds.office@nic.in
  INTRANET_MAIL_PASSWORD=internal_lan_password
  ```
- **Internet Needed**: ❌ **No** (runs strictly over local office network / intranet).

---

## 📁 Part 4: Dynamic JSON Seeding & Excel-to-JSON Importer

You do **NOT** have to edit any Python code to change employees, departments, or emails. We have built two ready-to-use tools for you:

### Option A: Edit the JSON File Directly
Edit `backend/data/seed_data.json`. It defines all departments and employee records in clean JSON:
```json
{
  "departments": [
    { "name": "Finance", "code": "FIN" },
    { "name": "HR", "code": "HR" },
    { "name": "Technical", "code": "TECH" }
  ],
  "employees": [
    {
      "employee_code": "EMP-FIN-001",
      "username": "emp_rahul",
      "full_name": "Rahul Sharma",
      "department": "Finance",
      "designation": "Accounts Officer",
      "email": "rahul.sharma@cdtrs.gov.in",
      "outlook_email": "rahul.sharma@outlook.com",
      "gov_email": "rahul.sharma@nic.in",
      "default_password": "cdtrs@emp"
    }
  ]
}
```

### Option B: Import Directly from an Excel (`.xlsx`) or CSV File!
We created `backend/import_employees.py`.

If you have an Excel sheet (e.g., `roster.xlsx`) with columns:
| Full Name | Department | Designation | Outlook Email | Gov Email | Password |
|---|---|---|---|---|---|
| Priya Patel | Finance | Senior Auditor | priya@outlook.com | priya@nic.in | cdtrs@emp |

Just run:
```bash
python backend/import_employees.py roster.xlsx --seed-db
```
**What this does automatically:**
1. Reads all employee rows from your Excel/CSV.
2. Auto-detects new departments and adds them.
3. Updates `backend/data/seed_data.json`.
4. Seeds the database immediately with `--seed-db`.

### Option C: Run Database Seed Anytime
```bash
python backend/seed.py
```
*(Add `--reset` if you want a clean database wipe and re-seed)*.
