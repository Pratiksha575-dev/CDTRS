from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


# =========================================================
# DEPARTMENT SCHEMAS
# =========================================================

class DepartmentCreate(BaseModel):
    d_name: str


class DepartmentResponse(BaseModel):
    d_id: int
    d_name: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# EMPLOYEE SCHEMAS
# =========================================================

class EmployeeCreate(BaseModel):
    name: str
    designation: str
    d_id: int


class EmployeeResponse(BaseModel):
    e_id: int
    name: str
    designation: str
    d_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# USER SCHEMAS
# =========================================================

class UserCreate(BaseModel):
    username: str
    full_name: str
    email: Optional[str] = None
    password: str
    role: str
    department_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str] = None
    role: str
    department_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# LOGIN SCHEMAS
# =========================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    department_id: Optional[int] = None


# =========================================================
# DOCUMENT SCHEMAS
# =========================================================

class DocumentCreate(BaseModel):
    title: str
    date: date
    mode: str
    source: Optional[str] = None
    reference_no: Optional[str] = None

    priority: str = "Green"
    deadline: Optional[date] = None

    status: str = "Received"
    current_stage: str = "DS"

    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None

    current_owner_id: Optional[int] = None
    target_department_id: Optional[int] = None

    # Legacy / intake fields
    remarks: Optional[str] = None
    action: Optional[str] = None
    suggested_department_id: Optional[int] = None
    assigned_employee_id: Optional[int] = None
    file_path: Optional[str] = None
    created_by: Optional[int] = None


class DocumentResponse(BaseModel):
    doc_id: int
    reference_no: Optional[str] = None
    title: str
    date: date
    mode: str
    source: Optional[str] = None

    priority: str
    deadline: Optional[date] = None

    status: str
    current_stage: str

    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None

    current_owner_id: Optional[int] = None
    target_department_id: Optional[int] = None

    remarks: Optional[str] = None
    action: Optional[str] = None
    suggested_department_id: Optional[int] = None
    assigned_employee_id: Optional[int] = None
    file_path: Optional[str] = None

    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True
    )


class DocumentStatusUpdate(BaseModel):
    status: str


class DocumentStageUpdate(BaseModel):
    current_stage: str


class DirectorRemarkUpdate(BaseModel):
    director_remark: str


class HODRemarkUpdate(BaseModel):
    hod_remark: str


# =========================================================
# DOCUMENT ROUTING SCHEMAS (DS Routing Decisions)
# =========================================================

class DocumentRouteCreate(BaseModel):
    document_id: int
    route_type: str  # DS_TO_DIRECTOR, DIRECTOR_TO_DS, DS_TO_HOD, DS_TO_EMPLOYEE, DS_TO_DIRECTOR_FOLLOWUP
    from_user_id: int
    to_user_id: Optional[int] = None
    to_department_id: Optional[int] = None
    remarks: Optional[str] = None
    is_active: bool = True


class DocumentRouteResponse(BaseModel):
    id: int
    document_id: int
    route_type: str
    from_user_id: int
    to_user_id: Optional[int] = None
    to_department_id: Optional[int] = None
    remarks: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# WORK ASSIGNMENT SCHEMAS (HOD -> Employee Delegation)
# =========================================================

class WorkAssignmentCreate(BaseModel):
    document_id: int
    assigned_by_id: int
    assigned_to_id: int
    instructions: Optional[str] = None
    is_active: bool = True


class WorkAssignmentResponse(BaseModel):
    id: int
    document_id: int
    assigned_by_id: int
    assigned_to_id: int
    instructions: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# PROGRESS UPDATE SCHEMAS (Employee Chronological Notes)
# =========================================================

class ProgressUpdateCreate(BaseModel):
    document_id: int
    user_id: int
    description: str


class ProgressUpdateResponse(BaseModel):
    id: int
    document_id: int
    user_id: int
    description: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# ATTACHMENT SCHEMAS (Main Document & Supporting Files)
# =========================================================

class AttachmentCreate(BaseModel):
    document_id: int
    progress_update_id: Optional[int] = None
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: int


class AttachmentResponse(BaseModel):
    id: int
    document_id: int
    progress_update_id: Optional[int] = None
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# WORKFLOW HISTORY SCHEMAS (Document-Centric Activity Log)
# =========================================================

class WorkflowCreate(BaseModel):
    document_id: int
    action: str
    from_role: Optional[str] = None
    to_role: Optional[str] = None
    remarks: Optional[str] = None
    details: Optional[str] = None
    performed_by: int


class WorkflowResponse(BaseModel):
    id: int
    document_id: int
    action: str
    from_role: Optional[str] = None
    to_role: Optional[str] = None
    remarks: Optional[str] = None
    details: Optional[str] = None
    performed_by: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# NOTIFICATION SCHEMAS (In-App Activity Alerts)
# =========================================================

class NotificationCreate(BaseModel):
    user_id: int
    document_id: Optional[int] = None
    title: str
    message: str


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    document_id: Optional[int] = None
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# AUDIT LOG SCHEMAS (System/Security/Admin Trail)
# =========================================================

class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    description: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )