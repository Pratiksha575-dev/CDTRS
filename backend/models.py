from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    Float,
    BigInteger,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
import enum

from database import Base


# =========================================================
# ENUMS
# =========================================================

class UserRole(str, enum.Enum):
    ADMIN    = "ADMIN"
    DS       = "DS"
    DIRECTOR = "DIRECTOR"
    TSO      = "TSO"
    HOD      = "HOD"
    EMPLOYEE = "EMPLOYEE"


class WorkContextType(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    HOD      = "HOD"
    DIRECTOR = "DIRECTOR"
    DS       = "DS"
    TSO      = "TSO"
    ADMIN    = "ADMIN"


class DirectorDecision(str, enum.Enum):
    CONTINUE = "CONTINUE"
    CLOSE    = "CLOSE"


class BranchType(str, enum.Enum):
    DEPARTMENT_HOD  = "DEPARTMENT_HOD"
    DIRECT_EMPLOYEE = "DIRECT_EMPLOYEE"
    TSO             = "TSO"


class DocumentStatus(str, enum.Enum):
    RECEIVED                  = "RECEIVED"
    UNDER_DIRECTOR_REVIEW     = "UNDER_DIRECTOR_REVIEW"
    DIRECTOR_REVIEW_COMPLETED = "DIRECTOR_REVIEW_COMPLETED"
    UNDER_HOD_PROCESSING      = "UNDER_HOD_PROCESSING"
    ASSIGNED_FOR_EXECUTION    = "ASSIGNED_FOR_EXECUTION"
    IN_PROGRESS               = "IN_PROGRESS"
    PROGRESS_UPDATED          = "PROGRESS_UPDATED"
    REVIEW_COMPLETED          = "REVIEW_COMPLETED"
    CLOSED                    = "CLOSED"


class ProgressValidationStatus(str, enum.Enum):
    DIRECT_TO_DS         = "DIRECT_TO_DS"
    PENDING_HOD_REVIEW   = "PENDING_HOD_REVIEW"
    HOD_APPROVED         = "HOD_APPROVED"
    RETURNED_TO_EMPLOYEE = "RETURNED_TO_EMPLOYEE"


class AssignmentStatus(str, enum.Enum):
    PENDING_EMPLOYEE = "PENDING_EMPLOYEE"
    IN_PROGRESS      = "IN_PROGRESS"
    PROGRESS_UPDATED = "PROGRESS_UPDATED"
    COMPLETED        = "COMPLETED"


class WorkflowStage(str, enum.Enum):
    DS       = "DS"
    DIRECTOR = "DIRECTOR"
    HOD      = "HOD"
    EMPLOYEE = "EMPLOYEE"
    CLOSED   = "CLOSED"


class Priority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


class RouteType(str, enum.Enum):
    INITIAL_DIRECTOR_REVIEW   = "INITIAL_DIRECTOR_REVIEW"
    RETURN_TO_DS              = "RETURN_TO_DS"
    POST_REVIEW_TO_HOD        = "POST_REVIEW_TO_HOD"
    POST_REVIEW_TO_EMPLOYEE   = "POST_REVIEW_TO_EMPLOYEE"
    FOLLOW_UP_TO_DIRECTOR     = "FOLLOW_UP_TO_DIRECTOR"


class SourceType(str, enum.Enum):
    OUTLOOK                  = "OUTLOOK"
    GOVERNMENT_MAIL          = "GOVERNMENT_MAIL"
    MANUAL_UPLOAD            = "MANUAL_UPLOAD"
    OTHER_APPROVED_SOURCE    = "OTHER_APPROVED_SOURCE"
    MANUAL                   = "MANUAL"


class MessageProcessingStatus(str, enum.Enum):
    NEW        = "NEW"
    PROCESSING = "PROCESSING"
    PROCESSED  = "PROCESSED"
    FAILED     = "FAILED"
    IGNORED    = "IGNORED"


class AttachmentType(str, enum.Enum):
    ORIGINAL            = "ORIGINAL"
    EMAIL_ATTACHMENT    = "EMAIL_ATTACHMENT"
    SUPPORTING_DOCUMENT = "SUPPORTING_DOCUMENT"
    PROGRESS_ATTACHMENT = "PROGRESS_ATTACHMENT"


class OCRStatus(str, enum.Enum):
    NONE       = "NONE"
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"


class RoutingSource(str, enum.Enum):
    DOCUMENT_CONTENT = "DOCUMENT_CONTENT"
    DIRECTOR_REMARK  = "DIRECTOR_REMARK"
    SOURCE_METADATA  = "SOURCE_METADATA"
    MANUAL           = "MANUAL"


class RemarkType(str, enum.Enum):
    DIRECTOR = "DIRECTOR"
    HOD      = "HOD"
    OTHER    = "OTHER"


class ReminderReason(str, enum.Enum):
    DUE_SOON        = "DUE_SOON"
    OVERDUE         = "OVERDUE"
    ACTION_REQUIRED = "ACTION_REQUIRED"


# =========================================================
# DEPARTMENT
# =========================================================

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    users      = relationship("User", back_populates="department_rel")
    employees  = relationship("Employee", back_populates="department")


# =========================================================
# EMPLOYEE
# =========================================================

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    designation = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    outlook_email = Column(String(255), nullable=True)
    gov_email = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    department = relationship("Department", back_populates="employees")
    user       = relationship("User", foreign_keys=[user_id], back_populates="employee_record")


# =========================================================
# USER
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False)
    employee_code = Column(String(50), nullable=True)
    designation = Column(String(100), nullable=True)
    managed_depts = Column(Text, nullable=True)

    email = Column(String(255), unique=True, nullable=True, index=True)
    outlook_email = Column(String(255), nullable=True)
    gov_email = Column(String(255), nullable=True)
    preferred_mail_channel = Column(String(50), default="outlook", nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    employee_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    department_rel  = relationship("Department", back_populates="users", foreign_keys=[department_id])
    employee_record = relationship(
        "Employee",
        foreign_keys="Employee.user_id",
        back_populates="user",
        uselist=False
    )
    notifications   = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    context_memberships = relationship("WorkContextMembership", back_populates="user", cascade="all, delete-orphan")

    @property
    def department(self) -> Optional[str]:
        """Return the user's department name from the canonical Department relationship."""
        if self.department_rel:
            return self.department_rel.name
        return None


# =========================================================
# WORK CONTEXT MEMBERSHIP (Canonical User Operational Context)
# =========================================================

class WorkContextMembership(Base):
    __tablename__ = "work_context_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    context_type = Column(SAEnum(WorkContextType, name="work_context_type"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user       = relationship("User", back_populates="context_memberships", foreign_keys=[user_id])
    department = relationship("Department", foreign_keys=[department_id])

    @property
    def department_name(self) -> Optional[str]:
        return self.department.name if self.department else None


# =========================================================
# INCOMING MESSAGES (Mail Intake & Provenance)
# =========================================================

class IncomingMessage(Base):
    __tablename__ = "incoming_messages"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(SAEnum(SourceType, name="source_type_enum"), default=SourceType.MANUAL_UPLOAD, nullable=False)
    external_message_id = Column(String(255), unique=True, nullable=True, index=True)
    sender_name = Column(String(150), nullable=True)
    sender_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    received_at = Column(DateTime, default=datetime.now)
    body_reference = Column(Text, nullable=True)
    has_attachments = Column(Boolean, default=False)
    processing_status = Column(SAEnum(MessageProcessingStatus, name="msg_status_enum"), default=MessageProcessingStatus.NEW, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    documents   = relationship("Document", back_populates="source_message")
    attachments = relationship("Attachment", back_populates="source_message")


# =========================================================
# DOCUMENT (Main Canonical Document Table)
# =========================================================

class Document(Base):
    __tablename__ = "documents"

    doc_id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    received_date = Column(Date, nullable=False)
    deadline = Column(Date, nullable=True)
    source = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=False)
    priority = Column(SAEnum(Priority, name="priority_enum"), default=Priority.MEDIUM, nullable=False)
    status = Column(SAEnum(DocumentStatus, name="document_status"), default=DocumentStatus.RECEIVED, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Source & OCR linkages
    source_message_id = Column(Integer, ForeignKey("incoming_messages.id"), nullable=True)
    ocr_status = Column(SAEnum(OCRStatus, name="ocr_status_enum"), default=OCRStatus.NONE, nullable=False)

    # Optimistic Concurrency Control
    version = Column(Integer, default=1, nullable=False)

    director_remark = Column(Text, nullable=True)
    hod_remark = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    creator             = relationship("User", foreign_keys=[created_by])
    source_message      = relationship("IncomingMessage", back_populates="documents")
    routes              = relationship("DocumentRoute", back_populates="document", cascade="all, delete-orphan")
    assignments         = relationship("WorkAssignment", back_populates="document", cascade="all, delete-orphan")
    progress_updates    = relationship("ProgressUpdate", back_populates="document", cascade="all, delete-orphan")
    attachments         = relationship("Attachment", back_populates="document", cascade="all, delete-orphan")
    workflow_history    = relationship("WorkflowHistory", back_populates="document", cascade="all, delete-orphan")
    notifications       = relationship("Notification", back_populates="document", cascade="all, delete-orphan")
    ocr_record          = relationship("DocumentOCR", back_populates="document", uselist=False, cascade="all, delete-orphan")
    extracted_fields    = relationship("DocumentExtractedField", back_populates="document", cascade="all, delete-orphan")
    routing_suggestion  = relationship("RoutingSuggestion", back_populates="document", uselist=False, cascade="all, delete-orphan")
    remarks_history     = relationship("DocumentRemark", back_populates="document", cascade="all, delete-orphan")
    reminders           = relationship("Reminder", back_populates="document", cascade="all, delete-orphan")
    department_routings = relationship("DocumentDepartmentRouting", back_populates="document", cascade="all, delete-orphan")
    director_reviews    = relationship("DirectorReview", back_populates="document", cascade="all, delete-orphan")

    @property
    def branches(self):
        return self.department_routings

    @property
    def work_assignments(self):
        return self.assignments


    @property
    def suggested_department_name(self) -> Optional[str]:
        if self.routing_suggestion and self.routing_suggestion.suggested_department:
            return self.routing_suggestion.suggested_department.name
        return None

    @property
    def suggested_department_id(self) -> Optional[int]:
        if self.routing_suggestion:
            return self.routing_suggestion.suggested_department_id
        return None

    @property
    def suggested_employee_name(self) -> Optional[str]:
        if self.routing_suggestion and self.routing_suggestion.suggested_employee:
            return self.routing_suggestion.suggested_employee.full_name
        return None

    @property
    def suggested_employee_id(self) -> Optional[int]:
        if self.routing_suggestion:
            return self.routing_suggestion.suggested_employee_id
        return None

    @property
    def routing_confidence(self) -> Optional[float]:
        if self.routing_suggestion:
            return self.routing_suggestion.routing_confidence
        return None

    @property
    def routing_reason(self) -> Optional[str]:
        if self.routing_suggestion:
            return self.routing_suggestion.routing_reason
        return None

    @property
    def is_director_instruction(self) -> bool:
        if self.routing_suggestion:
            return bool(self.routing_suggestion.is_director_instruction)
        return False


# =========================================================
# DOCUMENT ROUTES (DS Routing Ledger)
# =========================================================

class DocumentRoute(Base):
    __tablename__ = "document_routes"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    route_type = Column(SAEnum(RouteType, name="route_type_enum"), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    document      = relationship("Document", back_populates="routes")
    from_user     = relationship("User", foreign_keys=[from_user_id])
    to_user       = relationship("User", foreign_keys=[to_user_id])
    to_department = relationship("Department", foreign_keys=[to_department_id])


# =========================================================
# CANONICAL BRANCH ENTITY (DocumentDepartmentRouting)
# =========================================================

class DocumentDepartmentRouting(Base):
    __tablename__ = "document_department_routings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    status = Column(SAEnum(DocumentStatus, name="doc_dept_status"), default=DocumentStatus.UNDER_HOD_PROCESSING, nullable=False)
    instructions = Column(Text, nullable=True)
    routed_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    # Canonical Evolved Fields
    branch_type = Column(SAEnum(BranchType, name="branch_type"), default=BranchType.DEPARTMENT_HOD, nullable=False)
    routed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    routed_by_context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    target_context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    requires_hod_validation = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    document           = relationship("Document", back_populates="department_routings")
    department         = relationship("Department", foreign_keys=[department_id])
    routed_by_user     = relationship("User", foreign_keys=[routed_by_user_id])
    target_user        = relationship("User", foreign_keys=[target_user_id])
    routed_by_context  = relationship("WorkContextMembership", foreign_keys=[routed_by_context_membership_id])
    target_context     = relationship("WorkContextMembership", foreign_keys=[target_context_membership_id])
    assignments        = relationship("WorkAssignment", back_populates="routing", cascade="all, delete-orphan")
    remark_targets     = relationship("DocumentRemarkTarget", back_populates="routing", cascade="all, delete-orphan")


# =========================================================
# WORK ASSIGNMENTS (Canonical Responsibility Model)
# =========================================================

class WorkAssignment(Base):
    __tablename__ = "work_assignments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requires_hod_validation = Column(Boolean, default=False)
    instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    # Canonical Evolved Fields
    routing_id = Column(Integer, ForeignKey("document_department_routings.id"), nullable=False)
    assigned_to_context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    superseded_by_id = Column(Integer, ForeignKey("work_assignments.id"), nullable=True)
    change_reason = Column(Text, nullable=True)
    team_name = Column(String(150), nullable=True)
    is_team = Column(Boolean, default=False, nullable=False)

    # Relationships
    document             = relationship("Document", back_populates="assignments")
    assigned_by          = relationship("User", foreign_keys=[assigned_by_user_id])
    assigned_to          = relationship("User", foreign_keys=[assigned_to_user_id])
    routing              = relationship("DocumentDepartmentRouting", back_populates="assignments", foreign_keys=[routing_id])
    assigned_to_context  = relationship("WorkContextMembership", foreign_keys=[assigned_to_context_membership_id])
    progress_updates     = relationship("ProgressUpdate", back_populates="work_assignment", cascade="all, delete-orphan")
    members              = relationship("WorkAssignmentMember", back_populates="assignment", cascade="all, delete-orphan")
    superseded_by        = relationship("WorkAssignment", remote_side=[id], foreign_keys=[superseded_by_id])


# =========================================================
# WORK ASSIGNMENT MEMBERS (HOD Team / Multi-Employee Support)
# =========================================================

class WorkAssignmentMember(Base):
    """
    Employee membership in a canonical WorkAssignment.
    Multiple active members can share one HOD-created work assignment.
    """
    __tablename__ = "work_assignment_members"

    id = Column(Integer, primary_key=True, index=True)
    work_assignment_id = Column(Integer, ForeignKey("work_assignments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    assignment = relationship("WorkAssignment", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    context_membership = relationship("WorkContextMembership", foreign_keys=[context_membership_id])

    @property
    def user_name(self) -> Optional[str]:
        return self.user.full_name if self.user else None


# =========================================================
# PROGRESS UPDATES (Append-only Work Update tied to WorkAssignment)
# =========================================================

class ProgressUpdate(Base):
    __tablename__ = "progress_updates"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    hod_validation_required = Column(Boolean, default=False)
    hod_validation_status = Column(SAEnum(ProgressValidationStatus, name="prog_val_status_enum"), default=ProgressValidationStatus.DIRECT_TO_DS, nullable=False)
    hod_review_note = Column(Text, nullable=True)
    hod_reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hod_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Canonical Evolved Link to WorkAssignment
    work_assignment_id = Column(Integer, ForeignKey("work_assignments.id"), nullable=False)

    # Relationships
    document        = relationship("Document", back_populates="progress_updates")
    submitted_by    = relationship("User", foreign_keys=[submitted_by_user_id])
    hod_reviewer    = relationship("User", foreign_keys=[hod_reviewed_by_user_id])
    attachments     = relationship("Attachment", back_populates="progress_update")
    work_assignment = relationship("WorkAssignment", back_populates="progress_updates", foreign_keys=[work_assignment_id])

    @property
    def user_name(self) -> Optional[str]:
        return self.submitted_by.full_name if self.submitted_by else None

    @property
    def hod_reviewer_name(self) -> Optional[str]:
        return self.hod_reviewer.full_name if self.hod_reviewer else None


# =========================================================
# ATTACHMENTS (Storage & Provenance)
# =========================================================

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=True)
    progress_update_id = Column(Integer, ForeignKey("progress_updates.id"), nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    attachment_type = Column(SAEnum(AttachmentType, name="att_type_enum"), default=AttachmentType.ORIGINAL, nullable=False)
    source_message_id = Column(Integer, ForeignKey("incoming_messages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    document        = relationship("Document", back_populates="attachments")
    progress_update = relationship("ProgressUpdate", back_populates="attachments")
    uploaded_by     = relationship("User", foreign_keys=[uploaded_by_user_id])
    source_message  = relationship("IncomingMessage", back_populates="attachments")


# =========================================================
# DIRECTOR REVIEWS (Canonical Immutable Director Decisions)
# =========================================================

class DirectorReview(Base):
    __tablename__ = "director_reviews"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    director_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    director_context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    decision = Column(SAEnum(DirectorDecision, name="director_decision"), nullable=False)
    remark_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    document_version = Column(Integer, default=1, nullable=False)

    # Relationships
    document           = relationship("Document", back_populates="director_reviews")
    director           = relationship("User", foreign_keys=[director_user_id])
    context_membership = relationship("WorkContextMembership", foreign_keys=[director_context_membership_id])


# =========================================================
# DOCUMENT REMARKS (Canonical History & Targeted Instructions)
# =========================================================

class DocumentRemark(Base):
    __tablename__ = "document_remarks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role_remark"), nullable=False)
    remark_text = Column(Text, nullable=False)
    remark_type = Column(SAEnum(RemarkType, name="remark_type_enum"), nullable=False)
    provenance = Column(String(50), default="MANUAL", nullable=False)
    context_membership_id = Column(Integer, ForeignKey("work_context_memberships.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    document           = relationship("Document", back_populates="remarks_history")
    author             = relationship("User", foreign_keys=[author_user_id])
    context_membership = relationship("WorkContextMembership", foreign_keys=[context_membership_id])
    targets            = relationship("DocumentRemarkTarget", back_populates="remark", cascade="all, delete-orphan")


class DocumentRemarkTarget(Base):
    __tablename__ = "document_remark_targets"

    id = Column(Integer, primary_key=True, index=True)
    remark_id = Column(Integer, ForeignKey("document_remarks.id"), nullable=False)
    routing_id = Column(Integer, ForeignKey("document_department_routings.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    remark  = relationship("DocumentRemark", back_populates="targets")
    routing = relationship("DocumentDepartmentRouting", back_populates="remark_targets")


# =========================================================
# DOCUMENT OCR (Full OCR Artifact)
# =========================================================

class DocumentOCR(Base):
    __tablename__ = "document_ocr"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), unique=True, nullable=False)
    extracted_text = Column(Text, nullable=True)
    ocr_status = Column(SAEnum(OCRStatus, name="ocr_record_status_enum"), default=OCRStatus.PENDING, nullable=False)
    ocr_engine = Column(String(100), default="Tesseract-v5/PaddleOCR", nullable=False)
    confidence = Column(Float, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="ocr_record")


# =========================================================
# DOCUMENT EXTRACTED FIELDS (Structured Key-Values & Verification)
# =========================================================

class DocumentExtractedField(Base):
    __tablename__ = "document_extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    extracted_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    source_page = Column(Integer, default=1, nullable=True)
    source_text = Column(Text, nullable=True)
    verified_value = Column(Text, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    document      = relationship("Document", back_populates="extracted_fields")
    verifier_user = relationship("User", foreign_keys=[verified_by])


# =========================================================
# ROUTING SUGGESTIONS (Advisory Routing Intelligence)
# =========================================================

class RoutingSuggestion(Base):
    __tablename__ = "routing_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), unique=True, nullable=False)
    suggested_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    suggested_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    routing_confidence = Column(Float, nullable=False)
    routing_reason = Column(Text, nullable=False)
    routing_source = Column(SAEnum(RoutingSource, name="routing_source_enum"), default=RoutingSource.DOCUMENT_CONTENT, nullable=False)
    is_director_instruction = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.now)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # Relationships
    document             = relationship("Document", back_populates="routing_suggestion")
    suggested_department = relationship("Department", foreign_keys=[suggested_department_id])
    suggested_employee   = relationship("User", foreign_keys=[suggested_employee_id])
    confirmer            = relationship("User", foreign_keys=[confirmed_by])


# =========================================================
# REMINDERS (Deadline & Action Escalation)
# =========================================================

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(SAEnum(ReminderReason, name="reminder_reason_enum"), nullable=False)
    due_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, default=datetime.now)
    is_read = Column(Boolean, default=False)
    deduplication_key = Column(String(200), unique=True, nullable=False, index=True)

    # Relationships
    document       = relationship("Document", back_populates="reminders")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])


# =========================================================
# WORKFLOW HISTORY (Immutable Document-centric Audit Trail)
# =========================================================

class WorkflowHistory(Base):
    __tablename__ = "workflow_history"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    performed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(150), nullable=False)
    from_role = Column(String(50), nullable=True)
    to_role = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    document     = relationship("Document", back_populates="workflow_history")
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])

    @property
    def performed_by_name(self) -> Optional[str]:
        if self.performed_by:
            return self.performed_by.full_name
        return self.from_role or "System"

    @property
    def user(self) -> Optional[str]:
        return self.performed_by_name

    @property
    def remarks(self) -> Optional[str]:
        return self.details


# =========================================================
# AUDIT LOG (System/Security/Administrative Logs)
# =========================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")


# =========================================================
# NOTIFICATIONS (Context-aware In-App Notifications)
# =========================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=True)
    workflow_event_id = Column(Integer, ForeignKey("workflow_history.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user     = relationship("User", back_populates="notifications")
    document = relationship("Document", back_populates="notifications")


# =========================================================
# SYSTEM SETTINGS
# =========================================================

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)