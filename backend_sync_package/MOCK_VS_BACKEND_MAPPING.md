# Mock vs. Backend Field-by-Field Mapping & Gap Analysis

This document identifies the field-by-field mapping between the working `MockRepository` / Frontend models and the current `backend/models.py` and `backend/schemas.py`.

---

## 1. Document Model Mapping (`documents` table)

| MockRepository / Frontend Field | Backend SQL Column (`models.Document`) | Backend Schema (`schemas.DocumentResponse`) | Classification | Resolution / Recommended Action |
|:---|:---|:---|:---:|:---|
| `id` | `doc_id` | `doc_id` | **API MISMATCH** | Frontend accepts both `id` and `doc_id`. Recommend exposing `id` in API responses or keeping `id: int = Field(alias="doc_id")`. |
| `reference_no` / `reference` | `reference_no` | `reference_no` | **MATCH** | Perfectly aligned. Unique string `CDTRS-2026-XXXX`. |
| `title` / `subject` | `title` | `title` | **MATCH** | Perfectly aligned. |
| `date` / `received` | `date` | `date` | **MATCH** | Stored as `Date` in SQL. |
| `mode` | `mode` | `mode` | **MATCH** | Channel string (`"Outlook / Government Mail"`, etc.). |
| `source` | `source` | `source` | **MATCH** | Sender / external agency name. |
| `priority` | `priority` | `priority` | **NEEDS BACKEND DECISION** | Backend defaults to `"Green"`. Frontend standardizes on `"High"`, `"Medium"`, `"Low"` (with color aliases). Recommend standardizing on `"High"`, `"Medium"`, `"Low"`. |
| `deadline` | `deadline` | `deadline` | **MATCH** | Stored as nullable `Date`. |
| `status` | `status` | `status` | **MATCH** | Aligned with `DocumentStatusEnum`. |
| `current_stage` | `current_stage` | `current_stage` | **MATCH** | Aligned with `WorkflowStageEnum` (`DS`, `DIRECTOR`, `HOD`, `EMPLOYEE`, `CLOSED`). |
| `director_remark` | `director_remark` | `director_remark` | **MATCH** | Stored as `Text`. |
| `hod_remark` | `hod_remark` | `hod_remark` | **MATCH** | Stored as `Text`. |
| `current_owner_id` | `current_owner_id` | `current_owner_id` | **MATCH** | Foreign key pointing to `users.id`. |
| `target_department_id` | `target_department_id` | `target_department_id` | **MATCH** | Foreign key pointing to `departments.d_id`. |
| `assigned_employee_id` | `assigned_employee_id` | `assigned_employee_id` | **MATCH** | Foreign key pointing to `employees.e_id` / `users.id`. |
| `file_path` | `file_path` | `file_path` | **MATCH** | Path or URL to primary document file. |
| `ocr_text` | *Missing* | *Missing* | **BACKEND MISSING** | Add `ocr_text = Column(Text, nullable=True)` to `models.Document`. |
| `has_prior_director_remark` | *Missing* | *Missing* | **BACKEND MISSING** | Add `has_prior_director_remark = Column(Boolean, default=False)` to `models.Document` to persist pre-reviewed status. |
| `has_director_routing_instruction` | *Missing* | *Missing* | **BACKEND MISSING** | Add `has_director_routing_instruction = Column(Boolean, default=False)`. |
| `director_routing_raw_text` | *Missing* | *Missing* | **BACKEND MISSING** | Add `director_routing_raw_text = Column(Text, nullable=True)`. |
| `routing_instruction_confidence` | *Missing* | *Missing* | **BACKEND MISSING** | Add `routing_instruction_confidence = Column(Integer, default=0)`. |
| `suggested_department_id` | `suggested_department_id` | `suggested_department_id` | **MATCH** | Foreign key to `departments.d_id`. |
| `suggested_employee_id` | *Missing* | *Missing* | **BACKEND MISSING** | Add `suggested_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)` to persist employee suggestion for Document 3 & 4. |

---

## 2. Department & Employee Model Mapping

| MockRepository / Frontend Field | Backend SQL Column | Classification | Resolution / Recommended Action |
|:---|:---|:---:|:---|
| `department.id` | `departments.d_id` | **API MISMATCH** | Frontend expects `id` in JSON responses. Backend schemas should expose `id` (or alias `d_id`). |
| `department.name` | `departments.d_name` | **API MISMATCH** | Frontend expects `name` in JSON responses. Backend schemas should expose `name` (or alias `d_name`). |
| `employee.id` | `employees.e_id` | **MATCH** | Aligned with user IDs (101, 201, etc.). |
| `employee.name` | `employees.name` | **MATCH** | Aligned. |
| `employee.designation` | `employees.designation` | **MATCH** | Aligned. |
| `employee.department_id` | `employees.d_id` | **API MISMATCH** | Schema should serialize `department_id`. |

---

## 3. User & Authentication Model Mapping

| MockRepository / Frontend Field | Backend SQL Column | Classification | Resolution / Recommended Action |
|:---|:---|:---:|:---|
| `user.id` | `users.id` | **MATCH** | Primary key. |
| `user.username` | `users.username` | **MATCH** | Unique string (`ds`, `director`, `hod_finance`, etc.). |
| `user.full_name` | `users.full_name` | **MATCH** | Full name string. |
| `user.role` | `users.role` | **MATCH** | String matching `RoleEnum` (`"Director Secretary"`, `"Director"`, `"HOD"`, `"Employee"`). |
| `user.department_id` | `users.department_id` | **MATCH** | Foreign key to department. |
| `user.password` | `users.password_hash` | **NEEDS BACKEND DECISION** | Backend uses bcrypt/hashing. Seed accounts must use hashed passwords corresponding to demo passwords (`1234`). |

---

## 4. Summary of Backend Additions Needed

To achieve 100% feature parity with `MockRepository`:
1. Add columns to `documents` table for OCR / Directive intelligence:
   - `ocr_text` (`Text`, nullable)
   - `has_prior_director_remark` (`Boolean`, default=False)
   - `has_director_routing_instruction` (`Boolean`, default=False)
   - `director_routing_raw_text` (`Text`, nullable)
   - `routing_instruction_confidence` (`Integer`, default=0)
   - `suggested_employee_id` (`Integer`, ForeignKey to `users.id`, nullable)
2. Ensure Pydantic response schemas serialize `id` and `name` alongside `doc_id`, `d_id`, and `d_name`.
3. Seed bcrypt hashes for the standard demonstration passwords (`1234`).
