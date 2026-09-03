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
    ProgressValidationStatus, AssignmentStatus
)


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
    return db.query(models.IncomingMessage).order_by(models.IncomingMessage.created_at.desc()).all()


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
        target_department_id=None,
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
        current_stage=WorkflowStage.DS,
        current_owner_id=created_by,
        target_department_id=doc.target_department_id,
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
    if doc.suggested_department_id or doc.suggested_employee_id or doc.target_department_id:
        generate_routing_suggestion(
            db,
            db_doc.doc_id,
            include_director_remark=bool(doc.director_remark),
            preferred_dept_id=doc.suggested_department_id or doc.target_department_id,
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


def get_documents(db: Session) -> List[models.Document]:
    return db.query(models.Document).order_by(models.Document.created_at.desc()).all()


# =========================================================
# STRICT ROLE & DEPARTMENT SCOPING / INBOX
# =========================================================

def get_inbox(db: Session, user: models.User) -> List[models.Document]:
    """
    Hard-enforced backend scoping:
    - DS: All documents in DS intake stage
    - DIRECTOR: Only documents routed to Director (current_stage = DIRECTOR)
    - HOD: Documents routed to HOD's department (target_department_id OR doc_assignments matching user.department_id)
    - EMPLOYEE: Documents actively assigned to user via WorkAssignment or DocumentAssignment
    """
    if user.role == UserRole.DS:
        return (
            db.query(models.Document)
            .filter(
                models.Document.current_stage == WorkflowStage.DS,
                models.Document.status == DocumentStatus.RECEIVED
            )
            .order_by(models.Document.created_at.desc())
            .all()
        )

    elif user.role == UserRole.DIRECTOR:
        return (
            db.query(models.Document)
            .filter(
                models.Document.current_stage == WorkflowStage.DIRECTOR,
                or_(
                    models.Document.current_owner_id == user.id,
                    models.Document.current_owner_id == None
                )
            )
            .order_by(models.Document.updated_at.desc())
            .all()
        )

    elif user.role == UserRole.HOD:
        if not user.department_id:
            return []
        
        # Subquery for documents assigned to this department in multi-assignment table
        multi_dept_doc_ids = (
            db.query(models.DocumentAssignment.document_id)
            .filter(models.DocumentAssignment.department_id == user.department_id)
            .all()
        )
        multi_ids = [r[0] for r in multi_dept_doc_ids]

        return (
            db.query(models.Document)
            .filter(
                or_(
                    and_(
                        models.Document.current_stage == WorkflowStage.HOD,
                        models.Document.target_department_id == user.department_id
                    ),
                    models.Document.doc_id.in_(multi_ids)
                )
            )
            .order_by(models.Document.updated_at.desc())
            .all()
        )

    elif user.role == UserRole.EMPLOYEE:
        assigned_doc_ids = (
            db.query(models.WorkAssignment.document_id)
            .filter(
                models.WorkAssignment.assigned_to_user_id == user.id,
                models.WorkAssignment.is_active == True
            )
            .all()
        )
        multi_assign_ids = (
            db.query(models.DocumentAssignment.document_id)
            .filter(models.DocumentAssignment.assigned_employee_id == user.id)
            .all()
        )
        combined_ids = list(set([r[0] for r in assigned_doc_ids] + [r[0] for r in multi_assign_ids]))

        return (
            db.query(models.Document)
            .filter(
                or_(
                    models.Document.doc_id.in_(combined_ids),
                    and_(
                        models.Document.current_owner_id == user.id,
                        models.Document.current_stage == WorkflowStage.EMPLOYEE
                    )
                )
            )
            .order_by(models.Document.updated_at.desc())
            .all()
        )

    return []


def is_document_accessible(db: Session, doc: models.Document, user: models.User) -> bool:
    """Check if the user is authorized to view this document and its attachments/history."""
    if user.role in (UserRole.DS, UserRole.DIRECTOR):
        return True
    elif user.role == UserRole.HOD:
        if user.department_id is not None and doc.target_department_id == user.department_id:
            return True
        has_multi = db.query(models.DocumentAssignment).filter(
            models.DocumentAssignment.document_id == doc.doc_id,
            models.DocumentAssignment.department_id == user.department_id
        ).first()
        return has_multi is not None
    elif user.role == UserRole.EMPLOYEE:
        has_assignment = db.query(models.WorkAssignment).filter(
            models.WorkAssignment.document_id == doc.doc_id,
            models.WorkAssignment.assigned_to_user_id == user.id
        ).first()
        has_multi = db.query(models.DocumentAssignment).filter(
            models.DocumentAssignment.document_id == doc.doc_id,
            models.DocumentAssignment.assigned_employee_id == user.id
        ).first()
        return (doc.current_owner_id == user.id or has_assignment is not None or has_multi is not None)
    return False


def get_accessible_documents_for_user(db: Session, user: models.User) -> List[models.Document]:
    """Returns all documents accessible to the given user based on their role and department."""
    if user.role in (UserRole.DS, UserRole.DIRECTOR):
        return db.query(models.Document).order_by(models.Document.created_at.desc()).all()
    elif user.role == UserRole.HOD:
        if not user.department_id:
            return []
        multi_dept_doc_ids = [
            r[0] for r in db.query(models.DocumentAssignment.document_id)
            .filter(models.DocumentAssignment.department_id == user.department_id).all()
        ]
        return (
            db.query(models.Document)
            .filter(
                or_(
                    models.Document.target_department_id == user.department_id,
                    models.Document.doc_id.in_(multi_dept_doc_ids)
                )
            )
            .order_by(models.Document.updated_at.desc())
            .all()
        )
    elif user.role == UserRole.EMPLOYEE:
        return get_inbox(db, user)
    return []


# =========================================================
# DOCUMENT WORKFLOW TRANSITIONS
# =========================================================

def route_document(db: Session, doc_id: int, route_req: schemas.RouteRequest, current_user: models.User) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, route_req.expected_version):
        return None

    if route_req.route_type == RouteType.INITIAL_DIRECTOR_REVIEW:
        new_stage = WorkflowStage.DIRECTOR
        new_status = DocumentStatus.UNDER_DIRECTOR_REVIEW
        new_owner = route_req.to_user_id

    elif route_req.route_type == RouteType.POST_REVIEW_TO_HOD:
        new_stage = WorkflowStage.HOD
        new_status = DocumentStatus.UNDER_HOD_PROCESSING
        new_owner = None
        if route_req.to_department_id:
            doc.target_department_id = route_req.to_department_id

    elif route_req.route_type == RouteType.POST_REVIEW_TO_EMPLOYEE:
        new_stage = WorkflowStage.EMPLOYEE
        new_status = DocumentStatus.ASSIGNED_FOR_EXECUTION
        new_owner = route_req.to_user_id
        if route_req.to_user_id:
            target_user = db.query(models.User).filter(models.User.id == route_req.to_user_id).first()
            if target_user and target_user.department_id:
                doc.target_department_id = target_user.department_id

            db.query(models.WorkAssignment).filter(
                models.WorkAssignment.document_id == doc_id,
                models.WorkAssignment.is_active == True
            ).update({"is_active": False})

            assign_entry = models.WorkAssignment(
                document_id=doc_id,
                assigned_by_user_id=current_user.id,
                assigned_to_user_id=route_req.to_user_id,
                instructions=route_req.remarks,
                is_active=True
            )
            db.add(assign_entry)

    elif route_req.route_type == RouteType.FOLLOW_UP_TO_DIRECTOR:
        new_stage = WorkflowStage.DIRECTOR
        new_status = DocumentStatus.UNDER_DIRECTOR_REVIEW
        new_owner = route_req.to_user_id
    else:
        return None

    doc.current_stage = new_stage
    doc.status = new_status
    doc.current_owner_id = new_owner
    doc.updated_at = datetime.now()
    doc.version += 1

    # Record Route entry
    db_route = models.DocumentRoute(
        document_id=doc_id,
        from_user_id=current_user.id,
        to_user_id=route_req.to_user_id,
        to_department_id=route_req.to_department_id,
        route_type=route_req.route_type,
        remarks=route_req.remarks,
    )
    db.add(db_route)
    db.commit()
    db.refresh(doc)

    # Workflow history
    if route_req.route_type == RouteType.INITIAL_DIRECTOR_REVIEW:
        route_detail = route_req.remarks or "Forwarded for Executive Review"
    elif route_req.route_type == RouteType.POST_REVIEW_TO_HOD:
        route_detail = route_req.remarks or f"Destination: {doc.target_department_name or 'Department'} (For departmental processing)"
    elif route_req.route_type == RouteType.POST_REVIEW_TO_EMPLOYEE:
        route_detail = route_req.remarks or f"Direct Staff Delegation: {doc.assigned_employee_name or 'Staff'}"
    elif route_req.route_type == RouteType.FOLLOW_UP_TO_DIRECTOR:
        route_detail = route_req.remarks or "Progress follow-up forwarded to Director for Executive Review"
    else:
        route_detail = route_req.remarks or "Document routed"

    event = _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action=f"ROUTED_{route_req.route_type.value}",
        from_role=current_user.role.value,
        to_role=new_stage.value,
        details=route_detail
    )

    # Send Notification to recipient
    if route_req.to_user_id:
        _create_notification(
            db=db,
            user_id=route_req.to_user_id,
            document_id=doc_id,
            workflow_event_id=event.id,
            title=f"Document routed: {doc.reference_no}",
            message=f"Document '{doc.title}' routed to you by DS."
        )
    elif route_req.to_department_id:
        # Notify active HODs of that department
        dept_hods = db.query(models.User).filter(
            models.User.department_id == route_req.to_department_id,
            models.User.role == UserRole.HOD,
            models.User.is_active == True
        ).all()
        for hod in dept_hods:
            _create_notification(
                db=db,
                user_id=hod.id,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"New Department Document: {doc.reference_no}",
                message=f"Document '{doc.title}' routed to your department."
            )

    return doc


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

    doc.current_stage = WorkflowStage.DS
    doc.status = DocumentStatus.DIRECTOR_REVIEW_COMPLETED
    doc.current_owner_id = ds_user_id
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


