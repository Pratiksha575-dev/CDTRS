import os
import sys
import hashlib
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Ensure the OCR engine (OCR/ocr.py + OCR/rules.py) is importable from the
# backend. Works whether the backend is run from the project root or from
# backend/ sub-directory.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OCR_DIR = _PROJECT_ROOT / "OCR"
if str(_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(_OCR_DIR))

try:
    from OCR.ocr import DocumentOCR as _DocumentOCR
    _OCR_AVAILABLE = (_DocumentOCR is not None)
except Exception:
    _OCR_AVAILABLE = False
    _DocumentOCR = None

# PZ_26/08: Import standalone extract_fields helper from rules
try:
    from OCR.rules import extract_fields as _extract_fields
except ImportError:
    try:
        from OCR.rules import extract_fields as _extract_fields
    except ImportError:
        _extract_fields = None

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

import bcrypt
from jose import jwt

import models
import schemas
from models import (
    UserRole, DocumentStatus, WorkflowStage, Priority, RouteType,
    SourceType, MessageProcessingStatus, AttachmentType, OCRStatus,
    RoutingSource, RemarkType, ReminderReason,
    ProgressValidationStatus,
    WorkContextType, DirectorDecision, BranchType
)


# =========================================================
# CONTEXT RESOLUTION
# =========================================================

def _resolve_context_membership(
    db: Session,
    user: models.User,
    context_id: Optional[int] = None,
) -> Optional[models.WorkContextMembership]:
    """Resolve the work context used by workflow/document operations.

    Every document query must use the same context-resolution rule as the
    FastAPI dependency.  A supplied context_id must belong to the user and be
    active.  When no context is supplied, prefer an active context matching
    the user's role; otherwise use the first active context.

    This helper is deliberately kept in CRUD so service functions cannot
    accidentally bypass context authorization.
    """
    if user is None:
        return None

    if context_id is not None:
        return validate_user_context(db, user.id, context_id)

    memberships = get_user_context_memberships(db, user.id)
    if not memberships:
        return None

    # Prefer the context that corresponds to the persisted user role.
    for membership in memberships:
        context_value = getattr(membership.context_type, "value", membership.context_type)
        role_value = getattr(user.role, "value", user.role)
        if context_value == role_value:
            return membership

    return memberships[0]


# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================

SECRET_KEY = os.getenv("SECRET_KEY", "cdtrs-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "500"))


# =========================================================
# LIVE EVENT MANAGER (WebSocket & Event Broadcast)
# =========================================================

class LiveEventManager:
    def __init__(self):
        self._active_connections: List[Any] = []
        self._recent_events: List[Dict[str, Any]] = []
        self._max_recent = 100

    async def connect(self, websocket: Any):
        await websocket.accept()
        self._active_connections.append(websocket)

    def disconnect(self, websocket: Any):
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    async def broadcast(self, event_type: str, document_id: Optional[int] = None,
                        user_id: Optional[int] = None, payload: Optional[dict] = None):
        event = {
            "event_type": event_type,
            "document_id": document_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "payload": payload or {}
        }
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events.pop(0)

        # Broadcast to all live WebSocket connections safely
        for connection in list(self._active_connections):
            try:
                await connection.send_json(event)
            except Exception:
                self.disconnect(connection)

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._recent_events[-limit:]


# Global singleton event manager
event_manager = LiveEventManager()


# =========================================================
# PASSWORD & JWT HELPERS
# =========================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


# =========================================================
# USER OPERATIONS
# =========================================================

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        username=user.username,
        password_hash=hash_password(user.password),
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        employee_id=user.employee_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    if not username:
        return None
    u = username.strip().lower()
    alias_map = {
        "ds": "ds_user",
        "master": "ds_user",
        "hod": "hod_finance",
        "employee": "emp_rahul",
        "rahul": "emp_rahul",
        "priya": "emp_priya",
    }
    resolved = alias_map.get(u, u)
    return (
        db.query(models.User)
        .filter((models.User.username == resolved) | (models.User.username == username) | (models.User.username == u))
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).order_by(models.User.full_name).all()


def get_users_by_role(db: Session, role: UserRole) -> List[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.role == role, models.User.is_active == True)
        .order_by(models.User.full_name)
        .all()
    )


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user


def update_user_password(db: Session, user_id: int, new_password: str) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    return True


# =========================================================
# DEPARTMENT OPERATIONS
# =========================================================

def create_department(db: Session, dept: schemas.DepartmentCreate) -> models.Department:
    db_dept = models.Department(name=dept.name, code=dept.code)
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept


def get_departments(db: Session) -> List[models.Department]:
    return db.query(models.Department).filter(models.Department.is_active == True).order_by(models.Department.name).all()


def get_department_by_id(db: Session, dept_id: int) -> Optional[models.Department]:
    return db.query(models.Department).filter(models.Department.id == dept_id).first()


# =========================================================
# EMPLOYEE OPERATIONS
# =========================================================

def create_employee(db: Session, emp: schemas.EmployeeCreate) -> models.Employee:
    db_emp = models.Employee(
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        department_id=emp.department_id,
        designation=emp.designation,
        user_id=emp.user_id,
    )
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp


def get_employees(db: Session) -> List[models.Employee]:
    return db.query(models.Employee).filter(models.Employee.is_active == True).order_by(models.Employee.full_name).all()


def get_employees_by_department(db: Session, department_id: int) -> List[models.Employee]:
    return (
        db.query(models.Employee)
        .filter(models.Employee.department_id == department_id, models.Employee.is_active == True)
        .order_by(models.Employee.full_name)
        .all()
    )


# =========================================================
# INTAKE & INCOMING MESSAGES
# =========================================================

