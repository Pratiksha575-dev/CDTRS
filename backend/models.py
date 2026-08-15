from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


# =========================================================
# DEPARTMENT
# =========================================================
class Department(Base):
    __tablename__ = "departments"

    d_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    d_name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    # Relationships
    employees = relationship(
        "Employee",
        back_populates="department"
    )

    users = relationship(
        "User",
        back_populates="department"
    )

    target_documents = relationship(
        "Document",
        foreign_keys="[Document.target_department_id]",
        back_populates="target_department"
    )

    suggested_documents = relationship(
        "Document",
        foreign_keys="[Document.suggested_department_id]",
        back_populates="suggested_department"
    )

    routes = relationship(
        "DocumentRoute",
        back_populates="to_department"
    )


# =========================================================
# EMPLOYEE (Organizational Structure Unit)
# =========================================================
class Employee(Base):
    __tablename__ = "employees"

    e_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    designation = Column(
        String(100),
        nullable=False
    )

    d_id = Column(
        Integer,
        ForeignKey("departments.d_id"),
        nullable=False
    )

    # Relationships
    department = relationship(
        "Department",
        back_populates="employees"
    )

    assigned_documents = relationship(
        "Document",
        back_populates="assigned_employee"
    )


# =========================================================
# USER (System Account & Authentication Actor)
# =========================================================
class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        nullable=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(30),
        nullable=False
    )  # Core V2: "Director Secretary", "Director", "HOD", "Employee"

    department_id = Column(
        Integer,
        ForeignKey("departments.d_id"),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    department = relationship(
        "Department",
        back_populates="users"
    )

    created_documents = relationship(
        "Document",
        foreign_keys="[Document.created_by]",
        back_populates="creator"
    )

    owned_documents = relationship(
        "Document",
        foreign_keys="[Document.current_owner_id]",
        back_populates="current_owner"
    )

    routes_sent = relationship(
        "DocumentRoute",
        foreign_keys="[DocumentRoute.from_user_id]",
        back_populates="from_user"
    )

    routes_received = relationship(
        "DocumentRoute",
        foreign_keys="[DocumentRoute.to_user_id]",
        back_populates="to_user"
    )

    assignments_given = relationship(
        "WorkAssignment",
        foreign_keys="[WorkAssignment.assigned_by_id]",
        back_populates="assigned_by"
    )

    assignments_received = relationship(
        "WorkAssignment",
        foreign_keys="[WorkAssignment.assigned_to_id]",
        back_populates="assigned_to"
    )

    progress_updates = relationship(
        "ProgressUpdate",
        back_populates="user"
    )

    attachments = relationship(
        "Attachment",
        back_populates="uploader"
    )

    workflow_history = relationship(
        "WorkflowHistory",
        back_populates="performer"
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="user"
    )

    notifications = relationship(
        "Notification",
        back_populates="recipient"
    )


# =========================================================
# MAIN DOCUMENT TABLE (Canonical Document Identity)
# =========================================================
class Document(Base):
    __tablename__ = "documents"

    doc_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    reference_no = Column(
        String(50),
        unique=True,
        index=True,
        nullable=True
    )  # e.g., "CDTRS-2026-001"

    title = Column(
        String(255),
        nullable=False
    )

    date = Column(
        Date,
        nullable=False
    )  # Received / Intake date

    mode = Column(
        String(50),
        nullable=False
    )  # Email, Intranet, Fax, Physical/Scan, Other

    source = Column(
        String(255),
        nullable=True
    )  # Sender / External origin

    # Priority & Deadlines
    priority = Column(
        String(20),
        default="Green",
        nullable=False
    )  # Red, Orange, Yellow, Green

    deadline = Column(
        Date,
        nullable=True
    )

    # User-facing status & Internal workflow stage
    status = Column(
        String(50),
        default="Received",
        nullable=False
    )  # Received, Under Director Review, Director Review Completed, Under HOD Processing, Assigned for Execution, In Progress, Progress Updated, Review Completed, Closed

    current_stage = Column(
        String(30),
        default="DS",
        nullable=False
    )  # Internal stage: DS, DIRECTOR, HOD, EMPLOYEE, CLOSED

    # Dedicated Director & HOD Remarks
    director_remark = Column(
        Text,
        nullable=True
    )

    hod_remark = Column(
        Text,
        nullable=True
    )

    # Dynamic Ownership & Target Department
    current_owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    target_department_id = Column(
        Integer,
        ForeignKey("departments.d_id"),
        nullable=True
    )

    # Retained intake / legacy fields
    remarks = Column(
        Text,
        nullable=True
    )  # General / Intake remarks

    action = Column(
        Text,
        nullable=True
    )  # Final action / summary description

    suggested_department_id = Column(
        Integer,
        ForeignKey("departments.d_id"),
        nullable=True
    )  # OCR suggested department

    assigned_employee_id = Column(
        Integer,
        ForeignKey("employees.e_id"),
        nullable=True
    )  # Backward compatible pointer

    file_path = Column(
        String(500),
        nullable=True
    )  # Primary file path / URI

    # Audit & Tracking
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_documents"
    )

    current_owner = relationship(
        "User",
        foreign_keys=[current_owner_id],
        back_populates="owned_documents"
    )

    target_department = relationship(
        "Department",
        foreign_keys=[target_department_id],
        back_populates="target_documents"
    )

    suggested_department = relationship(
        "Department",
        foreign_keys=[suggested_department_id],
        back_populates="suggested_documents"
    )

    assigned_employee = relationship(
        "Employee",
        foreign_keys=[assigned_employee_id],
        back_populates="assigned_documents"
    )

    routes = relationship(
        "DocumentRoute",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentRoute.created_at"
    )

    assignments = relationship(
        "WorkAssignment",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="WorkAssignment.created_at"
    )

    progress_updates = relationship(
        "ProgressUpdate",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProgressUpdate.created_at"
    )

    attachments = relationship(
        "Attachment",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at"
    )

    history = relationship(
        "WorkflowHistory",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="WorkflowHistory.created_at"
    )

    notifications = relationship(
        "Notification",
        back_populates="document",
        cascade="all, delete-orphan"
    )


