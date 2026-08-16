# Canonical Attachments & OCR Processing Specification

This document defines the attachment storage model, file metadata structures, and OCR extraction contracts in the CDTRS system.

---

## 1. Attachment Data Model

CDTRS supports multiple file attachments per document across two distinct lifecycle categories:
1. **`ORIGINAL`**: Initial scanned dispatches, official PDFs, and annexures uploaded during intake.
2. **`WORKFLOW`**: Supporting files, reports, proof of completion, and vouchers uploaded by employees during progress updates.

### Database Table: `attachments`
```sql
CREATE TABLE attachments (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    progress_update_id INTEGER REFERENCES progress_updates(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    category VARCHAR(50) DEFAULT 'ORIGINAL', -- 'ORIGINAL' or 'WORKFLOW'
    source VARCHAR(255),                     -- 'Government Mail', 'Initial Intake', etc.
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);
```

### JSON / API Representation:
```json
{
  "id": 1,
  "document_id": 1,
  "progress_update_id": null,
  "file_name": "accreditation_compliance_directive.pdf",
  "file_path": "data/incoming/government_mail/accreditation_compliance_directive.pdf",
  "file_type": "PDF",
  "file_size": 2048,
  "category": "ORIGINAL",
  "source": "Ministry of Higher Education",
  "uploaded_by": 1,
  "uploaded_by_name": "Director Secretary",
  "created_at": "2026-08-16 09:30"
}
```

---

## 2. OCR Metadata & Routing Intelligence Schema

When an incoming dispatch is processed, OCR analysis extracts textual content and infers structured routing suggestions.

### Required Fields on `documents`:
| Field Name | Type | Description | Example |
|:---|:---|:---|:---|
| `ocr_text` | `TEXT` | Raw extracted text from document pages | `"CENTRAL HIGHER EDUCATION COUNCIL..."` |
| `has_prior_director_remark` | `BOOLEAN` | Whether handwritten/prior Director directive is found | `true` |
| `director_remark` | `TEXT` | Extracted directive text | `"Approved. Expedite procurement..."` |
| `has_director_routing_instruction` | `BOOLEAN` | Whether directive includes explicit staff routing | `true` |
| `director_routing_raw_text` | `TEXT` | Exact text fragment containing instruction | `"assign to Rahul Sharma for immediate execution"` |
| `routing_instruction_confidence` | `INTEGER` | Extraction confidence score (0-100) | `96` |
| `suggested_department_id` | `INTEGER` | Inferred target department ID | `1` (`Finance`) |
| `suggested_department_name` | `VARCHAR(100)` | Inferred target department name | `"Finance"` |
| `suggested_employee_id` | `INTEGER` | Inferred target employee ID | `101` (`Rahul Sharma`) |
| `suggested_employee_name` | `VARCHAR(100)` | Inferred target employee name | `"Rahul Sharma"` |

---

## 3. Physical / Manual Intake Workflow

```text
               [ Physical Letter / Scanned Document Uploaded ]
                                      |
                                      v
                       [ OCR Extraction & Inference ]
                                      |
                                      v
                       Populate Metadata on Intake Form
                                      |
                         Director Directive Detected?
                                    /           \
                                  YES            NO
                                  /               \
            [ Direct Route Bypass Available ]    [ Standard DS Routing Flow ]
            (DS can route directly to Staff)     (DS routes to Director)
```

---

## 4. Backend Implementation Note (OCR Engine vs. Data Storage)

> [!NOTE]
> The backend **is not currently required to run an active OCR neural network or Tesseract binary**.
> 
> The backend's responsibility is to **store, persist, and return the OCR and routing suggestion fields** in the `documents` table and API responses. The frontend client handles the heuristic suggestions and preview parsing.