def create_incoming_message(db: Session, intake: schemas.IntakeCreate, has_attachments: bool = False) -> models.IncomingMessage:
    # De-duplication check using external_message_id
    if intake.external_message_id:
        existing = db.query(models.IncomingMessage).filter(
            models.IncomingMessage.external_message_id == intake.external_message_id
        ).first()
        if existing:
            return existing

    msg = models.IncomingMessage(
        source_type=intake.source_type,
        external_message_id=intake.external_message_id,
        sender_name=intake.sender_name,
        sender_email=intake.sender_email,
        subject=intake.subject,
        received_at=intake.received_at or datetime.now(),
        body_reference=intake.body_reference,
        has_attachments=has_attachments,
        processing_status=MessageProcessingStatus.NEW
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_incoming_messages(db: Session) -> List[models.IncomingMessage]:
    """Return only external intake items still awaiting DS processing.

    Manual uploads never enter this queue. Once an external message has been
    converted into its canonical Document, its intake record is PROCESSED and
    disappears from the DS Inbox while the Document remains available under
    Documents/History.
    """
    return (
        db.query(models.IncomingMessage)
        .filter(
            models.IncomingMessage.processing_status
            != MessageProcessingStatus.PROCESSED
        )
        .order_by(models.IncomingMessage.created_at.desc())
        .all()
    )


def get_incoming_message_by_id(db: Session, msg_id: int) -> Optional[models.IncomingMessage]:
    return db.query(models.IncomingMessage).filter(models.IncomingMessage.id == msg_id).first()


def get_incoming_message_by_external_id(db: Session, external_id: str) -> Optional[models.IncomingMessage]:
    return db.query(models.IncomingMessage).filter(models.IncomingMessage.external_message_id == external_id).first()


def process_intake_to_document(db: Session, msg_id: int, proc_req: schemas.IntakeProcessRequest, user: models.User) -> Optional[models.Document]:
    msg = get_incoming_message_by_id(db, msg_id)
    if not msg:
        return None

    # Title fallback from message subject
    title = proc_req.title or msg.subject or f"Incoming Message #{msg.id}"
    doc_create = schemas.DocumentCreate(
        title=title,
        description=msg.body_reference,
        received_date=msg.received_at.date() if msg.received_at else date.today(),
        deadline=proc_req.deadline,
        source=msg.sender_name or msg.sender_email or "External Intake",
        mode=msg.source_type.value,
        priority=proc_req.priority,
        source_message_id=msg.id,
        suggested_department_id=proc_req.suggested_department_id,
        suggested_employee_id=proc_req.suggested_employee_id,
        ocr_text=proc_req.ocr_text,
        confidence=proc_req.confidence
    )

    doc = create_document(db, doc_create, created_by=user.id)
    msg.processing_status = MessageProcessingStatus.PROCESSED

    # Re-link pre-intake attachments to the newly generated document
    existing_attachments = db.query(models.Attachment).filter(
        models.Attachment.source_message_id == msg.id,
        models.Attachment.document_id == None
    ).all()
    for att in existing_attachments:
        att.document_id = doc.doc_id

    db.commit()
    db.refresh(doc)

    # Automatically trigger OCR processing on canonical document
    trigger_ocr_processing(
        db,
        doc.doc_id,
        intake_ocr_text=proc_req.ocr_text,
        intake_ocr_confidence=proc_req.confidence,
        preferred_dept_id=proc_req.suggested_department_id,
        preferred_emp_id=proc_req.suggested_employee_id
    )

    return doc


# =========================================================
# REFERENCE NUMBER GENERATOR
# =========================================================

def _generate_reference_no(db: Session) -> str:
    year = datetime.now().year
    prefix = f"CDTRS-{year}-"
    existing_refs = (
        db.query(models.Document.reference_no)
        .filter(models.Document.reference_no.like(f"{prefix}%"))
        .all()
    )
    max_num = 0
    for (ref,) in existing_refs:
        if ref and ref.startswith(prefix):
            suffix = ref[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    sequence = str(max_num + 1).zfill(4)
    return f"{prefix}{sequence}"


# =========================================================
# OPTIMISTIC CONCURRENCY HELPER
# =========================================================

def check_concurrency(doc: models.Document, expected_version: Optional[int]) -> bool:
    if expected_version is not None and doc.version != expected_version:
        return False
    return True


def _refresh_document_overall_state(db: Session, doc: models.Document) -> None:
    """Keep document status derived from independent branches without hiding history."""
    branches = db.query(models.DocumentDepartmentRouting).filter(
        models.DocumentDepartmentRouting.document_id == doc.doc_id
    ).all()
    if not branches:
        return
    active = [b for b in branches if b.is_active]
    if not active:
        if all(b.status in (DocumentStatus.COMPLETED, DocumentStatus.CLOSED) for b in branches):
            doc.status = DocumentStatus.COMPLETED
        return
    statuses = {b.status for b in active}
    if DocumentStatus.PROGRESS_UPDATED in statuses:
        doc.status = DocumentStatus.PROGRESS_UPDATED
    elif DocumentStatus.IN_PROGRESS in statuses:
        doc.status = DocumentStatus.IN_PROGRESS
    elif DocumentStatus.ASSIGNED_FOR_EXECUTION in statuses:
        doc.status = DocumentStatus.ASSIGNED_FOR_EXECUTION
    elif DocumentStatus.UNDER_HOD_PROCESSING in statuses:
        doc.status = DocumentStatus.UNDER_HOD_PROCESSING
    doc.updated_at = datetime.now()


# =========================================================
# DOCUMENT CRUD
# =========================================================

def create_document(db: Session, doc: schemas.DocumentCreate, created_by: int) -> models.Document:
    reference_no = _generate_reference_no(db)

    db_doc = models.Document(
        reference_no=reference_no,
        title=doc.title,
        description=doc.description,
        received_date=doc.received_date,
        deadline=doc.deadline,
        source=doc.source,
        mode=doc.mode,
        priority=doc.priority,
        status=DocumentStatus.RECEIVED,
        created_by=created_by,
        source_message_id=doc.source_message_id,
        director_remark=doc.director_remark,
        ocr_status=OCRStatus.NONE,
        version=1
    )

    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # If suggested routing was supplied at creation, initialize advisory routing suggestion
    if doc.suggested_department_id or doc.suggested_employee_id:
        generate_routing_suggestion(
            db,
            db_doc.doc_id,
            include_director_remark=bool(doc.director_remark),
            preferred_dept_id=doc.suggested_department_id,
            preferred_emp_id=doc.suggested_employee_id
        )

    # Workflow history entry
    _add_workflow_history(
        db=db,
        document_id=db_doc.doc_id,
        user_id=created_by,
        action="DOCUMENT_RECEIVED",
        from_role="DS",
        to_role=None,
        details=f"Document registered as {reference_no}"
    )

    return db_doc


def get_document(db: Session, doc_id: int) -> Optional[models.Document]:
    return db.query(models.Document).filter(models.Document.doc_id == doc_id).first()


def _document_has_historical_participation(db: Session, doc_id: int, user: models.User, context: Optional[models.WorkContextMembership]) -> bool:
    """Backend-enforced historical visibility. Active queues are separate from history."""
    uid = user.id
    # The DS who registered the canonical document is a legitimate participant
    # for the entire lifecycle, including the Director-returned state.
    if db.query(models.Document).filter(
        models.Document.doc_id == doc_id,
        models.Document.created_by == uid,
    ).first():
        return True

    # Direct participation in the workflow ledger.
    if db.query(models.DocumentRoute).filter(
        models.DocumentRoute.document_id == doc_id,
        or_(models.DocumentRoute.from_user_id == uid, models.DocumentRoute.to_user_id == uid)
    ).first():
        return True
    if db.query(models.DirectorReview).filter(models.DirectorReview.document_id == doc_id, models.DirectorReview.director_user_id == uid).first():
        return True
    if db.query(models.DocumentRemark).filter(models.DocumentRemark.document_id == doc_id, models.DocumentRemark.author_user_id == uid).first():
        return True
    if db.query(models.DocumentDepartmentRouting).filter(models.DocumentDepartmentRouting.document_id == doc_id, models.DocumentDepartmentRouting.routed_by_user_id == uid).first():
        return True
    if db.query(models.WorkAssignment).filter(models.WorkAssignment.document_id == doc_id, models.WorkAssignment.assigned_by_user_id == uid).first():
        return True
    if db.query(models.WorkAssignmentMember).filter(models.WorkAssignmentMember.user_id == uid, models.WorkAssignmentMember.assignment.has(document_id=doc_id)).first():
        return True
    if db.query(models.ProgressUpdate).filter(models.ProgressUpdate.document_id == doc_id, models.ProgressUpdate.submitted_by_user_id == uid).first():
        return True

    if context is None:
        return False
    if context.context_type == WorkContextType.HOD and context.department_id is not None:
        return db.query(models.DocumentDepartmentRouting).filter(
            models.DocumentDepartmentRouting.document_id == doc_id,
            models.DocumentDepartmentRouting.department_id == context.department_id,
        ).first() is not None
    # Employee/TSO history is intentionally user-specific, never department-wide.
    return False


def get_documents(db: Session, user: Optional[models.User] = None, context_id: Optional[int] = None) -> List[models.Document]:
    if user is None:
        return db.query(models.Document).order_by(models.Document.created_at.desc()).all()
    context = _resolve_context_membership(db, user, context_id)
    docs = db.query(models.Document).order_by(models.Document.updated_at.desc()).all()
    if context and context.context_type == WorkContextType.ADMIN:
        return []  # Admin is not a workflow participant merely by having admin role.
    return [d for d in docs if _document_has_historical_participation(db, d.doc_id, user, context)]


def get_inbox(db: Session, user: models.User, context_id: Optional[int] = None) -> List[models.Document]:
    """Active action queue only. Completed work is intentionally removed from inbox."""
    context = _resolve_context_membership(db, user, context_id)
    if context is None:
        return []
    ct = context.context_type
    if ct == WorkContextType.ADMIN:
        return []
    if ct == WorkContextType.DS:
        return db.query(models.Document).filter(models.Document.status.in_([
            DocumentStatus.RECEIVED, DocumentStatus.DIRECTOR_REVIEW_COMPLETED,
            DocumentStatus.PROGRESS_UPDATED, DocumentStatus.COMPLETED,
            DocumentStatus.REVIEW_COMPLETED, DocumentStatus.DIRECTOR_REVIEW_COMPLETED,
        ])).order_by(models.Document.updated_at.desc()).all()
    if ct == WorkContextType.DIRECTOR:
        return db.query(models.Document).join(models.DocumentRoute, models.DocumentRoute.document_id == models.Document.doc_id).filter(
            models.Document.status == DocumentStatus.UNDER_DIRECTOR_REVIEW,
            models.DocumentRoute.to_user_id == user.id,
        ).distinct().order_by(models.Document.updated_at.desc()).all()
    if ct == WorkContextType.HOD and context.department_id is not None:
        return db.query(models.Document).join(models.DocumentDepartmentRouting, models.DocumentDepartmentRouting.document_id == models.Document.doc_id).filter(
            models.DocumentDepartmentRouting.department_id == context.department_id,
            models.DocumentDepartmentRouting.branch_type == BranchType.DEPARTMENT_HOD,
            models.DocumentDepartmentRouting.is_active == True,
            models.DocumentDepartmentRouting.status.in_([DocumentStatus.UNDER_HOD_PROCESSING, DocumentStatus.PROGRESS_UPDATED]),
        ).distinct().order_by(models.Document.updated_at.desc()).all()
    if ct in (WorkContextType.EMPLOYEE, WorkContextType.TSO):
        return db.query(models.Document).join(models.WorkAssignment, models.WorkAssignment.document_id == models.Document.doc_id).join(
            models.WorkAssignmentMember, models.WorkAssignmentMember.work_assignment_id == models.WorkAssignment.id, isouter=True
        ).filter(
            models.WorkAssignment.is_active == True,
            or_(
                and_(models.WorkAssignment.assigned_to_user_id == user.id, models.WorkAssignment.assigned_to_context_membership_id == context.id),
                and_(models.WorkAssignmentMember.user_id == user.id, models.WorkAssignmentMember.context_membership_id == context.id, models.WorkAssignmentMember.is_active == True),
            )
        ).distinct().order_by(models.Document.updated_at.desc()).all()
    return []


def is_document_accessible(db: Session, doc: models.Document, user: models.User, context_id: Optional[int] = None) -> bool:
    context = _resolve_context_membership(db, user, context_id)
    return bool(context and context.context_type != WorkContextType.ADMIN and _document_has_historical_participation(db, doc.doc_id, user, context))


def get_accessible_documents_for_user(db: Session, user: models.User, context_id: Optional[int] = None) -> List[models.Document]:
    return get_documents(db, user, context_id)


def route_document(
    db: Session,
    doc_id: int,
    route_req: schemas.RouteRequest,
    current_user: models.User
) -> Optional[models.Document]:
    """
    Route a document. Director review remains a single document-level phase;
    post-review HOD/employee routing is converted to canonical independent branches.
    """
    doc = get_document(db, doc_id)
    if current_user.role != UserRole.DS:
        raise ValueError("Only DS can perform document routing.")
    if not doc or not check_concurrency(doc, route_req.expected_version):
        return None

    if route_req.route_type == RouteType.INITIAL_DIRECTOR_REVIEW:
        doc.status = DocumentStatus.UNDER_DIRECTOR_REVIEW
        doc.updated_at = datetime.now()
        doc.version += 1

        db.add(models.DocumentRoute(
            document_id=doc_id, from_user_id=current_user.id,
            to_user_id=route_req.to_user_id, to_department_id=route_req.to_department_id,
            route_type=route_req.route_type, remarks=route_req.remarks, created_at=datetime.now()
        ))
        db.commit()
        db.refresh(doc)
        return doc

    if route_req.route_type == RouteType.POST_REVIEW_TO_HOD:
        if not route_req.to_department_id:
            return None
        create_canonical_branches(
            db=db, document_id=doc_id,
            branches=[schemas.BranchCreate(
                branch_type=BranchType.DEPARTMENT_HOD,
                department_id=route_req.to_department_id,
                target_user_id=None,
                requires_hod_validation=False,
                instructions=route_req.remarks,
            )],
            current_user=current_user, expected_version=route_req.expected_version,
        )
        return get_document(db, doc_id)

    if route_req.route_type == RouteType.POST_REVIEW_TO_EMPLOYEE:
        if not route_req.to_user_id:
            return None
        create_canonical_branches(
            db=db, document_id=doc_id,
            branches=[schemas.BranchCreate(
                branch_type=BranchType.DIRECT_EMPLOYEE,
                target_user_id=route_req.to_user_id,
                requires_hod_validation=bool(route_req.requires_hod_validation),
                instructions=route_req.remarks,
            )],
            current_user=current_user, expected_version=route_req.expected_version,
        )
        return get_document(db, doc_id)

    if route_req.route_type == RouteType.FOLLOW_UP_TO_DIRECTOR:
        if not route_req.to_user_id:
            return None
        doc.status = DocumentStatus.UNDER_DIRECTOR_REVIEW
        doc.updated_at = datetime.now()
        doc.version += 1
        db.add(models.DocumentRoute(
            document_id=doc_id, from_user_id=current_user.id,
            to_user_id=route_req.to_user_id, route_type=route_req.route_type,
            remarks=route_req.remarks, created_at=datetime.now()
        ))
        db.commit()
        db.refresh(doc)
        return doc

    return None

def save_director_remark(db: Session, doc_id: int, remark: str, current_user: models.User,
                         expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.director_remark = remark
    doc.updated_at = datetime.now()
    doc.version += 1

    # Add to DocumentRemark history table
    remark_entry = models.DocumentRemark(
        document_id=doc_id,
        author_user_id=current_user.id,
        role=UserRole.DIRECTOR,
        remark_text=remark,
        remark_type=RemarkType.DIRECTOR
    )
    db.add(remark_entry)
    db.commit()
    db.refresh(doc)

    _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="DIRECTOR_REMARK_SAVED",
        from_role="DIRECTOR",
        to_role=None,
        details=f'Director Remark: "{remark}"'
    )

    # Automatically generate/update routing intelligence suggestions based on Director remark
    generate_routing_suggestion(db, doc_id, include_director_remark=True)

    return doc


def return_to_ds(db: Session, doc_id: int, ds_user_id: int, remarks: Optional[str],
                 current_user: models.User, expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.status = DocumentStatus.DIRECTOR_REVIEW_COMPLETED
    if remarks:
        doc.director_remark = remarks
        remark_entry = models.DocumentRemark(
            document_id=doc_id,
            author_user_id=current_user.id,
            role=UserRole.DIRECTOR,
            remark_text=remarks,
            remark_type=RemarkType.DIRECTOR
        )
        db.add(remark_entry)

    # Always generate / refresh routing suggestion on return to DS
    generate_routing_suggestion(db, doc_id, include_director_remark=True)

    doc.updated_at = datetime.now()
    doc.version += 1


    db_route = models.DocumentRoute(
        document_id=doc_id,
        from_user_id=current_user.id,
        to_user_id=ds_user_id,
        route_type=RouteType.RETURN_TO_DS,
        remarks=remarks or doc.director_remark,
    )
    db.add(db_route)
    db.commit()
    db.refresh(doc)

    ret_details = remarks or (f'Director Review Completed: "{doc.director_remark}"' if doc.director_remark else "Returned to Director Secretary with review comments")
    event = _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="RETURNED_TO_DS",
        from_role="DIRECTOR",
        to_role="DS",
        details=ret_details
    )

    _create_notification(
        db=db,
        user_id=ds_user_id,
        document_id=doc_id,
        workflow_event_id=event.id,
        title=f"Document returned: {doc.reference_no}",
        message=f"Director has returned '{doc.title}' to DS."
    )

    return doc


def save_hod_remark(db: Session, doc_id: int, remark: str, current_user: models.User,
                    expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.hod_remark = remark
    doc.updated_at = datetime.now()
    doc.version += 1

    remark_entry = models.DocumentRemark(
        document_id=doc_id,
        author_user_id=current_user.id,
        role=UserRole.HOD,
        remark_text=remark,
        remark_type=RemarkType.HOD
    )
    db.add(remark_entry)
    db.commit()
    db.refresh(doc)

    _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="HOD_REMARK_SAVED",
        from_role="HOD",
        to_role=None,
        details=f'HOD Remark: "{remark}"'
    )

    return doc


def _get_active_employee_context(
    db: Session,
    user_id: int,
    department_id: Optional[int] = None,
) -> Optional[models.WorkContextMembership]:
    """Return the user's active EMPLOYEE context, optionally for one department.

    Employee eligibility is membership-based, not persisted-role-based. This
    is required for users such as a TSO who also work as an EMPLOYEE in FCTD.
    """
    q = db.query(models.WorkContextMembership).filter(
        models.WorkContextMembership.user_id == user_id,
        models.WorkContextMembership.context_type == WorkContextType.EMPLOYEE,
        models.WorkContextMembership.is_active == True,
    )
    if department_id is not None:
        q = q.filter(models.WorkContextMembership.department_id == department_id)
    return q.order_by(models.WorkContextMembership.id.asc()).first()


def create_hod_team_assignment(
    db: Session,
    doc_id: int,
    request: schemas.HODTeamAssignmentRequest,
    current_user: models.User,
    context_id: Optional[int] = None
) -> Optional[models.WorkAssignment]:
    """Create a coworking assignment on exactly one canonical HOD branch."""
    doc = get_document(db, doc_id)
    # Branch operations are independent workstreams. Do not use the global
    # document version as a concurrency lock for one branch.
    if not doc:
        return None
    if current_user.role not in (UserRole.HOD, UserRole.DS):
        raise ValueError("Only HOD, DS, or Admin can create a team assignment.")

    member_ids = list(dict.fromkeys(int(uid) for uid in request.member_user_ids if uid))
    if not member_ids:
        raise ValueError("At least one employee must be selected.")

    selected_context = _resolve_context_membership(db, current_user, context_id)
    if current_user.role == UserRole.HOD:
        if not selected_context or selected_context.context_type != WorkContextType.HOD:
            raise ValueError("HOD operations require a selected HOD work context.")
        selected_department_id = selected_context.department_id
        if selected_department_id is None:
            raise ValueError("The selected HOD context has no department.")
    else:
        selected_department_id = (
            selected_context.department_id
            if selected_context and selected_context.context_type == WorkContextType.HOD
            else current_user.department_id
        )

    if request.routing_id is not None:
        branch = db.query(models.DocumentDepartmentRouting).filter(
            models.DocumentDepartmentRouting.id == request.routing_id,
            models.DocumentDepartmentRouting.document_id == doc_id,
            models.DocumentDepartmentRouting.branch_type == BranchType.DEPARTMENT_HOD,
            models.DocumentDepartmentRouting.is_active == True,
        ).first()
    elif current_user.role == UserRole.HOD and selected_department_id:
        branch = db.query(models.DocumentDepartmentRouting).filter(
            models.DocumentDepartmentRouting.document_id == doc_id,
            models.DocumentDepartmentRouting.department_id == selected_department_id,
            models.DocumentDepartmentRouting.branch_type == BranchType.DEPARTMENT_HOD,
            models.DocumentDepartmentRouting.is_active == True,
        ).order_by(models.DocumentDepartmentRouting.routed_at.desc()).first()
    else:
        branch = None

    if not branch:
        raise ValueError("An active canonical Department/HOD routing branch is required.")
    if current_user.role == UserRole.HOD and branch.department_id != selected_department_id:
        raise ValueError("HOD can assign only within the selected HOD context's department branch.")

    employees = db.query(models.User).filter(
        models.User.id.in_(member_ids),
        models.User.is_active == True,
    ).all()
    by_id = {u.id: u for u in employees}
    if any(uid not in by_id for uid in member_ids):
        raise ValueError("Every selected member must be an active user.")

    # Membership, not base User.role, defines whether a person can work as
    # an employee. This permits TSO + EMPLOYEE coexistence.
    employee_contexts = {}
    for uid in member_ids:
        membership = _get_active_employee_context(db, uid, selected_department_id)
        if not membership:
            raise ValueError(
                f"User {uid} does not have an active EMPLOYEE context"
                + (f" for department {selected_department_id}." if selected_department_id else ".")
            )
        employee_contexts[uid] = membership

    if current_user.role == UserRole.HOD and any(
        employee_contexts[uid].department_id != selected_department_id for uid in member_ids
    ):
        raise ValueError("HOD can assign only employees from the selected HOD context's department.")

    old = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.routing_id == branch.id,
        models.WorkAssignment.is_active == True,
    ).first()
    if old:
        raise ValueError("This routing branch already has an active assignment. Reassignment is not allowed.")
    primary = by_id[member_ids[0]]
    team_name = (request.team_name or "").strip() or None
    now = datetime.now()

    assignment = models.WorkAssignment(
        document_id=doc_id,
        routing_id=branch.id,
        assigned_by_user_id=current_user.id,
        assigned_to_user_id=primary.id,
        requires_hod_validation=bool(request.requires_hod_validation),
        instructions=request.instructions,
        team_name=team_name,
        is_team=len(member_ids) > 1 or bool(team_name),
        is_active=True,
        assigned_at=now,
    )
    db.add(assignment)
    db.flush()

    for user_id in member_ids:
        membership = employee_contexts[user_id]
        db.add(models.WorkAssignmentMember(
            work_assignment_id=assignment.id,
            user_id=user_id,
            context_membership_id=membership.id,
            is_active=True,
            assigned_at=now,
        ))

    branch.status = DocumentStatus.ASSIGNED_FOR_EXECUTION
    branch.target_user_id = primary.id
    branch.version += 1
    _refresh_document_overall_state(db, doc)
    doc.version += 1

    event = _add_workflow_history(
        db=db, document_id=doc_id, user_id=current_user.id,
        action="HOD_TEAM_ASSIGNED" if len(member_ids) > 1 or team_name else "HOD_WORK_ASSIGNED",
        from_role=current_user.role.value, to_role="EMPLOYEE",
        details=f"Canonical HOD branch {branch.id}; team={team_name or 'Individual'}; members={member_ids}; work_assignment_id={assignment.id}"
    )
    for user_id in member_ids:
        _create_notification(
            db=db, user_id=user_id, document_id=doc_id, workflow_event_id=event.id,
            title=f"Work Assignment: {doc.reference_no}",
            message=f"Document '{doc.title}' has been assigned to you" + (f" as part of team '{team_name}'." if team_name else ".")
        )
    db.commit()
    db.refresh(assignment)
    return assignment

def complete_work_assignment(db: Session, doc_id: int, assignment_id: int, current_user: models.User, context_id: Optional[int] = None) -> Optional[models.WorkAssignment]:
    assignment = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.id == assignment_id,
        models.WorkAssignment.document_id == doc_id,
        models.WorkAssignment.is_active == True,
    ).first()
    if not assignment:
        return None
    context = _resolve_context_membership(db, current_user, context_id)
    if context is None or context.context_type not in (WorkContextType.EMPLOYEE, WorkContextType.TSO):
        raise ValueError("Employee/TSO context required.")
    member = db.query(models.WorkAssignmentMember).filter(
        models.WorkAssignmentMember.work_assignment_id == assignment.id,
        models.WorkAssignmentMember.user_id == current_user.id,
        models.WorkAssignmentMember.context_membership_id == context.id,
        models.WorkAssignmentMember.is_active == True,
    ).first()
    direct = assignment.assigned_to_user_id == current_user.id and assignment.assigned_to_context_membership_id == context.id
    if not member and not direct:
        raise ValueError("You are not a member of this assignment.")
    now = datetime.now()
    if member:
        member.is_active = False
        member.completed_at = now
    # For an individual assignment, direct completion closes the assignment.
    remaining = db.query(models.WorkAssignmentMember).filter(
        models.WorkAssignmentMember.work_assignment_id == assignment.id,
        models.WorkAssignmentMember.is_active == True,
    ).count()
    if not assignment.is_team or remaining == 0:
        assignment.is_active = False
        assignment.completed_at = now
        if assignment.routing:
            assignment.routing.status = DocumentStatus.COMPLETED
            assignment.routing.is_active = False
            assignment.routing.completed_at = now
            assignment.routing.version += 1
    else:
        if assignment.routing:
            assignment.routing.status = DocumentStatus.PROGRESS_UPDATED
            assignment.routing.version += 1
    doc = get_document(db, doc_id)
    if doc:
        _refresh_document_overall_state(db, doc)
        doc.version += 1
    _add_workflow_history(db=db, document_id=doc_id, user_id=current_user.id,
                          action="ASSIGNMENT_COMPLETED", from_role=current_user.role.value,
                          to_role="DS", details=f"Assignment {assignment.id} completed by user {current_user.id}.")
    db.commit(); db.refresh(assignment)
    return assignment


