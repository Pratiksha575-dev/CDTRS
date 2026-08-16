# Canonical Demonstration Documents (5-Document Dataset)

This document specifies the exact fields, metadata, and initial state for the 5 canonical demonstration documents.

---

## 1. Initial State Summary Matrix

| ID | Reference Number | Title | Priority | Stage | Status | Owner | Suggestion | Director Directive | Deadline | Attachments |
|:---:|:---|:---|:---:|:---:|:---:|:---|:---|:---|:---:|:---:|
| **1** | `CDTRS-2026-0001` | National Higher Education Accreditation & Governance Compliance Directive | `Medium` | `DS` | `Received` | Director Secretary | *None* | *None* | *None* | 1 (`.pdf`) |
| **2** | `CDTRS-2026-0002` | Q3 Financial Audit & Capital Grant Disbursement Notice | `High` | `DS` | `Received` | Director Secretary | Dept: Finance (ID: 1) | *None* | *None* | 2 (`.pdf`, `.xlsx`) |
| **3** | `CDTRS-2026-0003` | Statutory Vendor Tax Clearance & Procurement Verification | `High` | `DS` | `Received` | Director Secretary | Dept: Finance, Emp: Rahul Sharma (101) | *None* | *None* | 1 (`.pdf`) |
| **4** | `CDTRS-2026-0004` | Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed) | `High` | `DS` | `Received` | Director Secretary | Dept: Finance, Emp: Rahul Sharma (101) | *"Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."* | *None* | 1 (`.pdf`) |
| **5** | `CDTRS-2026-0005` | High-Priority Enterprise Server Maintenance & Firewall Compliance | `High` | `DS` | `Received` | Director Secretary | Dept: IT (ID: 5) | *None* | `+7 days` | 2 (`.pdf`, `.xlsx`) |

---

## 2. Comprehensive Field-by-Field Specifications

### Document 1: Fresh / Normal Workflow
- **ID**: `1`
- **Reference Number**: `"CDTRS-2026-0001"`
- **Title / Subject**: `"National Higher Education Accreditation & Governance Compliance Directive"`
- **Source / Sender**: `"Ministry of Higher Education"`
- **Ingestion Mode**: `"Outlook / Government Mail"`
- **Priority**: `"Medium"`
- **Deadline**: `None`
- **Status**: `"Received"`
- **Current Stage**: `"DS"`
- **Current Owner ID**: `1` (`"Director Secretary"`)
- **Target Department**: `None`
- **Assigned Employee**: `None`
- **Suggested Department**: `None`
- **Suggested Employee**: `None`
- **Director Remark**: `None`
- **HOD Remark**: `None`
- **Has Prior Director Remark**: `False`
- **Has Director Routing Instruction**: `False`
- **Routing Confidence**: `0`
- **File Path**: `"data/incoming/government_mail/accreditation_compliance_directive.pdf"`
- **File Type / Format**: `"PDF"`
- **Attachment Count**: `1`
- **Attachments List**: `["accreditation_compliance_directive.pdf"]`
- **Initial History Record**: Action `"Document Ingested"`, Performed By User `1` (`"DS"`), Remarks `"Document CDTRS-2026-0001 registered into repository."`

---

### Document 2: Department Suggestion
- **ID**: `2`
- **Reference Number**: `"CDTRS-2026-0002"`
- **Title / Subject**: `"Q3 Financial Audit & Capital Grant Disbursement Notice"`
- **Source / Sender**: `"State Audit Bureau"`
- **Ingestion Mode**: `"Internet / Web Portal"`
- **Priority**: `"High"`
- **Deadline**: `None`
- **Status**: `"Received"`
- **Current Stage**: `"DS"`
- **Current Owner ID**: `1` (`"Director Secretary"`)
- **Target Department**: `None`
- **Assigned Employee**: `None`
- **Suggested Department ID**: `1`
- **Suggested Department Name**: `"Finance"`
- **Suggested Employee**: `None`
- **Director Remark**: `None`
- **HOD Remark**: `None`
- **Has Prior Director Remark**: `False`
- **Has Director Routing Instruction**: `False`
- **Routing Confidence**: `94`
- **File Path**: `"data/incoming/government_mail/audit_disbursement_notice.pdf"`
- **File Type / Format**: `"PDF"`
- **Attachment Count**: `2`
- **Attachments List**: `["audit_disbursement_notice.pdf", "capital_grant_schedule.xlsx"]`
- **Initial History Record**: Action `"Document Ingested"`, Performed By User `1` (`"DS"`), Remarks `"Document CDTRS-2026-0002 registered into repository."`