def assign_employee(db: Session, doc_id: int, assign_req: schemas.AssignmentRequest,
                    current_user: models.User) -> Optional[models.WorkAssignment]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, assign_req.expected_version):
        return None

    # Deactivate any previous active assignment
    (
        db.query(models.WorkAssignment)
        .filter(models.WorkAssignment.document_id == doc_id, models.WorkAssignment.is_active == True)
        .update({"is_active": False})
    )

    assignment = models.WorkAssignment(
        document_id=doc_id,
        assigned_by_user_id=current_user.id,
        assigned_to_user_id=assign_req.assigned_to_user_id,
        requires_hod_validation=assign_req.requires_hod_validation,
        instructions=assign_req.instructions,
        is_active=True,
    )
    db.add(assignment)

    # Also record in document_assignments if not already present
    doc_assign = models.DocumentAssignment(
        document_id=doc_id,
        department_id=current_user.department_id,
        assigned_employee_id=assign_req.assigned_to_user_id,
        assigned_by_user_id=current_user.id,
        requires_hod_validation=assign_req.requires_hod_validation,
        assignment_status=AssignmentStatus.IN_PROGRESS,
        instructions=assign_req.instructions,
        created_at=datetime.now()
    )
    db.add(doc_assign)

    doc.current_stage = WorkflowStage.EMPLOYEE
    doc.status = DocumentStatus.ASSIGNED_FOR_EXECUTION
    doc.current_owner_id = assign_req.assigned_to_user_id
    doc.updated_at = datetime.now()
    doc.version += 1

    db.commit()
    db.refresh(assignment)

    assignee_name = assignment.assigned_to.full_name if (assignment.assigned_to and assignment.assigned_to.full_name) else (doc.assigned_employee_name or "Staff")
    val_note = " [HOD Validation Required]" if assign_req.requires_hod_validation else " [Direct to DS]"
    assign_detail = f"Delegated to {assignee_name}: {assign_req.instructions or 'Standard departmental execution'}{val_note}"

    event = _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="EMPLOYEE_ASSIGNED",
        from_role="HOD",
        to_role="EMPLOYEE",
        details=assign_detail
    )

    _create_notification(
        db=db,
        user_id=assign_req.assigned_to_user_id,
        document_id=doc_id,
        workflow_event_id=event.id,
        title=f"Task assigned: {doc.reference_no}",
        message=f"You have been assigned to document '{doc.title}' by HOD."
    )

    return assignment