def create_progress_update(
    db: Session,
    doc_id: int,
    prog: schemas.ProgressCreate,
    current_user: models.User,
    context_id: Optional[int] = None,
) -> Optional[models.ProgressUpdate]:
    """Create progress against exactly one active WorkAssignment."""
    doc = get_document(db, doc_id)
    if not doc:
        return None

    selected_context = _resolve_context_membership(db, current_user, context_id)
    if selected_context is None:
        raise ValueError("No active work context is available for this user.")
    if selected_context.context_type not in (WorkContextType.EMPLOYEE, WorkContextType.TSO):
        raise ValueError("Progress can only be submitted from an EMPLOYEE or TSO work context.")

    # Scope progress to the selected work-context membership. This prevents a
    # multi-context user (for example TSO + EMPLOYEE) from writing progress to
    # a workstream belonging to another active context.
    q = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.document_id == doc_id,
        models.WorkAssignment.is_active == True,
        or_(
            models.WorkAssignment.assigned_to_context_membership_id == selected_context.id,
            models.WorkAssignment.members.any(and_(
                models.WorkAssignmentMember.user_id == current_user.id,
                models.WorkAssignmentMember.context_membership_id == selected_context.id,
                models.WorkAssignmentMember.is_active == True,
            )),
        ),
    )
    if getattr(prog, "work_assignment_id", None):
        active_assign = q.filter(models.WorkAssignment.id == prog.work_assignment_id).first()
        if not active_assign:
            raise ValueError("The selected work assignment is not active or is not assigned to you.")
    else:
        candidates = q.order_by(models.WorkAssignment.assigned_at.desc()).all()
        if not candidates:
            raise ValueError("No active work assignment is available for this user on this document.")
        if len(candidates) > 1:
            raise ValueError("This document has multiple active workstreams. Select the specific work assignment before submitting progress.")
        active_assign = candidates[0]

    branch = active_assign.routing
    requires_hod = bool(active_assign.requires_hod_validation)
    if branch and branch.branch_type == BranchType.TSO:
        requires_hod = False
    elif branch and branch.branch_type == BranchType.DEPARTMENT_HOD:
        requires_hod = bool(active_assign.requires_hod_validation)

    progress = models.ProgressUpdate(
        document_id=doc_id, submitted_by_user_id=current_user.id,
        work_assignment_id=active_assign.id, description=prog.description,
        hod_validation_required=requires_hod,
        hod_validation_status=(ProgressValidationStatus.PENDING_HOD_REVIEW if requires_hod else ProgressValidationStatus.DIRECT_TO_DS),
    )
    db.add(progress)
    if branch:
        branch.status = DocumentStatus.PROGRESS_UPDATED
        branch.version += 1
    _refresh_document_overall_state(db, doc)
    doc.version += 1

    event = _add_workflow_history(
        db=db, document_id=doc_id, user_id=current_user.id,
        action="PROGRESS_SUBMITTED_FOR_HOD" if requires_hod else "PROGRESS_UPDATED",
        from_role=current_user.role.value, to_role="HOD" if requires_hod else "DS",
        details=f"Progress submitted on work_assignment_id={active_assign.id}, routing_id={branch.id if branch else None}: {prog.description}"
    )

    if requires_hod and branch and branch.department_id:
        hods = db.query(models.User).filter(
            models.User.department_id == branch.department_id,
            models.User.role == UserRole.HOD, models.User.is_active == True,
        ).all()
        for hod in hods:
            _create_notification(
                db=db, user_id=hod.id, document_id=doc_id, workflow_event_id=event.id,
                title=f"Progress awaiting HOD review: {doc.reference_no}",
                message=f"{current_user.full_name} submitted progress on '{doc.title}' for the HOD workstream."
            )
    elif doc.created_by:
        _create_notification(
            db=db, user_id=doc.created_by, document_id=doc_id, workflow_event_id=event.id,
            title=f"Progress update on {doc.reference_no}",
            message=f"{current_user.full_name} updated progress on '{doc.title}'."
        )

    db.commit()
    db.refresh(progress)
    return progress

def hod_validate_progress_update(
    db: Session,
    doc_id: int,
    progress_id: int,
    action: str,
    note: Optional[str],
    current_user: models.User,
    context_id: Optional[int] = None,
) -> Optional[models.ProgressUpdate]:
    progress = db.query(models.ProgressUpdate).filter(
        models.ProgressUpdate.id == progress_id,
        models.ProgressUpdate.document_id == doc_id
    ).first()
    if not progress:
        return None

    doc = get_document(db, doc_id)
    if not doc:
        return None

    selected_context = _resolve_context_membership(db, current_user, context_id)
    if (
        current_user.role != UserRole.HOD
        or not selected_context
        or selected_context.context_type != WorkContextType.HOD
        or selected_context.department_id is None
    ):
        raise ValueError("Only an HOD in a selected departmental HOD context can validate departmental progress.")

    selected_department_id = selected_context.department_id

    if progress.work_assignment and progress.work_assignment.routing:
        branch = progress.work_assignment.routing
        if (
            branch.branch_type != BranchType.DEPARTMENT_HOD
            or branch.department_id != selected_department_id
        ):
            raise ValueError("This progress update does not belong to the selected HOD context's department workstream.")
    else:
        raise ValueError("Progress update is not linked to a canonical workstream.")

    action_lower = action.lower().strip()
    if action_lower == "approve":
        progress.hod_validation_status = ProgressValidationStatus.HOD_APPROVED
        progress.hod_review_note = note
        progress.hod_reviewed_by_user_id = current_user.id
        progress.hod_reviewed_at = datetime.now()

        if progress.work_assignment and progress.work_assignment.routing:
            progress.work_assignment.routing.status = DocumentStatus.PROGRESS_UPDATED
            progress.work_assignment.routing.version += 1
        _refresh_document_overall_state(db, doc)
        doc.version += 1

        db.commit()
        db.refresh(progress)

        event = _add_workflow_history(
            db=db,
            document_id=doc_id,
            user_id=current_user.id,
            action="HOD_PROGRESS_APPROVED",
            from_role="HOD",
            to_role="DS",
            details=f"HOD approved progress update: {note or 'Validated and approved for DS'}"
        )

        # Notify DS
        if doc.created_by:
            _create_notification(
                db=db,
                user_id=doc.created_by,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"Validated progress on {doc.reference_no}",
                message=f"HOD approved employee progress on '{doc.title}'."
            )
        # Notify employee
        if progress.submitted_by_user_id:
            _create_notification(
                db=db,
                user_id=progress.submitted_by_user_id,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"Progress approved: {doc.reference_no}",
                message=f"HOD has approved your progress update on '{doc.title}'."
            )

    elif action_lower == "return":
        progress.hod_validation_status = ProgressValidationStatus.RETURNED_TO_EMPLOYEE
        progress.hod_review_note = note
        progress.hod_reviewed_by_user_id = current_user.id
        progress.hod_reviewed_at = datetime.now()
        if progress.work_assignment and progress.work_assignment.routing:
            progress.work_assignment.routing.status = DocumentStatus.IN_PROGRESS
            progress.work_assignment.routing.version += 1
        _refresh_document_overall_state(db, doc)
        doc.version += 1

        db.commit()
        db.refresh(progress)

        event = _add_workflow_history(
            db=db,
            document_id=doc_id,
            user_id=current_user.id,
            action="HOD_PROGRESS_RETURNED",
            from_role="HOD",
            to_role="EMPLOYEE",
            details=f"HOD requested correction: {note or 'Please revise and resubmit.'}"
        )

        # Notify employee
        if progress.submitted_by_user_id:
            _create_notification(
                db=db,
                user_id=progress.submitted_by_user_id,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"Update returned for correction: {doc.reference_no}",
                message=f"HOD requested correction on your update for '{doc.title}':\n{note or 'Please review remarks.'}"
            )
    else:
        return None

    return progress