---

### Document 3: Department + Employee Suggestion
- **ID**: `3`
- **Reference Number**: `"CDTRS-2026-0003"`
- **Title / Subject**: `"Statutory Vendor Tax Clearance & Procurement Verification"`
- **Source / Sender**: `"Central Board of Direct Taxes"`
- **Ingestion Mode**: `"Fax"`
- **Priority**: `"High"`
- **Deadline**: `None`
- **Status**: `"Received"`
- **Current Stage**: `"DS"`
- **Current Owner ID**: `1` (`"Director Secretary"`)
- **Target Department**: `None`
- **Assigned Employee**: `None`
- **Suggested Department ID**: `1`
- **Suggested Department Name**: `"Finance"`
- **Suggested Employee ID**: `101`
- **Suggested Employee Name**: `"Rahul Sharma"`
- **Director Remark**: `None`
- **HOD Remark**: `None`
- **Has Prior Director Remark**: `False`
- **Has Director Routing Instruction**: `False`
- **Routing Confidence**: `95`
- **File Path**: `"data/incoming/government_mail/vendor_tax_clearance.pdf"`
- **File Type / Format**: `"PDF"`
- **Attachment Count**: `1`
- **Attachments List**: `["vendor_tax_clearance.pdf"]`
- **Initial History Record**: Action `"Document Ingested"`, Performed By User `1` (`"DS"`), Remarks `"Document CDTRS-2026-0003 registered into repository."`

---

### Document 4: Pre-Reviewed / Director Remark Present
- **ID**: `4`
- **Reference Number**: `"CDTRS-2026-0004"`
- **Title / Subject**: `"Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed)"`
- **Source / Sender**: `"Office of the Director"`
- **Ingestion Mode**: `"Physical / Scanned PDF"`
- **Priority**: `"High"`
- **Deadline**: `None`
- **Status**: `"Received"`
- **Current Stage**: `"DS"`
- **Current Owner ID**: `1` (`"Director Secretary"`)
- **Target Department**: `None`
- **Assigned Employee**: `None`
- **Suggested Department ID**: `1`
- **Suggested Department Name**: `"Finance"`
- **Suggested Employee ID**: `101`
- **Suggested Employee Name**: `"Rahul Sharma"`
- **Director Remark**: `"Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."`
- **HOD Remark**: `None`
- **Has Prior Director Remark**: `True`
- **Has Director Routing Instruction**: `True`
- **Director Routing Raw Text**: `"Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."`
- **Routing Confidence**: `96`
- **File Path**: `"data/incoming/scans/security_infrastructure_upgrade.pdf"`
- **File Type / Format**: `"Scanned PDF"`
- **Attachment Count**: `1`
- **Attachments List**: `["security_infrastructure_upgrade.pdf"]`
- **Initial History Record**: Action `"Document Ingested"`, Performed By User `1` (`"DS"`), Remarks `"Document CDTRS-2026-0004 registered into repository."`

---

### Document 5: Urgent / Strict Deadline Tracking
- **ID**: `5`
- **Reference Number**: `"CDTRS-2026-0005"`
- **Title / Subject**: `"High-Priority Enterprise Server Maintenance & Firewall Compliance"`
- **Source / Sender**: `"Cyber Security Directorate"`
- **Ingestion Mode**: `"Internet / Web Portal"`
- **Priority**: `"High"`
- **Deadline**: `<CURRENT_DATE + 7 DAYS>` (e.g. `2026-08-23`)
- **Status**: `"Received"`
- **Current Stage**: `"DS"`
- **Current Owner ID**: `1` (`"Director Secretary"`)
- **Target Department**: `None`
- **Assigned Employee**: `None`
- **Suggested Department ID**: `5`
- **Suggested Department Name**: `"IT"`
- **Suggested Employee**: `None`
- **Director Remark**: `None`
- **HOD Remark**: `None`
- **Has Prior Director Remark**: `False`
- **Has Director Routing Instruction**: `False`
- **Routing Confidence**: `92`
- **File Path**: `"data/incoming/outlook/server_maintenance_compliance.pdf"`
- **File Type / Format**: `"PDF"`
- **Attachment Count**: `2`
- **Attachments List**: `["server_maintenance_compliance.pdf", "firewall_rules.xlsx"]`
- **Initial History Record**: Action `"Document Ingested"`, Performed By User `1` (`"DS"`), Remarks `"Document CDTRS-2026-0005 registered into repository."`