def create_progress_update(db: Session, doc_id: int, prog: schemas.ProgressCreate,
                           current_user: models.User) -> Optional[models.ProgressUpdate]:
    doc = get_document(db, doc_id)
    if not doc:
        return None

    # Check if this employee's assignment requires HOD validation
    active_assign = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.document_id == doc_id,
        models.WorkAssignment.assigned_to_user_id == current_user.id,
        models.WorkAssignment.is_active == True
    ).first()

    multi_assign = db.query(models.DocumentAssignment).filter(
        models.DocumentAssignment.document_id == doc_id,
        models.DocumentAssignment.assigned_employee_id == current_user.id
    ).first()

    requires_hod = False
    if active_assign and active_assign.requires_hod_validation:
        requires_hod = True
    elif multi_assign and multi_assign.requires_hod_validation:
        requires_hod = True

    val_status = ProgressValidationStatus.PENDING_HOD_REVIEW if requires_hod else ProgressValidationStatus.DIRECT_TO_DS

    db_progress = models.ProgressUpdate(
        document_id=doc_id,
        submitted_by_user_id=current_user.id,
        description=prog.description,
        hod_validation_required=requires_hod,
        hod_validation_status=val_status
    )
    db.add(db_progress)

    # If direct to DS, advance document status to PROGRESS_UPDATED;
    # if pending HOD, keep IN_PROGRESS or PROGRESS_UPDATED so HOD sees it in their queue
    doc.status = DocumentStatus.PROGRESS_UPDATED
    doc.updated_at = datetime.now()
    doc.version += 1

    db.commit()
    db.refresh(db_progress)

    if requires_hod:
        event = _add_workflow_history(
            db=db,
            document_id=doc_id,
            user_id=current_user.id,
            action="PROGRESS_SUBMITTED_FOR_HOD",
            from_role="EMPLOYEE",
            to_role="HOD",
            details=f'Progress update submitted for HOD validation: "{prog.description}"'
        )

        # Notify HOD(s)
        dept_id = current_user.department_id or doc.target_department_id
        if dept_id:
            hods = db.query(models.User).filter(
                models.User.department_id == dept_id,
                models.User.role == UserRole.HOD,
                models.User.is_active == True
            ).all()
            for hod in hods:
                _create_notification(
                    db=db,
                    user_id=hod.id,
                    document_id=doc_id,
                    workflow_event_id=event.id,
                    title=f"Progress awaiting HOD review: {doc.reference_no}",
                    message=f"{current_user.full_name} submitted progress on '{doc.title}' requiring your validation."
                )
    else:
        event = _add_workflow_history(
            db=db,
            document_id=doc_id,
            user_id=current_user.id,
            action="PROGRESS_UPDATED",
            from_role="EMPLOYEE",
            to_role="DS",
            details=f'Progress Report (Direct to DS): "{prog.description}"'
        )

        # Notify DS creator
        if doc.created_by:
            _create_notification(
                db=db,
                user_id=doc.created_by,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"Progress update on {doc.reference_no}",
                message=f"{current_user.full_name} updated progress on '{doc.title}'."
            )

    return db_progress