# =========================================================
# DOCUMENT ROUTE (DS Routing Decisions)
# =========================================================
class DocumentRoute(Base):
    __tablename__ = "document_routes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=False
    )

    route_type = Column(
        String(50),
        nullable=False
    )  # DS_TO_DIRECTOR, DIRECTOR_TO_DS, DS_TO_HOD, DS_TO_EMPLOYEE, DS_TO_DIRECTOR_FOLLOWUP

    from_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    to_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    to_department_id = Column(
        Integer,
        ForeignKey("departments.d_id"),
        nullable=True
    )

    remarks = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="routes"
    )

    from_user = relationship(
        "User",
        foreign_keys=[from_user_id],
        back_populates="routes_sent"
    )

    to_user = relationship(
        "User",
        foreign_keys=[to_user_id],
        back_populates="routes_received"
    )

    to_department = relationship(
        "Department",
        back_populates="routes"
    )


# =========================================================
# WORK ASSIGNMENT (HOD -> Employee Delegation)
# =========================================================
class WorkAssignment(Base):
    __tablename__ = "work_assignments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=False
    )

    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    instructions = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="assignments"
    )

    assigned_by = relationship(
        "User",
        foreign_keys=[assigned_by_id],
        back_populates="assignments_given"
    )

    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assignments_received"
    )


# =========================================================
# PROGRESS UPDATE (Employee Chronological Free-Text Notes)
# =========================================================
class ProgressUpdate(Base):
    __tablename__ = "progress_updates"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="progress_updates"
    )

    user = relationship(
        "User",
        back_populates="progress_updates"
    )

    attachments = relationship(
        "Attachment",
        back_populates="progress_update",
        cascade="all, delete-orphan"
    )


# =========================================================
# ATTACHMENT (Main Document & Supporting Progress Files)
# =========================================================
class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=False
    )

    progress_update_id = Column(
        Integer,
        ForeignKey("progress_updates.id"),
        nullable=True
    )

    file_name = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        String(500),
        nullable=False
    )

    file_type = Column(
        String(50),
        nullable=True
    )

    file_size = Column(
        Integer,
        nullable=True
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="attachments"
    )

    progress_update = relationship(
        "ProgressUpdate",
        back_populates="attachments"
    )

    uploader = relationship(
        "User",
        back_populates="attachments"
    )


# =========================================================
# WORKFLOW HISTORY (Document-Centric Chronological Activity)
# =========================================================
class WorkflowHistory(Base):
    __tablename__ = "workflow_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=False
    )

    action = Column(
        String(100),
        nullable=False
    )

    from_role = Column(
        String(50),
        nullable=True
    )

    to_role = Column(
        String(50),
        nullable=True
    )

    remarks = Column(
        Text,
        nullable=True
    )

    details = Column(
        Text,
        nullable=True
    )

    performed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="history"
    )

    performer = relationship(
        "User",
        back_populates="workflow_history"
    )


# =========================================================
# NOTIFICATION (In-App Activity Notices)
# =========================================================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.doc_id"),
        nullable=True
    )

    title = Column(
        String(150),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    is_read = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    recipient = relationship(
        "User",
        back_populates="notifications"
    )

    document = relationship(
        "Document",
        back_populates="notifications"
    )


# =========================================================
# AUDIT LOG (System/Security/Admin Audit Trail)
# =========================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    action = Column(
        String(100),
        nullable=False
    )

    entity_type = Column(
        String(50),
        nullable=True
    )

    entity_id = Column(
        Integer,
        nullable=True
    )

    description = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="audit_logs"
    )