def get_progress_updates(db: Session, doc_id: int) -> List[models.ProgressUpdate]:
    return db.query(models.ProgressUpdate).filter(models.ProgressUpdate.document_id == doc_id).order_by(models.ProgressUpdate.created_at).all()


def follow_up_to_director(db: Session, doc_id: int, director_user: models.User,
                          remarks: Optional[str], current_user: models.User,
                          expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.status = DocumentStatus.UNDER_DIRECTOR_REVIEW
    doc.updated_at = datetime.now()
    doc.version += 1

    db_route = models.DocumentRoute(
        document_id=doc_id,
        from_user_id=current_user.id,
        to_user_id=director_user.id,
        route_type=RouteType.FOLLOW_UP_TO_DIRECTOR,
        remarks=remarks,
    )
    db.add(db_route)
    db.commit()
    db.refresh(doc)

    event = _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="FOLLOW_UP_TO_DIRECTOR",
        from_role="DS",
        to_role="DIRECTOR",
        details=remarks or "Progress follow-up forwarded to Director for Executive Review"
    )

    _create_notification(
        db=db,
        user_id=director_user.id,
        document_id=doc_id,
        workflow_event_id=event.id,
        title=f"Follow-up for review: {doc.reference_no}",
        message=f"DS forwarded employee progress for '{doc.title}'."
    )

    return doc


def close_document(
    db: Session,
    doc_id: int,
    remarks: Optional[str],
    current_user: models.User,
    expected_version: Optional[int] = None
) -> Optional[models.Document]:

    doc = get_document(db, doc_id)

    if not doc or not check_concurrency(doc, expected_version):
        return None

    if current_user.role != UserRole.DS:
        raise ValueError("Only DS can close a document.")
    if doc.status == DocumentStatus.CLOSED:
        raise ValueError("Document is already closed.")
    # Final Director review is mandatory before closure.
    has_return = db.query(models.DocumentRoute).filter(
        models.DocumentRoute.document_id == doc_id,
        models.DocumentRoute.route_type == RouteType.RETURN_TO_DS,
    ).first() is not None
    if not has_return:
        raise ValueError("Document cannot be closed before final Director review is returned to DS.")
    active_branches = db.query(models.DocumentDepartmentRouting).filter(
        models.DocumentDepartmentRouting.document_id == doc_id, models.DocumentDepartmentRouting.is_active == True
    ).all()
    if any(b.status not in (DocumentStatus.COMPLETED, DocumentStatus.CLOSED) for b in active_branches):
        raise ValueError("Document cannot be closed while any routed branch is still active.")

    doc.status = DocumentStatus.CLOSED
    doc.closed_at = datetime.now()
    doc.updated_at = datetime.now()
    doc.version += 1

    # Deactivate and mark open branches as completed/closed
    open_branches = db.query(models.DocumentDepartmentRouting).filter(
        models.DocumentDepartmentRouting.document_id == doc_id,
        models.DocumentDepartmentRouting.is_active == True
    ).all()

    for br in open_branches:
        br.status = DocumentStatus.CLOSED
        br.is_active = False
        br.completed_at = datetime.now()

    # Deactivate active assignments
    db.query(models.WorkAssignment).filter(
        models.WorkAssignment.document_id == doc_id,
        models.WorkAssignment.is_active == True
    ).update({
        "is_active": False,
        "completed_at": datetime.now()
    })

    db.commit()
    db.refresh(doc)

    _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="DS_CLOSED_DOCUMENT",
        from_role="DS",
        to_role="CLOSED",
        details=(
            remarks
            or "DS finalized document lifecycle closure following Director instruction."
        )
    )

    return doc
    

# =========================================================
# REMARK HISTORY
# =========================================================

def get_document_remarks(db: Session, doc_id: int) -> List[models.DocumentRemark]:
    return (
        db.query(models.DocumentRemark)
        .filter(models.DocumentRemark.document_id == doc_id)
        .order_by(models.DocumentRemark.created_at.desc())
        .all()
    )


# =========================================================
# ATTACHMENTS & CHECKSUM
# =========================================================