def hod_validate_progress_update(
    db: Session,
    doc_id: int,
    progress_id: int,
    action: str,
    note: Optional[str],
    current_user: models.User
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

    action_lower = action.lower().strip()
    if action_lower == "approve":
        progress.hod_validation_status = ProgressValidationStatus.HOD_APPROVED
        progress.hod_review_note = note
        progress.hod_reviewed_by_user_id = current_user.id
        progress.hod_reviewed_at = datetime.now()

        doc.status = DocumentStatus.PROGRESS_UPDATED
        doc.updated_at = datetime.now()
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


def create_document_assignments(
    db: Session,
    doc_id: int,
    assignments_data: List[schemas.DocumentAssignmentCreate],
    by_user: models.User
) -> List[models.DocumentAssignment]:
    doc = get_document(db, doc_id)
    if not doc:
        return []

    created_assignments = []
    first_dept_id = None

    for item in assignments_data:
        assign = models.DocumentAssignment(
            document_id=doc_id,
            department_id=item.department_id,
            assigned_employee_id=item.assigned_employee_id,
            assigned_by_user_id=by_user.id,
            requires_hod_validation=item.requires_hod_validation,
            assignment_status=AssignmentStatus.PENDING_EMPLOYEE if not item.assigned_employee_id else AssignmentStatus.IN_PROGRESS,
            instructions=item.instructions,
            created_at=datetime.now()
        )
        db.add(assign)
        created_assignments.append(assign)
        if item.department_id and not first_dept_id:
            first_dept_id = item.department_id

    # Update document primary department if not set
    if first_dept_id and not doc.target_department_id:
        doc.target_department_id = first_dept_id

    doc.current_stage = WorkflowStage.HOD if any(a.department_id and not a.assigned_employee_id for a in assignments_data) else WorkflowStage.EMPLOYEE
    doc.status = DocumentStatus.UNDER_HOD_PROCESSING if doc.current_stage == WorkflowStage.HOD else DocumentStatus.ASSIGNED_FOR_EXECUTION
    doc.updated_at = datetime.now()
    doc.version += 1

    db.commit()
    for a in created_assignments:
        db.refresh(a)

    summary = f"Multi-department/employee routing configured ({len(created_assignments)} assignments)"
    event = _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=by_user.id,
        action="MULTI_ASSIGNMENT_CREATED",
        from_role="DS",
        to_role="HOD",
        details=summary
    )

    for assign in created_assignments:
        if assign.assigned_employee_id:
            _create_notification(
                db=db,
                user_id=assign.assigned_employee_id,
                document_id=doc_id,
                workflow_event_id=event.id,
                title=f"New Assignment: {doc.reference_no}",
                message=f"You have been assigned to document '{doc.title}'."
            )
        elif assign.department_id:
            dept_hods = db.query(models.User).filter(
                models.User.department_id == assign.department_id,
                models.User.role == UserRole.HOD,
                models.User.is_active == True
            ).all()
            for hod in dept_hods:
                _create_notification(
                    db=db,
                    user_id=hod.id,
                    document_id=doc_id,
                    workflow_event_id=event.id,
                    title=f"New Department Task: {doc.reference_no}",
                    message=f"Document '{doc.title}' assigned to your department."
                )

    return created_assignments


