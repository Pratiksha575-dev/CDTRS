"""Document intelligence: OCR extraction and advisory routing suggestions.

Both are ASSISTIVE only.  OCR fills in fields the DS can correct, and the
routing suggestion is a hint the DS may apply, edit or ignore.  Nothing in
this module routes a document or changes workflow state by itself.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

import models
from models import AttachmentType, OCRStatus, RoutingSource

# ---------------------------------------------------------------------------
# Make the OCR engine (OCR/ocr.py + OCR/rules.py) importable whether the
# backend runs from the project root or from backend/.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OCR_DIR = _PROJECT_ROOT / "OCR"
if str(_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(_OCR_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from OCR.ocr import DocumentOCR as _DocumentOCR
    _OCR_AVAILABLE = _DocumentOCR is not None
except Exception:
    _OCR_AVAILABLE = False
    _DocumentOCR = None

try:
    from OCR.rules import extract_fields as _extract_fields
except Exception:
    _extract_fields = None


def get_document(db: Session, doc_id: int) -> Optional[models.Document]:
    return db.query(models.Document).filter(models.Document.doc_id == doc_id).first()


def get_departments(db: Session) -> List[models.Department]:
    return db.query(models.Department).filter(models.Department.is_active.is_(True)).all()


def get_employees(db: Session) -> List[models.Employee]:
    return db.query(models.Employee).filter(models.Employee.is_active.is_(True)).all()


def get_document_ocr(db: Session, doc_id: int) -> Optional[models.DocumentOCR]:
    return db.query(models.DocumentOCR).filter(models.DocumentOCR.document_id == doc_id).first()


def get_routing_suggestion(db: Session, doc_id: int) -> Optional[models.RoutingSuggestion]:
    return db.query(models.RoutingSuggestion).filter(
        models.RoutingSuggestion.document_id == doc_id
    ).first()


def verify_extracted_field(
    db: Session, doc_id: int, field_name: str, verified_value: str, user: models.User
) -> Optional[models.DocumentExtractedField]:
    """The DS corrects an extracted value.  The original stays for provenance;
    `verified_value` is what the rest of the system trusts."""
    field = db.query(models.DocumentExtractedField).filter(
        models.DocumentExtractedField.document_id == doc_id,
        models.DocumentExtractedField.field_name == field_name,
    ).first()
    if not field:
        field = models.DocumentExtractedField(
            document_id=doc_id,
            field_name=field_name,
            extracted_value=None,
            confidence=None,
        )
        db.add(field)
    field.verified_value = verified_value
    field.verified_by = user.id
    field.verified_at = datetime.now()
    db.commit()
    db.refresh(field)
    return field


def generate_routing_suggestion(
    db: Session,
    doc_id: int,
    include_director_remark: bool = True,
    preferred_dept_id: Optional[int] = None,
    preferred_emp_id: Optional[int] = None
) -> Optional[models.RoutingSuggestion]:
    """
    Generates a routing suggestion using:
    1. Explicit Director remark analysis (employee name / department mention)
    2. Preferred intake routing intelligence provided during document intake verification
    3. Keyword scoring of real OCR extracted text against all live departments
    4. Fallback to document title + metadata keyword match
    Never uses hardcoded department names.
    """
    doc = get_document(db, doc_id)
    if not doc:
        return None

    depts = get_departments(db)
    suggested_dept_id: Optional[int] = preferred_dept_id or None
    suggested_emp_id: Optional[int] = preferred_emp_id

    ocr_record = db.query(models.DocumentOCR).filter(
        models.DocumentOCR.document_id == doc_id
    ).first()
    ocr_conf = ocr_record.confidence if (ocr_record and ocr_record.confidence and ocr_record.confidence > 0) else None

    confidence = ocr_conf if ocr_conf is not None else 0.0
    reason = "Routing intelligence confirmed during document intake verification." if (suggested_dept_id or suggested_emp_id) else "Insufficient content to determine department."
    source = RoutingSource.DOCUMENT_CONTENT if (suggested_dept_id or suggested_emp_id) else RoutingSource.SOURCE_METADATA
    is_director_instruction = False

    # ------------------------------------------------------------------
    # 1. Director Remark — explicit delegation detection
    # ------------------------------------------------------------------
    if include_director_remark and doc.latest_director_remark:
        remark_lower = doc.latest_director_remark.lower()

        # Employee name check (highest specificity)
        employees = get_employees(db)
        for emp in employees:
            if emp.full_name.lower() in remark_lower:
                suggested_emp_id = emp.user_id
                suggested_dept_id = emp.department_id
                confidence = 0.95
                dept_name = emp.department.name if emp.department else "unknown"
                reason = (
                    f"Director remark explicitly names {emp.full_name} "
                    f"({dept_name}) for assignment."
                )
                source = RoutingSource.DIRECTOR_REMARK
                is_director_instruction = True
                break

        # Department name / code check
        if not is_director_instruction:
            for dept in depts:
                if dept.name.lower() in remark_lower or (
                    dept.code and dept.code.lower() in remark_lower
                ):
                    suggested_dept_id = dept.id
                    confidence = 0.92
                    reason = (
                        f"Director remark explicitly references {dept.name} department."
                    )
                    source = RoutingSource.DIRECTOR_REMARK
                    is_director_instruction = True
                    break

    # ------------------------------------------------------------------
    # 2. Keyword scoring against real OCR extracted text (if not already set)
    # ------------------------------------------------------------------
    if not suggested_dept_id and not suggested_emp_id:
        ocr_record = db.query(models.DocumentOCR).filter(
            models.DocumentOCR.document_id == doc_id
        ).first()

        is_ocr_ok = (ocr_record and ocr_record.ocr_status == OCRStatus.COMPLETED and bool(ocr_record.extracted_text and ocr_record.extracted_text.strip()))

        if is_ocr_ok:
            text_to_score = ocr_record.extracted_text
            text_lower = text_to_score.lower()

            # Score each department using keyword counts
            dept_scores: Dict[int, float] = {}
            for dept in depts:
                score = 0.0
                # Department name / code direct hit (high weight)
                if dept.name.lower() in text_lower:
                    score += 5.0
                if dept.code and dept.code.lower() in text_lower:
                    score += 4.0

                # Word-level keyword scoring using rules loaded from the OCR module
                try:
                    from OCR.rules import DEPARTMENT_KEYWORDS, DEPARTMENT_SCORE_WEIGHTS
                    matched_key = None
                    for rules_key in DEPARTMENT_KEYWORDS:
                        if (
                            rules_key.lower() == dept.name.lower()
                            or rules_key.lower() in dept.name.lower()
                            or dept.name.lower() in rules_key.lower()
                        ):
                            matched_key = rules_key
                            break

                    if matched_key:
                        for kw in DEPARTMENT_KEYWORDS[matched_key]:
                            import re as _re
                            hits = len(_re.findall(_re.escape(kw), text_lower))
                            if hits:
                                weight = DEPARTMENT_SCORE_WEIGHTS.get(kw, 1.0)
                                score += hits * weight
                except ImportError:
                    pass

                if score > 0:
                    dept_scores[dept.id] = score

            if dept_scores:
                best_dept_id = max(dept_scores, key=dept_scores.__getitem__)
                best_score = dept_scores[best_dept_id]
                total_score = sum(dept_scores.values())

                confidence = ocr_record.confidence if (ocr_record and ocr_record.confidence > 0) else (0.95 if best_score >= 5 else 0.88)

                suggested_dept_id = best_dept_id
                dept_obj = next((d for d in depts if d.id == best_dept_id), None)
                source_label = "OCR text"
                reason = (
                    f"Keyword scoring of {source_label} matched "
                    f"{dept_obj.name if dept_obj else 'department'} "
                    f"(score {best_score:.1f} / {total_score:.1f})."
                )
                source = RoutingSource.DOCUMENT_CONTENT

                # Check if any employee is explicitly mentioned by name in the document text
                employees = get_employees(db)
                for emp in employees:
                    if emp.full_name and len(emp.full_name) > 3 and emp.full_name.lower() in text_lower:
                        suggested_emp_id = emp.user_id
                        reason += f" Staff '{emp.full_name}' explicitly mentioned in document text."
                        break

    # ------------------------------------------------------------------
    # 3. No match found: Honest None / 0.0 confidence (No fake default)
    # ------------------------------------------------------------------
    if not suggested_dept_id and not suggested_emp_id:
        suggested_dept_id = None
        confidence = 0.0
        reason = "OCR extraction did not yield a departmental keyword match. Manual review required."
        source = RoutingSource.SOURCE_METADATA

    # Upsert routing suggestion
    suggestion = db.query(models.RoutingSuggestion).filter(
        models.RoutingSuggestion.document_id == doc_id
    ).first()

    if not suggestion:
        suggestion = models.RoutingSuggestion(
            document_id=doc_id,
            suggested_department_id=suggested_dept_id,
            suggested_employee_id=suggested_emp_id,
            routing_confidence=confidence,
            routing_reason=reason,
            routing_source=source,
            is_director_instruction=is_director_instruction,
            generated_at=datetime.now(),
        )
        db.add(suggestion)
    elif not suggestion.confirmed_at:          # Preserve DS-confirmed suggestions
        suggestion.suggested_department_id = suggested_dept_id
        suggestion.suggested_employee_id = suggested_emp_id
        suggestion.routing_confidence = confidence
        suggestion.routing_reason = reason
        suggestion.routing_source = source
        suggestion.is_director_instruction = is_director_instruction
        suggestion.generated_at = datetime.now()

    db.commit()
    db.refresh(suggestion)

    # PZ_26/08 - Terminal Debug: Output Routing Suggestion
    suggested_dept_name = "None"
    if suggestion.suggested_department_id:
        d_obj = db.query(models.Department).filter(models.Department.id == suggestion.suggested_department_id).first()
        suggested_dept_name = d_obj.name if d_obj else str(suggestion.suggested_department_id)

    print(f"[ROUTING AI] Suggestion for Doc #{doc_id}:", flush=True)
    print(f" * Suggested Dept : {suggested_dept_name}", flush=True)
    print(f" * Confidence     : {suggestion.routing_confidence * 100:.1f}%", flush=True)
    print(f" * Rule Reason    : {suggestion.routing_reason}\n", flush=True)

    return suggestion


def trigger_ocr_processing(
    db: Session,
    doc_id: int,
    intake_ocr_text: Optional[str] = None,
    intake_ocr_confidence: Optional[float] = None,
    preferred_dept_id: Optional[int] = None,
    preferred_emp_id: Optional[int] = None
) -> Optional[models.DocumentOCR]:
    """
    Runs real PaddleOCR on the first original attachment found for this document.
    Falls back to metadata-based text if no file is on disk or PaddleOCR unavailable.
    Stores extracted_text, confidence, structured fields, and triggers routing suggestion.
    """
    doc = get_document(db, doc_id)
    if not doc:
        return None

    # PZ_26/08 - Terminal Debug: Starting OCR Pipeline
    mode_str = doc.mode.value if hasattr(doc.mode, "value") else str(doc.mode)
    prio_str = doc.priority.value if hasattr(doc.priority, "value") else str(doc.priority)

    print("\n" + "=" * 70, flush=True)
    print(f" [OCR PIPELINE] Starting Text Extraction for Doc #{doc.doc_id} ({doc.reference_no})", flush=True)
    print(f" * Document Title : {doc.title}", flush=True)
    print(f" * Mode / Source  : {mode_str} | {doc.source or 'Internal'}", flush=True)

    # Upsert OCR record
    ocr_record = db.query(models.DocumentOCR).filter(
        models.DocumentOCR.document_id == doc_id
    ).first()
    existing_conf = ocr_record.confidence if (ocr_record and ocr_record.confidence and ocr_record.confidence > 0) else None
    existing_text = ocr_record.extracted_text if (ocr_record and ocr_record.extracted_text) else None

    if not ocr_record:
        ocr_record = models.DocumentOCR(
            document_id=doc_id,
            ocr_status=OCRStatus.PROCESSING,
            ocr_engine="PaddleOCR-v3"
        )
        db.add(ocr_record)
    else:
        ocr_record.ocr_status = OCRStatus.PROCESSING
        ocr_record.error_message = None

    doc.ocr_status = OCRStatus.PROCESSING
    db.commit()

    extracted_text = (intake_ocr_text.strip() if (intake_ocr_text and intake_ocr_text.strip()) else (existing_text or ""))
    confidence = float(intake_ocr_confidence) if (intake_ocr_confidence is not None and float(intake_ocr_confidence) > 0) else (existing_conf or 0.0)
    is_handwritten = False
    ocr_fields: dict = {}
    ocr_error: Optional[str] = None

    # ---- Attempt real PaddleOCR on stored file -------------------------
    file_processed = bool(extracted_text and len(extracted_text.strip()) > 5)
    attachment = db.query(models.Attachment).filter(
        models.Attachment.document_id == doc_id,
        models.Attachment.attachment_type == AttachmentType.ORIGINAL
    ).order_by(models.Attachment.id).first()

    if attachment:
        # Build absolute file path from storage_key (robust check across backend/uploads and root/uploads)
        upload_candidates = [
            Path(os.getenv("UPLOAD_DIR", "./uploads")).resolve(),
            (Path(__file__).parent / "uploads").resolve(),
            (Path(__file__).parent.parent / "uploads").resolve(),
        ]
        full_path = None
        for base in upload_candidates:
            cand = base / attachment.storage_key
            if cand.exists():
                full_path = cand
                break
        if not full_path:
            cand = Path(attachment.storage_key)
            if cand.exists():
                full_path = cand

        if full_path and full_path.exists():
            print(f" * File Location  : {full_path}", flush=True)
            ext = full_path.suffix.lower()

            if _OCR_AVAILABLE and _DocumentOCR is not None:
                try:
                    print(f" * Engine Running : PaddleOCR Inference Engine ({full_path.name})", flush=True)
                    engine = _DocumentOCR()
                    ocr_res = engine.process(str(full_path))
                    paddle_text = ocr_res.get("raw_text", "")
                    raw_conf = ocr_res.get("confidence", 0.0)
                    if paddle_text and len(paddle_text.strip()) > 5:
                        extracted_text = paddle_text
                        if raw_conf is not None and float(raw_conf) > 0:
                            confidence = float(raw_conf)
                        is_handwritten = bool(ocr_res.get("is_handwritten", False))
                        ocr_fields = ocr_res.get("fields", {})
                        file_processed = True
                        hw_note = " [handwritten]" if is_handwritten else ""
                        engine_name = f"PaddleOCR-v3{hw_note}"
                        ocr_error = None
                        print(f" * PaddleOCR Success: {len(extracted_text)} chars, confidence={confidence:.4f}", flush=True)
                except Exception as ocr_ex:
                    ocr_error = f"PaddleOCR processing notice: {ocr_ex}"
                    print(f" * [WARN] PaddleOCR notice: {ocr_error}", flush=True)

            # If PaddleOCR unavailable or returned empty text, fall back to pure text extraction (e.g. pypdf)
            if not file_processed or not extracted_text:
                try:
                    if ext in (".txt", ".md", ".csv", ".json", ".log"):
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as tf:
                            txt_content = tf.read().strip()
                            if txt_content:
                                extracted_text = txt_content
                                file_processed = True
                                engine_name = "TextExtractor"
                                if confidence == 0.0:
                                    confidence = existing_conf or 1.0
                    elif ext == ".pdf":
                        try:
                            import pypdf
                            reader = pypdf.PdfReader(str(full_path))
                            pypdf_text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
                            if pypdf_text and len(pypdf_text) > 10:
                                if not extracted_text:
                                    extracted_text = pypdf_text
                                file_processed = True
                                engine_name = "Digital-PDF"
                                if confidence == 0.0:
                                    confidence = existing_conf or (float(intake_ocr_confidence) if intake_ocr_confidence else 0.98)
                        except Exception as pex:
                            print(f" * [WARN] pypdf error: {pex}", flush=True)
                    
                    if file_processed and _extract_fields and extracted_text:
                        ocr_fields = _extract_fields(extracted_text)
                    if file_processed and confidence == 0.0:
                        confidence = existing_conf or 0.98
                        ocr_error = None
                except Exception as e:
                    ocr_error = f"Digital extraction notice: {str(e)[:300]}"

            # If backend local file processing couldn't run but client intake stream provided valid OCR text, use it
            if not file_processed and intake_ocr_text and len(intake_ocr_text.strip()) > 5:
                print(" * Engine Running : Intake OCR Stream (Client-side PaddleOCR extraction)", flush=True)
                extracted_text = intake_ocr_text.strip()
                file_processed = True
                engine_name = "PaddleOCR-Client"
                if _extract_fields:
                    ocr_fields = _extract_fields(extracted_text)
                if confidence == 0.0:
                    confidence = float(intake_ocr_confidence) if intake_ocr_confidence else (existing_conf or 0.98)
                ocr_error = None

            # Only flag OCR missing if no processing route succeeded at all
            if not file_processed and not extracted_text.strip():
                ocr_error = ocr_error or "OCR processing failed: could not extract text from document."
        else:
            ocr_error = f"Attachment file not found on disk: {full_path}"
            print(f" * [WARN] {ocr_error}", flush=True)
    else:
        # Fallback to intake text if no attachment
        if (intake_ocr_text and len(intake_ocr_text.strip()) > 5) or (existing_text and len(existing_text.strip()) > 5):
            extracted_text = (intake_ocr_text or existing_text).strip()
            file_processed = True
            engine_name = "PaddleOCR-Client"
            if _extract_fields:
                ocr_fields = _extract_fields(extracted_text)
            if confidence == 0.0:
                confidence = float(intake_ocr_confidence) if intake_ocr_confidence else (existing_conf or 0.98)
            ocr_error = None
        else:
            ocr_error = "No attachments available for processing."

    # ---- Record OCR outcome ----
    # A document without an attachment is valid (for example, a direct-text
    # manual record or a dispatched text-only message).  Do not label that as
    # an OCR failure: there was simply no binary document to process.
    no_attachment_to_process = (
        not file_processed
        and not extracted_text.strip()
        and not attachment
    )

    if no_attachment_to_process:
        extracted_text = ""
        confidence = 0.0
        engine_name = "PaddleOCR-v3"
        ocr_status = OCRStatus.NONE
        ocr_error = "No attachment available for OCR processing."
    elif not file_processed or not extracted_text.strip():
        extracted_text = ""
        confidence = 0.0
        ocr_error = ocr_error or "OCR processing failed: could not extract text from document."
        engine_name = "PaddleOCR-v3"
        ocr_status = OCRStatus.FAILED
    else:
        ocr_status = OCRStatus.COMPLETED
        ocr_error = None
        if confidence == 0.0:
            confidence = existing_conf or (float(intake_ocr_confidence) if intake_ocr_confidence else 0.98)
        engine_name = getattr(ocr_record, "ocr_engine", None) or "PaddleOCR-v3"

    ocr_record.extracted_text = extracted_text
    ocr_record.confidence = confidence
    ocr_record.ocr_status = ocr_status
    ocr_record.processed_at = datetime.now()
    ocr_record.ocr_engine = engine_name
    ocr_record.error_message = ocr_error
    doc.ocr_status = ocr_status

    # ---- Persist structured fields (only if OCR succeeded) ----
    ocr_extracted_fields = []
    if file_processed:
        always_fields = [
            {"name": "TITLE",        "value": doc.title,            "conf": confidence, "page": 1},
            {"name": "REFERENCE_NO", "value": doc.reference_no,     "conf": confidence, "page": 1},
            {"name": "SOURCE",       "value": doc.source or "",     "conf": confidence, "page": 1},
            {"name": "PRIORITY",     "value": prio_str,             "conf": confidence, "page": 1},
        ]
        # Add OCR-extracted fields (from real PaddleOCR run)
        ocr_extracted_fields = [
            {"name": k.upper(), "value": (v if isinstance(v, str) else ", ".join(v)),
             "conf": confidence, "page": 1}
            for k, v in ocr_fields.items() if v
        ]

        for f_item in always_fields + ocr_extracted_fields:
            existing_f = db.query(models.DocumentExtractedField).filter(
                models.DocumentExtractedField.document_id == doc_id,
                models.DocumentExtractedField.field_name == f_item["name"]
            ).first()
            if not existing_f:
                db.add(models.DocumentExtractedField(
                    document_id=doc_id,
                    field_name=f_item["name"],
                    extracted_value=f_item["value"],
                    confidence=f_item["conf"],
                    source_page=f_item["page"],
                    source_text=f_item["value"][:500] if f_item["value"] else None
                ))
            elif not existing_f.verified_value:
                # Only update unverified fields
                existing_f.extracted_value = f_item["value"]
                existing_f.confidence = f_item["conf"]

    db.commit()
    db.refresh(ocr_record)

    # PZ_26/08 - Terminal Debug: Output OCR Results Summary
    print("-" * 70, flush=True)
    status_str = ocr_record.ocr_status.value if hasattr(ocr_record.ocr_status, "value") else str(ocr_record.ocr_status)
    print(f" [OCR OUTPUT] Doc #{doc.doc_id} ({doc.reference_no}) Result:", flush=True)
    print(f" * Status         : {status_str}", flush=True)
    print(f" * Engine Used    : {engine_name}", flush=True)
    print(f" * Confidence     : {confidence * 100:.1f}% ({confidence:.4f})", flush=True)
    print(f" * Extracted Size : {len(extracted_text)} characters", flush=True)
    if extracted_text.strip():
        preview_lines = extracted_text.strip().split("\n")[:4]
        preview_block = "\n   ".join(preview_lines)
        print(f" * Text Preview   :\n   {preview_block}", flush=True)
    if ocr_extracted_fields:
        print(" * Extracted Structured Fields:", flush=True)
        for f in ocr_extracted_fields:
            print(f"   - {f['name']:<15}: {f['value']}", flush=True)
    if ocr_error:
        print(f" * Notice/Warning : {ocr_error}", flush=True)
    print("=" * 70, flush=True)

    # Automatically generate routing suggestion from the fresh OCR text or confirmed intake parameters
    generate_routing_suggestion(
        db,
        doc_id,
        include_director_remark=True,
        preferred_dept_id=preferred_dept_id,
        preferred_emp_id=preferred_emp_id
    )

    return ocr_record


def reanalyze_document_ocr(db: Session, doc_id: int) -> Optional[models.DocumentOCR]:
    """Re-run extraction on demand from the DS screen."""
    return trigger_ocr_processing(db, doc_id)