def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_attachment(
    db: Session,
    doc_id: Optional[int],
    progress_update_id: Optional[int],
    uploaded_by: int,
    file_name: str,
    storage_key: str,
    file_type: Optional[str],
    file_size: Optional[int],
    checksum: Optional[str] = None,
    attachment_type: AttachmentType = AttachmentType.ORIGINAL,
    source_message_id: Optional[int] = None
) -> models.Attachment:
    att = models.Attachment(
        document_id=doc_id,
        progress_update_id=progress_update_id,
        uploaded_by_user_id=uploaded_by,
        file_name=file_name,
        storage_key=storage_key,
        file_type=file_type,
        file_size=file_size,
        checksum=checksum,
        attachment_type=attachment_type,
        source_message_id=source_message_id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    if doc_id:
        _add_workflow_history(
            db=db,
            document_id=doc_id,
            user_id=uploaded_by,
            action="ATTACHMENT_UPLOADED",
            from_role=None,
            to_role=None,
            details=f"File uploaded: {file_name} ({attachment_type.value})"
        )

    return att


def get_attachments(db: Session, doc_id: int) -> List[models.Attachment]:
    return db.query(models.Attachment).filter(models.Attachment.document_id == doc_id).order_by(models.Attachment.created_at).all()


def get_attachment(db: Session, attachment_id: int) -> Optional[models.Attachment]:
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()


# =========================================================
# OCR & STRUCTURED EXTRACTION PIPELINE
# =========================================================
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


def get_document_ocr(db: Session, doc_id: int) -> Optional[models.DocumentOCR]:
    return db.query(models.DocumentOCR).filter(models.DocumentOCR.document_id == doc_id).first()


def verify_extracted_field(db: Session, doc_id: int, field_name: str, verified_value: str, user: models.User) -> Optional[models.DocumentExtractedField]:
    field = db.query(models.DocumentExtractedField).filter(
        models.DocumentExtractedField.document_id == doc_id,
        models.DocumentExtractedField.field_name == field_name
    ).first()

    if not field:
        field = models.DocumentExtractedField(
            document_id=doc_id,
            field_name=field_name,
            extracted_value=verified_value,
            confidence=1.0,
            source_page=1
        )
        db.add(field)

    field.verified_value = verified_value
    field.verified_by = user.id
    field.verified_at = datetime.now()

    # If title was verified, update canonical document
    doc = get_document(db, doc_id)
    if doc and field_name == "TITLE":
        doc.title = verified_value
        doc.version += 1

    db.commit()
    db.refresh(field)
    return field


def reanalyze_document_ocr(db: Session, doc_id: int) -> Optional[models.DocumentOCR]:
    """Re-runs OCR extraction without overwriting fields that have been verified by DS."""
    return trigger_ocr_processing(db, doc_id)


# =========================================================
# ROUTING INTELLIGENCE & ADVISORY SUGGESTIONS
# =========================================================

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
    if include_director_remark and doc.director_remark:
        remark_lower = doc.director_remark.lower()

        # Employee name check (highest specificity)
        employees = get_employees(db)
        for emp in employees:
            if emp.full_name.lower() in remark_lower:
                suggested_emp_id = emp.user_id or (
                    db.query(models.User.id)
                    .filter(models.User.employee_id == emp.id)
                    .scalar()
                )
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
                        suggested_emp_id = emp.user_id or (
                            db.query(models.User.id)
                            .filter(models.User.employee_id == emp.id)
                            .scalar()
                        ) or emp.id
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


def get_routing_suggestion(db: Session, doc_id: int) -> Optional[models.RoutingSuggestion]:
    return db.query(models.RoutingSuggestion).filter(models.RoutingSuggestion.document_id == doc_id).first()


# =========================================================
# REMINDERS & DEADLINE ESCALATION LOGIC
# =========================================================

def generate_reminders(db: Session) -> List[models.Reminder]:
    today = date.today()
    active_docs = db.query(models.Document).filter(models.Document.status != DocumentStatus.CLOSED).all()
    created_reminders = []
    for doc in active_docs:
        reason = ReminderReason.OVERDUE if doc.deadline and doc.deadline < today else (ReminderReason.DUE_SOON if doc.deadline and doc.deadline <= today + timedelta(days=2) else ReminderReason.ACTION_REQUIRED)
        recipients = set()
        assignments = db.query(models.WorkAssignment).filter(models.WorkAssignment.document_id == doc.doc_id, models.WorkAssignment.is_active == True).all()
        for assignment in assignments:
            recipients.add(assignment.assigned_to_user_id)
            recipients.update(m.user_id for m in assignment.members if m.is_active)
        if not recipients:
            branches = db.query(models.DocumentDepartmentRouting).filter(models.DocumentDepartmentRouting.document_id == doc.doc_id, models.DocumentDepartmentRouting.is_active == True).all()
            for branch in branches:
                if branch.branch_type == BranchType.DEPARTMENT_HOD and branch.department_id:
                    recipients.update(u.id for u in db.query(models.User).filter(models.User.department_id == branch.department_id, models.User.role == UserRole.HOD, models.User.is_active == True).all())
                elif branch.target_user_id:
                    recipients.add(branch.target_user_id)
        if not recipients:
            recipients.add(doc.created_by)
        for uid in recipients:
            key = f"DOC_{doc.doc_id}_USER_{uid}_{reason.value}_{today.isoformat()}"
            if not db.query(models.Reminder).filter(models.Reminder.deduplication_key == key).first():
                created_reminders.append(models.Reminder(document_id=doc.doc_id, recipient_user_id=uid, reason=reason, due_at=datetime.combine(doc.deadline, datetime.min.time()) if doc.deadline else None, sent_at=datetime.now(), is_read=False, deduplication_key=key))
    if created_reminders:
        db.add_all(created_reminders)
        db.commit()
    return created_reminders


def get_reminders(db: Session, user_id: int) -> List[models.Reminder]:
    return (
        db.query(models.Reminder)
        .filter(models.Reminder.recipient_user_id == user_id)
        .order_by(models.Reminder.sent_at.desc())
        .all()
    )


def mark_reminder_read(db: Session, reminder_id: int, user_id: int) -> Optional[models.Reminder]:
    rem = db.query(models.Reminder).filter(
        models.Reminder.id == reminder_id,
        models.Reminder.recipient_user_id == user_id
    ).first()
    if rem:
        rem.is_read = True
        db.commit()
        db.refresh(rem)
    return rem


def send_document_reminder(
    db: Session,
    doc_id: int,
    current_user: models.User,
    custom_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Triggers an official action reminder for a single document based strictly on CURRENT workflow ownership:
    1. Active Work Assignment (Assigned Employee)
    2. Target Department HOD
    3. Current Owner (Director / DS)
    4. Creator (DS)
    """
    doc = get_document(db, doc_id)
    if not doc:
        return {"status": "error", "message": "Document not found."}

    if doc.status == DocumentStatus.CLOSED:
        return {"status": "error", "message": "Document is closed. Action reminders cannot be sent for closed documents."}

    # Resolve the latest active canonical workstream recipient.
    recipient: Optional[models.User] = None
    role_label = "Responsible Staff"
    active_assignment = db.query(models.WorkAssignment).filter(models.WorkAssignment.document_id == doc.doc_id, models.WorkAssignment.is_active == True).order_by(models.WorkAssignment.assigned_at.desc()).first()
    if active_assignment:
        recipient = active_assignment.assigned_to
        role_label = "Assigned Employee"
    else:
        branch = db.query(models.DocumentDepartmentRouting).filter(models.DocumentDepartmentRouting.document_id == doc.doc_id, models.DocumentDepartmentRouting.is_active == True).order_by(models.DocumentDepartmentRouting.routed_at.desc()).first()
        if branch and branch.branch_type == BranchType.DEPARTMENT_HOD and branch.department_id:
            recipient = db.query(models.User).filter(models.User.department_id == branch.department_id, models.User.role == UserRole.HOD, models.User.is_active == True).first()
            role_label = "Department HOD"
        elif branch and branch.target_user_id:
            recipient = db.query(models.User).filter(models.User.id == branch.target_user_id, models.User.is_active == True).first()
            role_label = recipient.role.value if recipient else "Responsible Staff"
    if not recipient:
        return {"status": "error", "message": "No active workflow recipient could be resolved for this document."}

    today = date.today()
    reason = ReminderReason.ACTION_REQUIRED
    if doc.deadline:
        if doc.deadline < today:
            reason = ReminderReason.OVERDUE
        elif doc.deadline <= today + timedelta(days=2):
            reason = ReminderReason.DUE_SOON

    # Deduplication and DB record
    dedup_key = f"DOC_{doc.doc_id}_USER_{recipient.id}_{reason.value}_{today.isoformat()}_{int(datetime.now().timestamp())}"
    reminder = models.Reminder(
        document_id=doc.doc_id,
        recipient_user_id=recipient.id,
        reason=reason,
        due_at=datetime.combine(doc.deadline, datetime.min.time()) if doc.deadline else None,
        sent_at=datetime.now(),
        is_read=False,
        deduplication_key=dedup_key
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    default_msg = f"Action reminder dispatched for document {doc.reference_no} ({doc.title}). Immediate action required."
    rem_msg = custom_message or default_msg

    # Log workflow history & in-app notification
    entry = _add_workflow_history(
        db=db,
        document_id=doc.doc_id,
        user_id=current_user.id,
        action="ACTION_REMINDER_SENT",
        from_role=current_user.role.value,
        to_role=recipient.role.value,
        details=f"Official reminder sent to {recipient.full_name} ({role_label}): {rem_msg}"
    )

    _create_notification(
        db=db,
        user_id=recipient.id,
        document_id=doc.doc_id,
        workflow_event_id=entry.id,
        title=f"Action Reminder: {doc.reference_no}",
        message=rem_msg
    )

    # Dispatched via MailService
    email_dispatched = False
    channel_used = recipient.preferred_mail_channel or "outlook"
    email_addr = None

    try:
        from mail.service import mail_service
        email_addr = mail_service.resolve_user_email(recipient)
        email_dispatched = mail_service.send_workflow_notification(
            db=db,
            doc_id=doc.doc_id,
            recipient_user_id=recipient.id,
            title=f"Action Reminder ({role_label})",
            message=rem_msg,
            channel=channel_used
        )
    except Exception as ex:
        pass

    return {
        "status": "success",
        "recipient_user_id": recipient.id,
        "recipient_name": recipient.full_name,
        "recipient_email": email_addr or recipient.email,
        "recipient_role": role_label,
        "document_id": doc.doc_id,
        "document_reference": doc.reference_no,
        "document_title": doc.title,
        "channel_used": channel_used,
        "email_dispatched": email_dispatched,
        "message": f"Action reminder successfully dispatched to {recipient.full_name} ({role_label})."
    }


# =========================================================
# WORKFLOW HISTORY
# =========================================================

def _add_workflow_history(
    db: Session,
    document_id: int,
    user_id: int,
    action: str,
    from_role: Optional[str] = None,
    to_role: Optional[str] = None,
    details: Optional[str] = None,
) -> models.WorkflowHistory:

    entry = models.WorkflowHistory(
        document_id=document_id,
        performed_by_user_id=user_id,
        action=action,
        from_role=from_role,
        to_role=to_role,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_document_history(db: Session, doc_id: int) -> List[models.WorkflowHistory]:
    return (
        db.query(models.WorkflowHistory)
        .filter(models.WorkflowHistory.document_id == doc_id)
        .order_by(models.WorkflowHistory.created_at)
        .all()
    )


def get_all_workflow_history(db: Session, current_user: models.User) -> List[models.WorkflowHistory]:
    """Retrieves all workflow history events accessible to current user in a single database query."""
    if current_user.role in (UserRole.DS, UserRole.DIRECTOR):
        return db.query(models.WorkflowHistory).order_by(models.WorkflowHistory.created_at.desc()).all()
    elif current_user.role == UserRole.HOD:
        if not current_user.department_id:
            return []
        return (
            db.query(models.WorkflowHistory)
            .join(models.Document, models.WorkflowHistory.document_id == models.Document.doc_id)
            .filter(models.DocumentDepartmentRouting.department_id == current_user.department_id)
            .order_by(models.WorkflowHistory.created_at.desc())
            .all()
        )
    elif current_user.role == UserRole.EMPLOYEE:
        assigned_doc_ids = (
            db.query(models.WorkAssignment.document_id)
            .filter(models.WorkAssignment.assigned_to_user_id == current_user.id)
            .subquery()
        )
        return (
            db.query(models.WorkflowHistory)
            .join(models.Document, models.WorkflowHistory.document_id == models.Document.doc_id)
            .filter(
                (models.Document.doc_id.in_(assigned_doc_ids))
            )
            .order_by(models.WorkflowHistory.created_at.desc())
            .all()
        )
    return []


# =========================================================
# NOTIFICATIONS
# =========================================================

def _create_notification(
    db: Session,
    user_id: int,
    document_id: Optional[int] = None,
    workflow_event_id: Optional[int] = None,
    title: str = "",
    message: str = ""
) -> models.Notification:
    notif = models.Notification(
        user_id=user_id,
        document_id=document_id,
        workflow_event_id=workflow_event_id,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Attempt workflow email dispatch if document_id is present
    if document_id:
        try:
            from mail.service import mail_service
            mail_service.send_workflow_notification(
                db=db,
                doc_id=document_id,
                recipient_user_id=user_id,
                title=title,
                message=message
            )
        except Exception:
            pass

    return notif


def get_notifications(db: Session, user_id: int) -> List[models.Notification]:
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.created_at.desc()).all()


def get_unread_notifications(db: Session, user_id: int) -> List[models.Notification]:
    return db.query(models.Notification).filter(models.Notification.user_id == user_id, models.Notification.is_read == False).order_by(models.Notification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id: int, user_id: int) -> Optional[models.Notification]:
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.user_id == user_id).first()
    if not notif:
        return None
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    updated = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id, models.Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return updated


# =========================================================
# AUDIT LOG
# =========================================================

def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.AuditLog:
    audit = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(audit)
    db.commit()
    return audit


def get_audit_logs(db: Session) -> List[models.AuditLog]:
    return db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).all()


# =========================================================
# DASHBOARD STATS
# =========================================================

def get_dashboard_stats(db: Session, user: models.User) -> dict:
    unread_notifs = (
        db.query(func.count(models.Notification.id))
        .filter(models.Notification.user_id == user.id, models.Notification.is_read == False)
        .scalar()
    ) or 0

    unread_reminders = (
        db.query(func.count(models.Reminder.id))
        .filter(models.Reminder.recipient_user_id == user.id, models.Reminder.is_read == False)
        .scalar()
    ) or 0

    if user.role == UserRole.DS:
        total = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id)
            .scalar()
        ) or 0

        under_director = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.status == DocumentStatus.UNDER_DIRECTOR_REVIEW)
            .scalar()
        ) or 0

        under_hod = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.status == DocumentStatus.UNDER_HOD_PROCESSING)
            .scalar()
        ) or 0

        in_progress = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.status.in_([DocumentStatus.ASSIGNED_FOR_EXECUTION, DocumentStatus.IN_PROGRESS, DocumentStatus.PROGRESS_UPDATED]))
            .scalar()
        ) or 0

        closed = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.status == DocumentStatus.CLOSED)
            .scalar()
        ) or 0

        intake_pending = (
            db.query(func.count(models.IncomingMessage.id))
            .filter(models.IncomingMessage.processing_status == MessageProcessingStatus.NEW)
            .scalar()
        ) or 0

        pending = total - closed

        return {
            "role": user.role.value,
            "total_documents": total,
            "pending_action": pending,
            "unread_notifications": unread_notifs,
            "unread_reminders": unread_reminders,
            "under_director_review": under_director,
            "under_hod_processing": under_hod,
            "in_progress": in_progress,
            "closed_documents": closed,
            "intake_pending": intake_pending
        }

    elif user.role == UserRole.DIRECTOR:
        for_review = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.status == DocumentStatus.UNDER_DIRECTOR_REVIEW)
            .scalar()
        ) or 0

        return {
            "role": user.role.value,
            "total_documents": for_review,
            "pending_action": for_review,
            "unread_notifications": unread_notifs,
            "unread_reminders": unread_reminders,
            "documents_for_review": for_review,
        }

    elif user.role == UserRole.HOD:
        dept_docs = 0
        pending_assignment = 0
        if user.department_id:
            q = db.query(models.DocumentDepartmentRouting).filter(
                models.DocumentDepartmentRouting.department_id == user.department_id,
                models.DocumentDepartmentRouting.branch_type == BranchType.DEPARTMENT_HOD,
                models.DocumentDepartmentRouting.is_active == True,
            )
            dept_docs = q.count()
            pending_assignment = q.filter(
                models.DocumentDepartmentRouting.status == DocumentStatus.UNDER_HOD_PROCESSING
            ).count()
        return {
            "role": user.role.value,
            "total_documents": dept_docs,
            "pending_action": pending_assignment,
            "unread_notifications": unread_notifs,
            "unread_reminders": unread_reminders,
            "pending_assignment": pending_assignment,
        }

    elif user.role == UserRole.EMPLOYEE:
        active = (
            db.query(func.count(models.WorkAssignment.id))
            .filter(models.WorkAssignment.assigned_to_user_id == user.id, models.WorkAssignment.is_active == True)
            .scalar()
        ) or 0

        return {
            "role": user.role.value,
            "total_documents": active,
            "pending_action": active,
            "unread_notifications": unread_notifs,
            "unread_reminders": unread_reminders,
            "active_assignments": active,
        }

    return {
        "role": user.role.value,
        "total_documents": 0,
        "pending_action": 0,
        "unread_notifications": unread_notifs,
        "unread_reminders": unread_reminders
    }


# =========================================================
# =========================================================
# COMPREHENSIVE SEED DATA (Exact 3 Departments & 6 Employees)
# =========================================================

def seed_data(db: Session) -> None:
    """
    Populates the database with departments, system accounts, and employees.
    Dynamically loads from backend/data/seed_data.json if present.
    """
    import json
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "seed_data.json")
    loaded_json = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_json = json.load(f)
        except Exception as ex:
            print(f"[WARN] Could not parse seed_data.json: {ex}")

    # 1. Departments
    depts_data = loaded_json.get("departments") or [
        {"name": "Finance", "code": "FIN"},
        {"name": "HR", "code": "HR"},
        {"name": "Technical", "code": "TECH"},
    ]

    dept_map = {}
    for d in depts_data:
        existing = db.query(models.Department).filter(models.Department.name == d["name"]).first()
        if not existing:
            dept = models.Department(name=d["name"], code=d["code"])
            db.add(dept)
            db.commit()
            db.refresh(dept)
            dept_map[d["name"]] = dept.id
        else:
            dept_map[d["name"]] = existing.id

    # 2. Employees
    raw_employees = loaded_json.get("employees") or [
        {"employee_code": "EMP-FIN-001", "username": "emp_rahul", "full_name": "Rahul Sharma", "department": "Finance", "designation": "Accounts Officer", "email": "rahul.sharma@cdtrs.gov.in", "outlook_email": "rahul.sharma@outlook.com", "gov_email": "rahul.sharma@nic.in", "default_password": "cdtrs@emp"},
        {"employee_code": "EMP-FIN-002", "username": "emp_sunil", "full_name": "Sunil Gupta", "department": "Finance", "designation": "Senior Accountant", "email": "sunil.gupta@cdtrs.gov.in", "outlook_email": "sunil.gupta@outlook.com", "gov_email": "sunil.gupta@nic.in", "default_password": "cdtrs@emp"},
        {"employee_code": "EMP-HR-001", "username": "emp_sneha", "full_name": "Sneha Deshmukh", "department": "HR", "designation": "HR Officer", "email": "sneha.deshmukh@cdtrs.gov.in", "outlook_email": "sneha.deshmukh@outlook.com", "gov_email": "sneha.deshmukh@nic.in", "default_password": "cdtrs@emp"},
        {"employee_code": "EMP-HR-002", "username": "emp_pooja", "full_name": "Pooja Nair", "department": "HR", "designation": "Establishment Specialist", "email": "pooja.nair@cdtrs.gov.in", "outlook_email": "pooja.nair@outlook.com", "gov_email": "pooja.nair@nic.in", "default_password": "cdtrs@emp"},
        {"employee_code": "EMP-TECH-001", "username": "emp_anil", "full_name": "Anil Kumar", "department": "Technical", "designation": "Systems Engineer", "email": "anil.kumar@cdtrs.gov.in", "outlook_email": "anil.kumar@outlook.com", "gov_email": "anil.kumar@nic.in", "default_password": "cdtrs@emp"},
        {"employee_code": "EMP-TECH-002", "username": "emp_vikram", "full_name": "Vikram Malhotra", "department": "Technical", "designation": "Network & IT Admin", "email": "vikram.malhotra@cdtrs.gov.in", "outlook_email": "vikram.malhotra@outlook.com", "gov_email": "vikram.malhotra@nic.in", "default_password": "cdtrs@emp"},
    ]

    emp_map = {}
    for emp_d in raw_employees:
        code_val = emp_d.get("employee_code") or emp_d.get("code")
        dept_name = emp_d.get("department") or emp_d.get("dept") or "General"
        dept_id = dept_map.get(dept_name)
        if not dept_id and dept_map:
            dept_id = next(iter(dept_map.values()))

        existing = db.query(models.Employee).filter(models.Employee.employee_code == code_val).first()
        if not existing:
            emp = models.Employee(
                employee_code=code_val,
                full_name=emp_d.get("full_name") or emp_d.get("name"),
                department_id=dept_id,
                designation=emp_d.get("designation") or "Staff",
                email=emp_d.get("email"),
                outlook_email=emp_d.get("outlook_email"),
                gov_email=emp_d.get("gov_email")
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)
            emp_map[code_val] = emp.id
        else:
            existing.email = emp_d.get("email")
            existing.outlook_email = emp_d.get("outlook_email")
            existing.gov_email = emp_d.get("gov_email")
            db.commit()
            emp_map[code_val] = existing.id

    # 3. Users (System & Role Accounts)
    raw_system_users = loaded_json.get("system_users") or [
        {
            "username": "ds_user",
            "password": "cdtrs@ds",
            "full_name": "Director Secretary",
            "role": UserRole.DS,
            "email": "ds.office@cdtrs.gov.in",
            "outlook_email": "ds.office@outlook.com",
            "gov_email": "ds.office@nic.in",
            "department_id": None,
            "employee_id": None
        },
        {
            "username": "director",
            "password": "cdtrs@director",
            "full_name": "The Director",
            "role": UserRole.DIRECTOR,
            "email": "director@cdtrs.gov.in",
            "outlook_email": "director@outlook.com",
            "gov_email": "director@nic.in",
            "department_id": None,
            "employee_id": None
        },
        {
            "username": "hod_finance",
            "password": "cdtrs@hod",
            "full_name": "Head of Finance",
            "role": UserRole.HOD,
            "email": "hod.finance@cdtrs.gov.in",
            "outlook_email": "hod.finance@outlook.com",
            "gov_email": "hod.finance@nic.in",
            "department_id": dept_map.get("Finance"),
            "employee_id": None
        },
        {
            "username": "hod_hr",
            "password": "cdtrs@hod",
            "full_name": "Head of Human Resources",
            "role": UserRole.HOD,
            "email": "hod.hr@cdtrs.gov.in",
            "outlook_email": "hod.hr@outlook.com",
            "gov_email": "hod.hr@nic.in",
            "department_id": dept_map.get("HR"),
            "employee_id": None
        },
        {
            "username": "hod_tech",
            "password": "cdtrs@hod",
            "full_name": "Head of Technical & IT",
            "role": UserRole.HOD,
            "email": "hod.tech@cdtrs.gov.in",
            "outlook_email": "hod.tech@outlook.com",
            "gov_email": "hod.tech@nic.in",
            "department_id": dept_map.get("Technical"),
            "employee_id": None
        },
    ]

    users_data = []
    # Add system users
    for su in raw_system_users:
        dept_name = su.get("department")
        dept_id = dept_map.get(dept_name) if dept_name else su.get("department_id")
        role_raw = su.get("role")
        role_val = UserRole(role_raw) if isinstance(role_raw, str) else role_raw
        managed_depts_val = json.dumps(su.get("managed_depts", [])) if isinstance(su.get("managed_depts"), list) else su.get("managed_depts")
        
        users_data.append({
            "username": su["username"],
            "password": su.get("default_password") or su.get("password") or "cdtrs@123",
            "full_name": su["full_name"],
            "role": role_val,
            "employee_code": su.get("employee_code"),
            "designation": su.get("designation"),
            "department": dept_name,
            "managed_depts": managed_depts_val,
            "email": su.get("email"),
            "outlook_email": su.get("outlook_email"),
            "gov_email": su.get("gov_email"),
            "department_id": dept_id,
            "employee_id": su.get("employee_id")
        })

    # Add employee user accounts
    for emp_d in raw_employees:
        code_val = emp_d.get("employee_code") or emp_d.get("code")
        dept_name = emp_d.get("department") or emp_d.get("dept") or "General"
        dept_id = dept_map.get(dept_name)
        username = emp_d.get("username")
        if not username:
            parts = emp_d.get("full_name", "emp").lower().split()
            username = f"emp_{parts[0]}" if len(parts) == 1 else f"emp_{parts[0]}_{parts[-1]}"
        managed_depts_val = json.dumps(emp_d.get("managed_depts", [])) if isinstance(emp_d.get("managed_depts"), list) else emp_d.get("managed_depts")

        users_data.append({
            "username": username,
            "password": emp_d.get("default_password") or "cdtrs@emp",
            "full_name": emp_d.get("full_name") or emp_d.get("name"),
            "role": UserRole.EMPLOYEE,
            "employee_code": code_val,
            "designation": emp_d.get("designation") or "Staff",
            "department": dept_name,
            "managed_depts": managed_depts_val,
            "email": emp_d.get("email"),
            "outlook_email": emp_d.get("outlook_email"),
            "gov_email": emp_d.get("gov_email"),
            "department_id": dept_id,
            "employee_id": emp_map.get(code_val)
        })

    user_objs = {}
    for u in users_data:
        existing = get_user_by_username(db, u["username"])
        if not existing:
            user = models.User(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                employee_code=u.get("employee_code"),
                designation=u.get("designation"),
                managed_depts=u.get("managed_depts"),
                email=u["email"],
                outlook_email=u["outlook_email"],
                gov_email=u["gov_email"],
                preferred_mail_channel="outlook",
                department_id=u["department_id"],
                employee_id=u["employee_id"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_objs[u["username"]] = user
        else:
            existing.employee_code = u.get("employee_code") or existing.employee_code
            existing.designation = u.get("designation") or existing.designation
            if u.get("department_id") is not None:
                existing.department_id = u["department_id"]
            existing.managed_depts = u.get("managed_depts") or existing.managed_depts

            if not existing.email:
                existing.email = u["email"]
                existing.outlook_email = u["outlook_email"]
                existing.gov_email = u["gov_email"]
            db.commit()
            user_objs[u["username"]] = existing

        # Link employee record to user record bidirectionally
        if u["employee_id"]:
            db_emp = db.query(models.Employee).filter(models.Employee.id == u["employee_id"]).first()
            if db_emp and not db_emp.user_id:
                db_emp.user_id = user_objs[u["username"]].id
                db.commit()

    # 4. Canonical work-context memberships
    #
    # Keep the existing user/role seed untouched.  Context membership is an
    # additional authorization/workspace layer used by the frontend context
    # selector.  Reuse an existing membership when present so running
    # seed_data() repeatedly does not create duplicates.
    #
    # If seed_data.json explicitly provides "contexts" for a user, those
    # definitions are authoritative.  Otherwise create the normal single
    # context implied by the user's role and department.
    default_contexts = {
        UserRole.ADMIN: [{"context": "ADMIN", "department": None}],
        UserRole.DS: [{"context": "DS", "department": None}],
        UserRole.DIRECTOR: [{"context": "DIRECTOR", "department": None}],
        UserRole.HOD: [{"context": "HOD", "department_from_user": True}],
        UserRole.EMPLOYEE: [{"context": "EMPLOYEE", "department_from_user": True}],
        UserRole.TSO: [{"context": "TSO", "department": None}],
    }

    def _context_type_from_value(value):
        if isinstance(value, WorkContextType):
            return value
        try:
            return WorkContextType(value)
        except Exception:
            try:
                return WorkContextType[str(value).upper()]
            except Exception:
                return None

    def _ensure_context_membership(user_obj, context_def):
        context_value = context_def.get("context") or context_def.get("context_type")
        context_type = _context_type_from_value(context_value)
        if context_type is None:
            return

        department_id = None

        # Accept both the current seed format (department_code) and the
        # compact internal format used by the fallback definitions above.
        department_code = context_def.get("department_code")
        if department_code:
            dept = db.query(models.Department).filter(
                models.Department.code == department_code,
                models.Department.is_active == True,
            ).first()
            if not dept:
                raise ValueError(
                    f"Department '{department_code}' not found while creating "
                    f"{context_type.value} context for {user_obj.username}."
                )
            department_id = dept.id
        elif context_def.get("department_from_user"):
            department_id = user_obj.department_id

        existing_mem = db.query(models.WorkContextMembership).filter(
            models.WorkContextMembership.user_id == user_obj.id,
            models.WorkContextMembership.context_type == context_type,
            models.WorkContextMembership.department_id == department_id,
        ).first()

        if existing_mem:
            if not existing_mem.is_active:
                existing_mem.is_active = True
            return existing_mem

        # Do not create a second active TSO.  The canonical helper enforces
        # that system-wide rule when a TSO context is explicitly seeded.
        if context_type == WorkContextType.TSO:
            return set_active_tso(db, user_obj.id)

        membership = models.WorkContextMembership(
            user_id=user_obj.id,
            context_type=context_type,
            department_id=department_id,
            is_active=True,
        )
        db.add(membership)
        db.flush()
        return membership

    # Seed definitions first, then also repair contexts for any already-existing
    # active account that was created by an older seed run.
    explicit_context_map = {}
    for source_def in list(raw_system_users) + list(raw_employees):
        if source_def.get("username") and source_def.get("contexts") is not None:
            explicit_context_map[source_def["username"]] = source_def.get("contexts")

    active_users = db.query(models.User).filter(models.User.is_active == True).all()
    for user_obj in active_users:
        explicit_contexts = explicit_context_map.get(user_obj.username)
        context_defs = (
            explicit_contexts
            if explicit_contexts
            else default_contexts.get(user_obj.role, [])
        )
        for context_def in context_defs:
            _ensure_context_membership(user_obj, context_def)

    db.commit()

    print(f"[CDTRS SEED] Successfully verified {len(dept_map)} departments, {len(users_data)} accounts, and canonical work contexts.", flush=True)


# =========================================================
# ADMINISTRATOR CRUD & SYSTEM OPERATIONS
# =========================================================

def log_audit_event(
    db: Session,
    user_id: int,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.AuditLog:
    log_entry = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        created_at=datetime.now()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_admin_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()



def create_admin_user(db: Session, user_data: dict, performed_by_user_id: int = 1) -> models.User:
    raw_pwd = user_data.get("password") or "cdtrs@123"
    managed_depts = user_data.get("managed_depts")
    if isinstance(managed_depts, list):
        import json
        managed_depts = json.dumps(managed_depts)

    role_val = user_data.get("role")
    if isinstance(role_val, str):
        role_val = UserRole(role_val)

    db_user = models.User(
        username=user_data["username"],
        password_hash=hash_password(raw_pwd),
        full_name=user_data["full_name"],
        role=role_val,
        employee_code=user_data.get("employee_code"),
        designation=user_data.get("designation"),
        managed_depts=managed_depts,
        email=user_data.get("email"),
        outlook_email=user_data.get("outlook_email"),
        gov_email=user_data.get("gov_email"),
        preferred_mail_channel=user_data.get("preferred_mail_channel", "outlook"),
        department_id=user_data.get("department_id"),
        is_active=user_data.get("is_active", True)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # If employee role, also create/sync Employee record
    if role_val == UserRole.EMPLOYEE and user_data.get("department_id"):
        db_emp = models.Employee(
            employee_code=user_data.get("employee_code") or f"EMP-{db_user.id:03d}",
            full_name=user_data["full_name"],
            department_id=user_data["department_id"],
            designation=user_data.get("designation") or "Staff",
            email=user_data.get("email"),
            outlook_email=user_data.get("outlook_email"),
            gov_email=user_data.get("gov_email"),
            user_id=db_user.id
        )
        db.add(db_emp)
        db.commit()
        db.refresh(db_emp)
        db_user.employee_id = db_emp.id
        db.commit()

    log_audit_event(db, user_id=performed_by_user_id, action="USER_CREATED", entity_type="User", entity_id=db_user.id, description=f"Admin created user {db_user.username} ({db_user.role})")
    return db_user


def update_admin_user(db: Session, user_id: int, user_data: dict, performed_by_user_id: int = 1) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    if "full_name" in user_data and user_data["full_name"]:
        user.full_name = user_data["full_name"]
    if "role" in user_data and user_data["role"]:
        user.role = UserRole(user_data["role"]) if isinstance(user_data["role"], str) else user_data["role"]
    if "employee_code" in user_data:
        user.employee_code = user_data["employee_code"]
    if "designation" in user_data:
        user.designation = user_data["designation"]
    if "department_name" in user_data and user_data["department_name"]:
        dept = db.query(models.Department).filter(
            models.Department.name == user_data["department_name"]
        ).first()
        if not dept:
            raise ValueError(f"Department '{user_data['department_name']}' not found.")
        user.department_id = dept.id
    if "department_id" in user_data:
        user.department_id = user_data["department_id"]
    if "managed_depts" in user_data:
        m = user_data["managed_depts"]
        import json
        user.managed_depts = json.dumps(m) if isinstance(m, list) else m
    if "email" in user_data:
        user.email = user_data["email"]
    if "outlook_email" in user_data:
        user.outlook_email = user_data["outlook_email"]
    if "gov_email" in user_data:
        user.gov_email = user_data["gov_email"]
    if "is_active" in user_data:
        user.is_active = user_data["is_active"]

    db.commit()
    db.refresh(user)
    log_audit_event(db, user_id=performed_by_user_id, action="USER_UPDATED", entity_type="User", entity_id=user.id, description=f"Admin updated user {user.username}")
    return user


def reset_user_password(db: Session, user_id: int, new_password: str, performed_by_user_id: int = 1) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    user.password_hash = hash_password(new_password)
    db.commit()
    log_audit_event(db, user_id=performed_by_user_id, action="PASSWORD_RESET", entity_type="User", entity_id=user.id, description=f"Password reset for user {user.username}")
    return True


def toggle_user_active(db: Session, user_id: int, performed_by_user_id: int = 1) -> Optional[bool]:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    user.is_active = not user.is_active
    db.commit()
    log_audit_event(db, user_id=performed_by_user_id, action="USER_STATUS_TOGGLED", entity_type="User", entity_id=user.id, description=f"User {user.username} active status set to {user.is_active}")
    return user.is_active


def get_all_departments(db: Session, include_inactive: bool = False):
    query = db.query(models.Department)
    if not include_inactive:
        query = query.filter(models.Department.is_active == True)
    return query.order_by(models.Department.name).all()


def create_admin_department(db: Session, dept_data: dict, performed_by_user_id: int = 1) -> models.Department:
    dept = models.Department(
        name=dept_data["name"],
        code=dept_data.get("code") or dept_data["name"][:10].upper(),
        is_active=dept_data.get("is_active", True)
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit_event(db, user_id=performed_by_user_id, action="DEPARTMENT_CREATED", entity_type="Department", entity_id=dept.id, description=f"Admin created department {dept.name} ({dept.code})")
    return dept


def update_admin_department(db: Session, dept_id: int, dept_data: dict, performed_by_user_id: int = 1) -> Optional[models.Department]:
    dept = db.query(models.Department).filter(models.Department.id == dept_id).first()
    if not dept:
        return None
    if "name" in dept_data and dept_data["name"]:
        dept.name = dept_data["name"]
    if "code" in dept_data and dept_data["code"]:
        dept.code = dept_data["code"]
    if "is_active" in dept_data:
        dept.is_active = dept_data["is_active"]
    db.commit()
    db.refresh(dept)
    log_audit_event(db, user_id=performed_by_user_id, action="DEPARTMENT_UPDATED", entity_type="Department", entity_id=dept.id, description=f"Admin updated department {dept.name}")
    return dept


def get_system_settings(db: Session) -> dict:
    settings = db.query(models.SystemSetting).all()
    defaults = {
        "priority_red_days": "0",
        "priority_orange_days": "3",
        "priority_yellow_days": "7",
        "reminder_email_subject": "ACTION REQUIRED: CDTRS Document Reminder - {reference}",
        "reminder_email_template": "Dear {assignee_name},\n\nThis is an automated reminder regarding document '{title}' (Ref: {reference}).\nDeadline: {deadline} ({days_left} remaining).\n\nPlease review and take necessary action.\n\nCDTRS Automated Dispatch System"
    }
    res = dict(defaults)
    for s in settings:
        res[s.key] = s.value
    return res


def update_system_setting(db: Session, key: str, value: str, description: Optional[str] = None, performed_by_user_id: int = 1) -> models.SystemSetting:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if not setting:
        setting = models.SystemSetting(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description:
            setting.description = description
    db.commit()
    db.refresh(setting)
    log_audit_event(db, user_id=performed_by_user_id, action="SETTING_UPDATED", entity_type="SystemSetting", entity_id=setting.id, description=f"Admin updated setting {key}")
    return setting


def get_admin_audit_logs(db: Session, limit: int = 100, offset: int = 0):
    """Return audit log entries for admin-role users only, to avoid log overflow from regular employee activity."""
    return (
        db.query(models.AuditLog)
        .join(models.User, models.User.id == models.AuditLog.user_id, isouter=True)
        .filter(
            (models.User.role == UserRole.ADMIN) | (models.AuditLog.user_id == None)
        )
        .order_by(models.AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_user_context_memberships(db: Session, user_id: int) -> List[models.WorkContextMembership]:
    """Retrieve all active work context memberships for a given user."""
    return (
        db.query(models.WorkContextMembership)
        .filter(
            models.WorkContextMembership.user_id == user_id,
            models.WorkContextMembership.is_active == True
        )
        .all()
    )


def get_context_membership(db: Session, membership_id: int) -> Optional[models.WorkContextMembership]:
    """Retrieve a single work context membership by ID."""
    return (
        db.query(models.WorkContextMembership)
        .filter(models.WorkContextMembership.id == membership_id)
        .first()
    )


def validate_user_context(db: Session, user_id: int, context_id: int) -> Optional[models.WorkContextMembership]:
    """Ensure that the given context membership belongs to the user and is currently active."""
    membership = get_context_membership(db, context_id)
    if membership and membership.user_id == user_id and membership.is_active:
        return membership
    return None


def get_single_active_tso(db: Session) -> Optional[models.WorkContextMembership]:
    """Retrieve the single active TSO membership in the system."""
    return (
        db.query(models.WorkContextMembership)
        .filter(
            models.WorkContextMembership.context_type == WorkContextType.TSO,
            models.WorkContextMembership.is_active == True
        )
        .first()
    )


def set_active_tso(db: Session, user_id: int) -> models.WorkContextMembership:
    """
    Enforce the rule: Exactly one active TSO person at a time.
    Deactivates any existing active TSO memberships and activates the target user as TSO.
    """
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise ValueError(f"User with ID {user_id} not found.")

    # Deactivate existing active TSO memberships
    db.query(models.WorkContextMembership).filter(
        models.WorkContextMembership.context_type == WorkContextType.TSO,
        models.WorkContextMembership.is_active == True
    ).update({"is_active": False})

    target_mem = db.query(models.WorkContextMembership).filter(
        models.WorkContextMembership.user_id == user_id,
        models.WorkContextMembership.context_type == WorkContextType.TSO
    ).first()

    if not target_mem:
        target_mem = models.WorkContextMembership(
            user_id=user_id,
            context_type=WorkContextType.TSO,
            is_active=True
        )
        db.add(target_mem)
    else:
        target_mem.is_active = True

    target_user.role = UserRole.TSO
    db.commit()
    db.refresh(target_mem)
    return target_mem


def create_work_context_membership(db: Session, data: schemas.WorkContextMembershipCreate) -> models.WorkContextMembership:
    """Create a new work context membership, respecting single-active-TSO constraint."""
    if data.context_type == WorkContextType.TSO and data.is_active:
        return set_active_tso(db, data.user_id)

    mem = models.WorkContextMembership(
        user_id=data.user_id,
        context_type=data.context_type,
        department_id=data.department_id,
        is_active=data.is_active
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def deactivate_work_context_membership(db: Session, membership_id: int) -> Optional[models.WorkContextMembership]:
    """Deactivate a work context membership."""
    mem = get_context_membership(db, membership_id)
    if mem:
        mem.is_active = False
        db.commit()
        db.refresh(mem)
    return mem


# =========================================================
# CANONICAL BRANCH OPERATIONS (DocumentDepartmentRouting)
# =========================================================

def get_document_branches(db: Session, document_id: int) -> List[models.DocumentDepartmentRouting]:
    """Retrieve all canonical branches for a document."""
    return (
        db.query(models.DocumentDepartmentRouting)
        .filter(models.DocumentDepartmentRouting.document_id == document_id)
        .order_by(models.DocumentDepartmentRouting.routed_at.asc())
        .all()
    )


def create_canonical_branches(
    db: Session,
    document_id: int,
    branches: List[schemas.BranchCreate],
    current_user: models.User,
    context_id: Optional[int] = None,
    expected_version: Optional[int] = None
) -> List[models.DocumentDepartmentRouting]:
    """
    DS routes a document to one or more canonical branches:
    - DEPARTMENT_HOD: department required, HOD validation does not apply, target HOD context.
    - DIRECT_EMPLOYEE: target employee required, requires_hod_validation toggleable.
    - TSO: exactly one TSO target in system, no HOD step/validation, department not treated as HOD dept.
    Prevents duplicate active branches for the same logical target.
    """
    doc = get_document(db, document_id)
    if not doc or not check_concurrency(doc, expected_version):
        raise ValueError("Document not found or optimistic concurrency conflict.")

    if not branches:
        raise ValueError("At least one branch definition is required.")

    created_branches = []
    for b in branches:
        if b.branch_type == BranchType.DEPARTMENT_HOD:
            if not b.department_id:
                raise ValueError("Department ID is required for DEPARTMENT_HOD branch.")
            existing = db.query(models.DocumentDepartmentRouting).filter(
                models.DocumentDepartmentRouting.document_id == document_id,
                models.DocumentDepartmentRouting.department_id == b.department_id,
                models.DocumentDepartmentRouting.branch_type == BranchType.DEPARTMENT_HOD,
                models.DocumentDepartmentRouting.is_active == True
            ).first()
            if existing:
                raise ValueError(f"An active DEPARTMENT_HOD branch already exists for department ID {b.department_id}.")

            dept = db.query(models.Department).filter(models.Department.id == b.department_id, models.Department.is_active == True).first()
            if not dept:
                raise ValueError(f"Active department {b.department_id} not found.")
            has_hod = db.query(models.User).filter(models.User.department_id == b.department_id, models.User.role == UserRole.HOD, models.User.is_active == True).first()
            if not has_hod:
                raise ValueError(f"No active HOD is configured for department {b.department_id}.")
            dept_name = dept.name

            branch = models.DocumentDepartmentRouting(
                document_id=document_id,
                branch_type=BranchType.DEPARTMENT_HOD,
                department_id=b.department_id,
                routed_by_user_id=current_user.id,
                routed_by_context_membership_id=context_id,
                requires_hod_validation=False,
                status=DocumentStatus.UNDER_HOD_PROCESSING,
                instructions=b.instructions,
                is_active=True,
                routed_at=datetime.now()
            )
            db.add(branch)
            db.flush()
            created_branches.append(branch)

            # Route ledger entry
            db_route = models.DocumentRoute(
                document_id=document_id,
                from_user_id=current_user.id,
                to_department_id=b.department_id,
                route_type=RouteType.POST_REVIEW_TO_HOD,
                remarks=b.instructions or f"Routed to {dept_name} HOD",
                created_at=datetime.now()
            )
            db.add(db_route)

            # Notify HODs
            dept_hods = db.query(models.User).filter(
                models.User.department_id == b.department_id,
                models.User.role == UserRole.HOD,
                models.User.is_active == True
            ).all()
            for hod in dept_hods:
                _create_notification(
                    db=db,
                    user_id=hod.id,
                    document_id=document_id,
                    title=f"Branch Routed to Department: {doc.reference_no}",
                    message=f"Document '{doc.title}' has been routed to your department for processing."
                )

        elif b.branch_type == BranchType.DIRECT_EMPLOYEE:
            if not b.target_user_id:
                raise ValueError("Target user ID is required for DIRECT_EMPLOYEE branch.")
            existing = db.query(models.DocumentDepartmentRouting).filter(
                models.DocumentDepartmentRouting.document_id == document_id,
                models.DocumentDepartmentRouting.target_user_id == b.target_user_id,
                models.DocumentDepartmentRouting.branch_type == BranchType.DIRECT_EMPLOYEE,
                models.DocumentDepartmentRouting.is_active == True
            ).first()
            if existing:
                raise ValueError(f"An active DIRECT_EMPLOYEE branch already exists for user ID {b.target_user_id}.")

            target_emp = db.query(models.User).filter(
                models.User.id == b.target_user_id,
                models.User.is_active == True,
            ).first()
            if not target_emp:
                raise ValueError("Target staff member must be active.")

            employee_context = _get_active_employee_context(db, target_emp.id, target_emp.department_id)
            if not employee_context:
                raise ValueError("Target staff member must have an active EMPLOYEE work context.")

            branch = models.DocumentDepartmentRouting(
                document_id=document_id,
                branch_type=BranchType.DIRECT_EMPLOYEE,
                department_id=target_emp.department_id,
                target_user_id=b.target_user_id,
                routed_by_user_id=current_user.id,
                routed_by_context_membership_id=context_id,
                requires_hod_validation=bool(b.requires_hod_validation),
                status=DocumentStatus.ASSIGNED_FOR_EXECUTION,
                instructions=b.instructions,
                is_active=True,
                routed_at=datetime.now()
            )
            db.add(branch)
            db.flush()
            created_branches.append(branch)

            # Create initial WorkAssignment for the direct employee.
            # Store the employee's canonical EMPLOYEE context so context-aware
            # inbox/authorization can distinguish this workstream correctly.
            assign_entry = models.WorkAssignment(
                document_id=document_id,
                routing_id=branch.id,
                assigned_by_user_id=current_user.id,
                assigned_to_user_id=b.target_user_id,
                assigned_to_context_membership_id=employee_context.id if employee_context else None,
                requires_hod_validation=bool(b.requires_hod_validation),
                instructions=b.instructions,
                is_active=True,
                assigned_at=datetime.now()
            )
            db.add(assign_entry)

            # Route ledger entry
            db_route = models.DocumentRoute(
                document_id=document_id,
                from_user_id=current_user.id,
                to_user_id=b.target_user_id,
                route_type=RouteType.POST_REVIEW_TO_EMPLOYEE,
                remarks=b.instructions or f"Direct staff delegation to {target_emp.full_name}",
                created_at=datetime.now()
            )
            db.add(db_route)

            _create_notification(
                db=db,
                user_id=b.target_user_id,
                document_id=document_id,
                title=f"Direct Task Assigned: {doc.reference_no}",
                message=f"Document '{doc.title}' has been directly routed to you by DS."
            )

        elif b.branch_type == BranchType.TSO:
            existing = db.query(models.DocumentDepartmentRouting).filter(
                models.DocumentDepartmentRouting.document_id == document_id,
                models.DocumentDepartmentRouting.branch_type == BranchType.TSO,
                models.DocumentDepartmentRouting.is_active == True
            ).first()
            if existing:
                raise ValueError("An active TSO branch already exists for this document.")

            tso_membership = get_single_active_tso(db)
            if not tso_membership:
                raise ValueError("No active TSO found in the system. Changing/activating TSO is required.")

            tso_user_id = tso_membership.user_id
            tso_user = db.query(models.User).filter(
                models.User.id == tso_user_id,
                models.User.is_active == True,
            ).first()
            if not tso_user:
                raise ValueError("The active TSO context points to an inactive or missing user.")

            branch = models.DocumentDepartmentRouting(
                document_id=document_id,
                branch_type=BranchType.TSO,
                target_user_id=tso_user_id,
                target_context_membership_id=tso_membership.id,
                routed_by_user_id=current_user.id,
                routed_by_context_membership_id=context_id,
                requires_hod_validation=False,
                status=DocumentStatus.ASSIGNED_FOR_EXECUTION,
                instructions=b.instructions,
                is_active=True,
                routed_at=datetime.now()
            )
            db.add(branch)
            db.flush()
            created_branches.append(branch)

            # Create initial WorkAssignment for TSO
            assign_entry = models.WorkAssignment(
                document_id=document_id,
                routing_id=branch.id,
                assigned_by_user_id=current_user.id,
                assigned_to_user_id=tso_user_id,
                assigned_to_context_membership_id=tso_membership.id,
                requires_hod_validation=False,
                instructions=b.instructions,
                is_active=True,
                assigned_at=datetime.now()
            )
            db.add(assign_entry)

            # Route ledger entry
            db_route = models.DocumentRoute(
                document_id=document_id,
                from_user_id=current_user.id,
                to_user_id=tso_user_id,
                route_type=RouteType.POST_REVIEW_TO_EMPLOYEE,
                remarks=b.instructions or "Routed to TSO",
                created_at=datetime.now()
            )
            db.add(db_route)

            _create_notification(
                db=db,
                user_id=tso_user_id,
                document_id=document_id,
                title=f"TSO Task Assigned: {doc.reference_no}",
                message=f"Document '{doc.title}' has been routed to TSO."
            )

    # The branches are authoritative. There is intentionally no single operational owner.
    _refresh_document_overall_state(db, doc)
    doc.version += 1

    _add_workflow_history(
        db=db, document_id=document_id, user_id=current_user.id,
        action="CANONICAL_MULTI_BRANCH_ROUTED",
        from_role=current_user.role.value, to_role="MULTI_BRANCH",
        details=f"DS created {len(created_branches)} canonical branch(es): {[b.branch_type.value for b in created_branches]}"
    )

    db.commit()
    db.refresh(doc)
    return created_branches


# =========================================================
# CANONICAL WORK ASSIGNMENT (Operational Responsibility)
# =========================================================

def assign_branch_employee(
    db: Session,
    document_id: int,
    routing_id: int,
    assign_req: schemas.AssignmentRequest,
    current_user: models.User,
    context_id: Optional[int] = None
) -> models.WorkAssignment:
    """Assign one canonical branch. Other branches and document owner are untouched."""
    doc = get_document(db, document_id)
    # Do NOT lock branch assignment on Document.version. Multiple active
    # branches are intentionally allowed to progress independently.
    if not doc:
        raise ValueError("Document not found.")

    branch = db.query(models.DocumentDepartmentRouting).filter(
        models.DocumentDepartmentRouting.id == routing_id,
        models.DocumentDepartmentRouting.document_id == document_id,
        models.DocumentDepartmentRouting.is_active == True,
    ).first()
    if not branch:
        raise ValueError(f"Active branch with ID {routing_id} not found on document {document_id}.")

    if current_user.role == UserRole.HOD:
        selected_context = _resolve_context_membership(db, current_user, context_id)
        selected_department_id = (
            selected_context.department_id
            if selected_context and selected_context.context_type == WorkContextType.HOD
            else current_user.department_id
        )
        if branch.branch_type != BranchType.DEPARTMENT_HOD:
            raise ValueError("HOD may assign staff only on a Department/HOD branch.")
        if branch.department_id != selected_department_id:
            raise ValueError("HOD may assign only within the selected HOD context's department branch.")

    target = db.query(models.User).filter(
        models.User.id == assign_req.assigned_to_user_id,
        models.User.is_active == True,
    ).first()
    if not target:
        raise ValueError(f"Assignee user {assign_req.assigned_to_user_id} not found or inactive.")

    target_context_id = branch.target_context_membership_id
    if branch.branch_type == BranchType.DEPARTMENT_HOD:
        if target.department_id != branch.department_id:
            raise ValueError("A Department/HOD branch can only be assigned to an employee in that department.")
        target_context = _get_active_employee_context(db, target.id, branch.department_id)
        if not target_context:
            raise ValueError("The selected assignee does not have an active EMPLOYEE context for this department.")
        target_context_id = target_context.id
    elif branch.branch_type == BranchType.DIRECT_EMPLOYEE:
        if target.id != branch.target_user_id:
            raise ValueError("The direct-employee branch can only be assigned to its routed employee.")
        target_context = _get_active_employee_context(db, target.id, target.department_id)
        if not target_context:
            raise ValueError("The routed employee does not have an active EMPLOYEE work context.")
        target_context_id = target_context.id
    elif branch.branch_type == BranchType.TSO:
        if target.id != branch.target_user_id:
            raise ValueError("A TSO branch can only be assigned to the routed TSO user.")
        tso_context = db.query(models.WorkContextMembership).filter(
            models.WorkContextMembership.id == branch.target_context_membership_id,
            models.WorkContextMembership.user_id == target.id,
            models.WorkContextMembership.context_type == WorkContextType.TSO,
            models.WorkContextMembership.is_active == True,
        ).first()
        if not tso_context:
            raise ValueError("The routed TSO does not have an active TSO work context.")
        target_context_id = tso_context.id

    old = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.routing_id == routing_id,
        models.WorkAssignment.is_active == True,
    ).first()
    now = datetime.now()
    req_val = branch.branch_type == BranchType.DEPARTMENT_HOD or (
        branch.branch_type == BranchType.DIRECT_EMPLOYEE and branch.requires_hod_validation
    )

    new_assign = models.WorkAssignment(
        document_id=document_id, routing_id=routing_id,
        assigned_by_user_id=current_user.id, assigned_to_user_id=target.id,
        assigned_to_context_membership_id=target_context_id,
        requires_hod_validation=bool(req_val),
        instructions=assign_req.instructions or branch.instructions,
        change_reason=assign_req.change_reason, team_name=None, is_team=False, is_active=True, assigned_at=now,
    )
    db.add(new_assign)
    db.flush()

    if old:
        old.is_active = False
        old.completed_at = now
        old.superseded_by_id = new_assign.id

    branch.status = DocumentStatus.ASSIGNED_FOR_EXECUTION
    branch.version += 1

    _refresh_document_overall_state(db, doc)
    doc.version += 1

    event = _add_workflow_history(
        db=db, document_id=document_id, user_id=current_user.id,
        action="BRANCH_EMPLOYEE_REASSIGNED" if old else "BRANCH_EMPLOYEE_ASSIGNED",
        from_role=current_user.role.value, to_role=target.role.value,
        details=f"Assigned {target.full_name} to routing branch {branch.id} ({branch.branch_type.value}); work_assignment_id={new_assign.id}"
    )
    _create_notification(
        db=db, user_id=target.id, document_id=document_id, workflow_event_id=event.id,
        title=f"Task Assigned: {doc.reference_no}",
        message=f"You have been assigned workstream '{branch.branch_type.value}' on '{doc.title}'."
    )
    db.commit()
    db.refresh(new_assign)
    return new_assign

def submit_director_review(
    db: Session,
    document_id: int,
    review_req: schemas.DirectorReviewRequest,
    current_user: models.User,
    context_id: Optional[int] = None
) -> models.DirectorReview:
    """
    Director review recording machine-readable decisions (CONTINUE or CLOSE).
    - CONTINUE: Continue active branches; completed branches stay completed.
    - CLOSE: Instructs closure; does NOT close the document itself. Document returns to DS.
    """
    doc = get_document(db, document_id)
    if not doc or not check_concurrency(doc, review_req.expected_version):
        raise ValueError("Document not found or optimistic concurrency conflict.")

    review = models.DirectorReview(
        document_id=document_id,
        director_user_id=current_user.id,
        director_context_membership_id=context_id,
        decision=review_req.decision,
        remark_text=review_req.remark_text,
        document_version=doc.version,
        created_at=datetime.now()
    )
    db.add(review)

    if review_req.remark_text:
        remark_entry = models.DocumentRemark(
            document_id=document_id,
            author_user_id=current_user.id,
            role=UserRole.DIRECTOR,
            remark_text=f"[{review_req.decision.value}] {review_req.remark_text}",
            remark_type=RemarkType.DIRECTOR,
            provenance="DIRECTOR_REVIEW",
            context_membership_id=context_id,
            created_at=datetime.now()
        )
        db.add(remark_entry)
        db.flush()

        active_branches = db.query(models.DocumentDepartmentRouting).filter(
            models.DocumentDepartmentRouting.document_id == document_id,
            models.DocumentDepartmentRouting.is_active == True
        ).all()
        for br in active_branches:
            target = models.DocumentRemarkTarget(
                remark_id=remark_entry.id,
                routing_id=br.id,
                created_at=datetime.now()
            )
            db.add(target)

        doc.status = DocumentStatus.DIRECTOR_REVIEW_COMPLETED
    if review_req.remark_text:
        doc.director_remark = f"[{review_req.decision.value}] {review_req.remark_text}"
    doc.updated_at = datetime.now()
    doc.version += 1

    decision_detail = f'Director issued instruction: {review_req.decision.value}. Remark: "{review_req.remark_text or ""}"'
    if review_req.decision == DirectorDecision.CLOSE:
        decision_detail += " (Document pending final closure by Director Secretary)"

    _add_workflow_history(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
        action=f"DIRECTOR_DECISION_{review_req.decision.value}",
        from_role="DIRECTOR",
        to_role="DS",
        details=decision_detail
    )

    ds_user = db.query(models.User).filter(models.User.role == UserRole.DS).first()
    ds_user_id = ds_user.id if ds_user else current_user.id

    db_route = models.DocumentRoute(
        document_id=document_id,
        from_user_id=current_user.id,
        to_user_id=ds_user_id,
        route_type=RouteType.RETURN_TO_DS,
        remarks=doc.director_remark,
        created_at=datetime.now()
    )
    db.add(db_route)

    _create_notification(
        db=db,
        user_id=ds_user_id,
        document_id=document_id,
        title=f"Director Review Decision: {review_req.decision.value} ({doc.reference_no})",
        message=f"Director instructed {review_req.decision.value} for document '{doc.title}'."
    )

    db.commit()
    db.refresh(review)
    return review