def get_document_assignments(db: Session, doc_id: int) -> List[models.DocumentAssignment]:
    return (
        db.query(models.DocumentAssignment)
        .filter(models.DocumentAssignment.document_id == doc_id)
        .order_by(models.DocumentAssignment.created_at)
        .all()
    )


def update_document_assignment(
    db: Session,
    assignment_id: int,
    assigned_employee_id: Optional[int],
    instructions: Optional[str],
    requires_hod_validation: Optional[bool],
    user: models.User
) -> Optional[models.DocumentAssignment]:
    assign = db.query(models.DocumentAssignment).filter(
        models.DocumentAssignment.id == assignment_id
    ).first()
    if not assign:
        return None

    if assigned_employee_id is not None:
        assign.assigned_employee_id = assigned_employee_id
        assign.assignment_status = AssignmentStatus.IN_PROGRESS
    if instructions is not None:
        assign.instructions = instructions
    if requires_hod_validation is not None:
        assign.requires_hod_validation = requires_hod_validation

    db.commit()
    db.refresh(assign)

    if assign.assigned_employee_id:
        doc = get_document(db, assign.document_id)
        if doc:
            event = _add_workflow_history(
                db=db,
                document_id=doc.doc_id,
                user_id=user.id,
                action="EMPLOYEE_ASSIGNED",
                from_role="HOD",
                to_role="EMPLOYEE",
                details=f"Assigned staff {assign.employee_name or 'Staff'}"
            )
            _create_notification(
                db=db,
                user_id=assign.assigned_employee_id,
                document_id=doc.doc_id,
                workflow_event_id=event.id,
                title=f"Task Assigned: {doc.reference_no}",
                message=f"You have been assigned to document '{doc.title}'."
            )

    return assign


def get_progress_updates(db: Session, doc_id: int) -> List[models.ProgressUpdate]:
    return db.query(models.ProgressUpdate).filter(models.ProgressUpdate.document_id == doc_id).order_by(models.ProgressUpdate.created_at).all()


def follow_up_to_director(db: Session, doc_id: int, director_user: models.User,
                          remarks: Optional[str], current_user: models.User,
                          expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.current_stage = WorkflowStage.DIRECTOR
    doc.status = DocumentStatus.PROGRESS_UPDATED
    doc.current_owner_id = director_user.id
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


def close_document(db: Session, doc_id: int, remarks: Optional[str],
                   current_user: models.User, expected_version: Optional[int] = None) -> Optional[models.Document]:
    doc = get_document(db, doc_id)
    if not doc or not check_concurrency(doc, expected_version):
        return None

    doc.status = DocumentStatus.CLOSED
    doc.current_stage = WorkflowStage.CLOSED
    doc.closed_at = datetime.now()
    doc.updated_at = datetime.now()
    doc.version += 1

    db.commit()
    db.refresh(doc)

    _add_workflow_history(
        db=db,
        document_id=doc_id,
        user_id=current_user.id,
        action="DOCUMENT_CLOSED",
        from_role="DS",
        to_role="CLOSED",
        details=remarks or "Document lifecycle finalized and closed successfully."
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

    # ---- Record real OCR outcome ----
    if not file_processed or not extracted_text.strip():
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
    suggested_dept_id: Optional[int] = preferred_dept_id or doc.target_department_id
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
    """
    Scans documents needing action and generates reminders using recipient escalation:
    1. If active employee assigned -> Remind assigned employee
    2. Elif target department exists -> Remind active HOD of target department
    3. Else -> Remind DS creator
    """
    today = date.today()
    active_docs = db.query(models.Document).filter(
        models.Document.status != DocumentStatus.CLOSED
    ).all()

    created_reminders = []

    for doc in active_docs:
        # Determine reason based on deadline
        reason = ReminderReason.ACTION_REQUIRED
        if doc.deadline:
            if doc.deadline < today:
                reason = ReminderReason.OVERDUE
            elif doc.deadline <= today + timedelta(days=2):
                reason = ReminderReason.DUE_SOON

        # Recipient Resolution:
        recipient_id: Optional[int] = None

        # 1. Check active work assignment for employee
        active_assignment = db.query(models.WorkAssignment).filter(
            models.WorkAssignment.document_id == doc.doc_id,
            models.WorkAssignment.is_active == True
        ).first()

        if active_assignment:
            recipient_id = active_assignment.assigned_to_user_id
        elif doc.target_department_id:
            # 2. Check active HOD of target department
            hod = db.query(models.User).filter(
                models.User.department_id == doc.target_department_id,
                models.User.role == UserRole.HOD,
                models.User.is_active == True
            ).first()
            if hod:
                recipient_id = hod.id
        elif doc.current_owner_id:
            recipient_id = doc.current_owner_id
        else:
            recipient_id = doc.created_by

        if recipient_id:
            dedup_key = f"DOC_{doc.doc_id}_USER_{recipient_id}_{reason.value}_{today.isoformat()}"
            existing = db.query(models.Reminder).filter(models.Reminder.deduplication_key == dedup_key).first()

            if not existing:
                reminder = models.Reminder(
                    document_id=doc.doc_id,
                    recipient_user_id=recipient_id,
                    reason=reason,
                    due_at=datetime.combine(doc.deadline, datetime.min.time()) if doc.deadline else None,
                    sent_at=datetime.now(),
                    is_read=False,
                    deduplication_key=dedup_key
                )
                db.add(reminder)
                created_reminders.append(reminder)

    if created_reminders:
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

    if doc.current_stage in (WorkflowStage.DS, WorkflowStage.DIRECTOR) or not doc.target_department_id:
        return {"status": "error", "message": "Action reminders can only be sent after the document has completed Director review and is officially routed to a department or staff member."}

    # Resolve responsible recipient
    recipient: Optional[models.User] = None
    role_label = "Responsible Staff"

    active_assignment = db.query(models.WorkAssignment).filter(
        models.WorkAssignment.document_id == doc.doc_id,
        models.WorkAssignment.is_active == True
    ).first()

    if active_assignment and active_assignment.assigned_to:
        recipient = active_assignment.assigned_to
        role_label = "Assigned Employee"
    elif doc.target_department_id:
        hod = db.query(models.User).filter(
            models.User.department_id == doc.target_department_id,
            models.User.role == UserRole.HOD,
            models.User.is_active == True
        ).first()
        if hod:
            recipient = hod
            role_label = f"HOD ({doc.target_department_name or 'Department'})"
    elif doc.current_owner_id:
        recipient = db.query(models.User).filter(models.User.id == doc.current_owner_id).first()
        role_label = recipient.role.value if recipient else "Current Owner"
    else:
        recipient = db.query(models.User).filter(models.User.id == doc.created_by).first()
        role_label = "Creator (DS)"

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
            .filter(models.Document.target_department_id == current_user.department_id)
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
                | (models.Document.current_owner_id == current_user.id)
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
    document_id: Optional[int],
    workflow_event_id: Optional[int],
    title: str,
    message: str
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
            .filter(models.Document.created_by == user.id, models.Document.current_stage == WorkflowStage.DIRECTOR)
            .scalar()
        ) or 0

        under_hod = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.current_stage == WorkflowStage.HOD)
            .scalar()
        ) or 0

        in_progress = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.current_stage == WorkflowStage.EMPLOYEE)
            .scalar()
        ) or 0

        closed = (
            db.query(func.count(models.Document.doc_id))
            .filter(models.Document.created_by == user.id, models.Document.current_stage == WorkflowStage.CLOSED)
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
            .filter(models.Document.current_owner_id == user.id, models.Document.current_stage == WorkflowStage.DIRECTOR)
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
            dept_docs = (
                db.query(func.count(models.Document.doc_id))
                .filter(models.Document.target_department_id == user.department_id, models.Document.current_stage == WorkflowStage.HOD)
                .scalar()
            ) or 0

            pending_assignment = (
                db.query(func.count(models.Document.doc_id))
                .filter(models.Document.target_department_id == user.department_id, models.Document.status == DocumentStatus.UNDER_HOD_PROCESSING)
                .scalar()
            ) or 0

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
                department_name=u.get("department"),
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
            existing.department_name = u.get("department") or existing.department_name
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

    print(f"[CDTRS SEED] Successfully verified {len(dept_map)} departments and {len(users_data)} system accounts.", flush=True)


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
        department_name=user_data.get("department_name") or user_data.get("department"),
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
    if "department_name" in user_data:
        user.department_name = user_data["department_name"]
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


def multi_route_document(
    db: Session,
    document_id: int,
    target_department_ids: List[int],
    instructions: Optional[str],
    current_user: models.User
) -> List[models.DocumentDepartmentRouting]:
    """Routes a single document to multiple departments concurrently."""
    doc = db.query(models.Document).filter(models.Document.doc_id == document_id).first()
    if not doc:
        return []

    created_routings = []
    for d_id in target_department_ids:
        dept = db.query(models.Department).filter(models.Department.id == d_id).first()
        if not dept:
            continue

        existing = db.query(models.DocumentDepartmentRouting).filter(
            models.DocumentDepartmentRouting.document_id == document_id,
            models.DocumentDepartmentRouting.department_id == d_id
        ).first()

        if not existing:
            routing = models.DocumentDepartmentRouting(
                document_id=document_id,
                department_id=d_id,
                department_name=dept.name,
                status=DocumentStatus.UNDER_HOD_PROCESSING,
                hod_instructions=instructions,
                routed_at=datetime.now()
            )
            db.add(routing)
            created_routings.append(routing)

    # Update primary document status and stage
    doc.status = DocumentStatus.UNDER_HOD_PROCESSING
    doc.current_stage = WorkflowStage.HOD
    if target_department_ids:
        doc.target_department_id = target_department_ids[0]
    if instructions:
        doc.hod_remark = instructions

    db.commit()
    log_audit_event(
        db,
        user_id=current_user.id,
        action="MULTI_DEPT_ROUTED",
        entity_type="Document",
        entity_id=document_id,
        description=f"Document {doc.reference_no} routed to {len(created_routings)} department(s)"
    )
    return created_routings


    print(f"[CDTRS SEED] Successfully verified {len(dept_map)} departments and {len(users_data)} system accounts.", flush=True)