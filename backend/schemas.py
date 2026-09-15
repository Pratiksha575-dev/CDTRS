from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import date, datetime

from models import (
    UserRole, DocumentStatus, WorkflowStage, Priority, RouteType,
    SourceType, MessageProcessingStatus, AttachmentType, OCRStatus,
    RoutingSource, RemarkType, ReminderReason,
    ProgressValidationStatus, AssignmentStatus,
    WorkContextType, DirectorDecision, BranchType
)


# =========================================================
# DEPARTMENT
# =========================================================

class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None


class DepartmentResponse(BaseModel):
    id:         int
    name:       str
    code:       Optional[str] = None
    is_active:  bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# EMPLOYEE
# =========================================================

class EmployeeCreate(BaseModel):
    employee_code: str
    full_name:     str
    department_id: int
    designation:   str
    email:         Optional[str] = None
    outlook_email: Optional[str] = None
    gov_email:     Optional[str] = None
    user_id:       Optional[int] = None


class EmployeeResponse(BaseModel):
    id:            int
    employee_code: str
    full_name:     str
    department_id: int
    designation:   str
    email:         Optional[str] = None
    outlook_email: Optional[str] = None
    gov_email:     Optional[str] = None
    user_id:       Optional[int] = None
    is_active:     bool

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# WORK CONTEXT MEMBERSHIP
# =========================================================

class WorkContextMembershipResponse(BaseModel):
    id:              int
    user_id:         int
    context_type:    WorkContextType
    department_id:   Optional[int] = None
    department_name: Optional[str] = None
    is_active:       bool
    created_at:      datetime
    updated_at:      datetime

    model_config = ConfigDict(from_attributes=True)


class WorkContextMembershipCreate(BaseModel):
    user_id:       int
    context_type:  WorkContextType
    department_id: Optional[int] = None
    is_active:     bool = True


class WorkContextSwitchRequest(BaseModel):
    context_membership_id: int


# =========================================================
# USER
# =========================================================

class UserCreate(BaseModel):
    username:               str
    password:               str
    full_name:              str
    role:                   UserRole
    employee_code:          Optional[str] = None
    designation:            Optional[str] = None
    department:             Optional[str] = None
    managed_depts:          Optional[List[str]] = None
    email:                  Optional[str] = None
    outlook_email:          Optional[str] = None
    gov_email:              Optional[str] = None
    preferred_mail_channel: Optional[str] = "outlook"
    department_id:          Optional[int] = None
    employee_id:            Optional[int] = None


class UserResponse(BaseModel):
    id:                     int
    username:               str
    full_name:              str
    role:                   UserRole
    employee_code:          Optional[str] = None
    designation:            Optional[str] = None
    department:             Optional[str] = None
    managed_depts:          Optional[Any] = None
    email:                  Optional[str] = None
    outlook_email:          Optional[str] = None
    gov_email:              Optional[str] = None
    preferred_mail_channel: Optional[str] = "outlook"
    department_id:          Optional[int] = None
    employee_id:            Optional[int] = None
    is_active:              bool
    active_context_id:      Optional[int] = None
    context_memberships:    List[WorkContextMembershipResponse] = []
    created_at:             datetime
    updated_at:             datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# AUTH / LOGIN
# =========================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    user_id:            int
    username:           str
    role:               UserRole
    active_context_id:  Optional[int] = None


class LoginResponse(BaseModel):
    access_token:      str
    token_type:        str = "bearer"
    user:              UserResponse
    active_context_id: Optional[int] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class AdminPasswordResetRequest(BaseModel):
    username: str
    new_password: str


# =========================================================
# INCOMING MESSAGES (Mail Intake)
# =========================================================

class IntakeCreate(BaseModel):
    source_type:         SourceType = SourceType.OUTLOOK
    external_message_id: Optional[str] = None
    sender_name:         Optional[str] = None
    sender_email:        Optional[str] = None
    subject:             Optional[str] = None
    received_at:         Optional[datetime] = None
    body_reference:      Optional[str] = None


class IntakeProcessRequest(BaseModel):
    title:                   Optional[str] = None
    deadline:                Optional[date] = None
    priority:                Priority = Priority.MEDIUM
    ocr_text:                Optional[str] = None
    confidence:              Optional[float] = None
    suggested_department_id: Optional[int] = None
    suggested_employee_id:   Optional[int] = None


class IntakeResponse(BaseModel):
    id:                  int
    source_type:         SourceType
    external_message_id: Optional[str] = None
    sender_name:         Optional[str] = None
    sender_email:        Optional[str] = None
    subject:             Optional[str] = None
    received_at:         datetime
    body_reference:      Optional[str] = None
    has_attachments:     bool
    processing_status:   MessageProcessingStatus
    created_at:          datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# CANONICAL BRANCH (DocumentDepartmentRouting)
# =========================================================

class BranchCreate(BaseModel):
    branch_type:             BranchType
    department_id:           Optional[int] = None
    target_user_id:          Optional[int] = None
    requires_hod_validation: bool = False
    instructions:            Optional[str] = None


class BranchResponse(BaseModel):
    id:                              int
    document_id:                     int
    branch_type:                     BranchType
    department_id:                   Optional[int] = None
    routed_by_user_id:               Optional[int] = None
    routed_by_context_membership_id: Optional[int] = None
    target_context_membership_id:    Optional[int] = None
    target_user_id:                  Optional[int] = None
    requires_hod_validation:         bool = False
    status:                          DocumentStatus
    is_active:                       bool
    version:                         int
    routed_at:                       datetime
    instructions:                    Optional[str] = None
    completed_at:                    Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MultiBranchRouteRequest(BaseModel):
    branches:         List[BranchCreate]
    expected_version: Optional[int] = None


# =========================================================
# DOCUMENT
# =========================================================

class DocumentCreate(BaseModel):
    title:                   str
    description:             Optional[str] = None
    received_date:           date
    deadline:                Optional[date] = None
    source:                  Optional[str] = None
    mode:                    str = "Manual Upload"
    priority:                Priority = Priority.MEDIUM
    source_message_id:       Optional[int] = None
    suggested_department_id: Optional[int] = None
    suggested_employee_id:   Optional[int] = None
    ocr_text:                Optional[str] = None
    confidence:              Optional[float] = None
    director_remark:         Optional[str] = None


# =========================================================
# DIRECTOR REVIEWS
# =========================================================

class DirectorReviewRequest(BaseModel):
    decision:         DirectorDecision
    remark_text:      Optional[str] = None
    expected_version: Optional[int] = None


class DirectorReviewResponse(BaseModel):
    id:                             int
    document_id:                    int
    director_user_id:               int
    director_context_membership_id: Optional[int] = None
    decision:                       DirectorDecision
    remark_text:                    Optional[str] = None
    created_at:                     datetime
    document_version:               int

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    doc_id: int
    reference_no: str
    title: str
    description: Optional[str] = None
    received_date: date
    deadline: Optional[date] = None
    source: Optional[str] = None
    mode: str
    priority: Priority
    status: DocumentStatus
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_employee_id: Optional[int] = None
    suggested_employee_name: Optional[str] = None
    routing_confidence: Optional[float] = None
    routing_reason: Optional[str] = None
    is_director_instruction: bool = False
    created_by: int
    source_message_id: Optional[int] = None
    ocr_status: OCRStatus
    version: int
    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None
    branches: List[BranchResponse] = Field(default_factory=list)
    work_assignments: List["AssignmentResponse"] = Field(default_factory=list)
    director_reviews: List[DirectorReviewResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    doc_id: int
    reference_no: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    priority: Priority
    status: DocumentStatus
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_employee_id: Optional[int] = None
    suggested_employee_name: Optional[str] = None
    routing_confidence: Optional[float] = None
    routing_reason: Optional[str] = None
    is_director_instruction: bool = False
    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None
    ocr_status: OCRStatus
    version: int
    received_date: date
    deadline: Optional[date] = None
    branches: List[BranchResponse] = Field(default_factory=list)
    work_assignments: List["AssignmentResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# DOCUMENT ROUTING (DS -> Director / HOD / Employee)
# =========================================================

class RouteRequest(BaseModel):
    route_type:       RouteType
    to_user_id:       Optional[int] = None
    to_department_id: Optional[int] = None
    remarks:          Optional[str] = None
    requires_hod_validation: bool = False
    expected_version: Optional[int] = None


# =========================================================
# DIRECTOR REMARK
# =========================================================

class DirectorRemarkUpdate(BaseModel):
    director_remark:  str
    expected_version: Optional[int] = None


class ReturnToDSRequest(BaseModel):
    remarks:          Optional[str] = None
    decision:         Optional[DirectorDecision] = None
    expected_version: Optional[int] = None


# =========================================================
# HOD REMARK & ASSIGNMENT
# =========================================================

class HODRemarkUpdate(BaseModel):
    hod_remark:       str
    expected_version: Optional[int] = None


class AssignmentRequest(BaseModel):
    assigned_to_user_id:     int
    routing_id:              Optional[int] = None
    requires_hod_validation: bool = False
    instructions:            Optional[str] = None
    change_reason:           Optional[str] = None
    expected_version:        Optional[int] = None


class AssignmentResponse(BaseModel):
    id:                                int
    document_id:                       int
    assigned_by_user_id:               int
    assigned_to_user_id:               int
    routing_id:                        int
    assigned_to_context_membership_id: Optional[int] = None
    requires_hod_validation:           bool = False
    instructions:                      Optional[str] = None
    is_active:                         bool
    superseded_by_id:                  Optional[int] = None
    change_reason:                     Optional[str] = None
    assigned_at:                       datetime
    completed_at:                      Optional[datetime] = None
    team_name:                         Optional[str] = None
    is_team:                           bool = False
    members:                           List["AssignmentMemberResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# HOD TEAM / MULTI-EMPLOYEE ASSIGNMENT
# =========================================================

class AssignmentMemberCreate(BaseModel):
    user_id: int
    context_membership_id: Optional[int] = None


class AssignmentMemberResponse(BaseModel):
    id: int
    work_assignment_id: int
    user_id: int
    user_name: Optional[str] = None
    context_membership_id: Optional[int] = None
    is_active: bool
    assigned_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HODTeamAssignmentRequest(BaseModel):
    """HOD delegates within their department; DS may span departments."""
    member_user_ids: List[int]
    routing_id: Optional[int] = None
    team_name: Optional[str] = None
    instructions: Optional[str] = None
    requires_hod_validation: bool = False
    expected_version: Optional[int] = None


class DSTeamAssignmentRequest(HODTeamAssignmentRequest):
    """DS may create a team spanning employees from multiple routed departments."""
    pass


class HODTeamAssignmentResponse(BaseModel):
    id: int
    document_id: int
    assigned_by_user_id: int
    assigned_to_user_id: int
    routing_id: Optional[int] = None
    requires_hod_validation: bool = False
    instructions: Optional[str] = None
    team_name: Optional[str] = None
    is_team: bool = False
    members: List[AssignmentMemberResponse] = Field(default_factory=list)
    is_active: bool
    assigned_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

AssignmentResponse.model_rebuild()

# =========================================================
# DOCUMENT REMARKS (History)
# =========================================================

class DocumentRemarkResponse(BaseModel):
    id:                    int
    document_id:           int
    author_user_id:        int
    role:                  UserRole
    remark_text:           str
    remark_type:           RemarkType
    provenance:            str = "MANUAL"
    context_membership_id: Optional[int] = None
    created_at:            datetime
    updated_at:            datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PROGRESS UPDATES (Employee)
# =========================================================

class ProgressCreate(BaseModel):
    description:        str
    work_assignment_id: Optional[int] = None


class HODValidationRequest(BaseModel):
    action: str                       # "approve" or "return"
    note:   Optional[str] = None      # Optional correction or approval guidance


class ProgressResponse(BaseModel):
    id:                      int
    document_id:             int
    submitted_by_user_id:    int
    user_name:               Optional[str] = None
    description:             str
    hod_validation_required: bool = False
    hod_validation_status:   ProgressValidationStatus = ProgressValidationStatus.DIRECT_TO_DS
    hod_review_note:         Optional[str] = None
    hod_reviewed_by_user_id: Optional[int] = None
    hod_reviewer_name:       Optional[str] = None
    hod_reviewed_at:         Optional[datetime] = None
    work_assignment_id:      int
    created_at:              datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# FOLLOW-UP & CLOSURE
# =========================================================

class FollowUpRequest(BaseModel):
    remarks:          Optional[str] = None
    expected_version: Optional[int] = None


class CloseRequest(BaseModel):
    remarks:          Optional[str] = None
    expected_version: Optional[int] = None


# =========================================================
# ATTACHMENTS
# =========================================================

class AttachmentResponse(BaseModel):
    id:                  int
    document_id:         Optional[int] = None
    progress_update_id:  Optional[int] = None
    uploaded_by_user_id: int
    file_name:           str
    file_type:           Optional[str] = None
    file_size:           Optional[int] = None
    checksum:            Optional[str] = None
    attachment_type:     AttachmentType
    source_message_id:   Optional[int] = None
    created_at:          datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# OUTLOOK SYNC & EMAIL DISPATCH SCHEMAS
# =========================================================

class OutlookSyncResponse(BaseModel):
    status:             str               # "success", "not_configured", "error"
    synced_count:       int = 0
    ignored_duplicates: int = 0
    message:            str
    details:            Optional[List[dict]] = None


class ReminderSendRequest(BaseModel):
    message: Optional[str] = None


class ReminderSendResponse(BaseModel):
    status:             str
    recipient_user_id:  int
    recipient_name:     str
    recipient_email:    Optional[str] = None
    recipient_role:     str
    document_id:        int
    document_reference: str
    document_title:     str
    channel_used:       str               # "outlook", "gov_mail", "in_app"
    email_dispatched:   bool
    message:            str


# =========================================================
# OCR & EXTRACTED FIELDS
# =========================================================

class ExtractedFieldResponse(BaseModel):
    id:              int
    document_id:     int
    field_name:      str
    extracted_value: Optional[str] = None
    confidence:      Optional[float] = None
    source_page:     Optional[int] = None
    source_text:     Optional[str] = None
    verified_value:  Optional[str] = None
    verified_by:     Optional[int] = None
    verified_at:     Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldVerifyRequest(BaseModel):
    field_name:     str
    verified_value: str


class OCRResponse(BaseModel):
    id:               Optional[int] = None
    document_id:      int
    ocr_status:       OCRStatus
    ocr_engine:       Optional[str] = None
    confidence:       Optional[float] = None
    extracted_text:   Optional[str] = None
    processed_at:     Optional[datetime] = None
    error_message:    Optional[str] = None
    extracted_fields: List[ExtractedFieldResponse] = []

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# ROUTING SUGGESTIONS
# =========================================================

class RoutingSuggestionResponse(BaseModel):
    id:                      Optional[int] = None
    document_id:             int
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_employee_id:   Optional[int] = None
    suggested_employee_name: Optional[str] = None
    routing_confidence:      float
    routing_reason:          str
    routing_source:          RoutingSource
    is_director_instruction: bool
    generated_at:            datetime
    confirmed_by:            Optional[int] = None
    confirmed_at:            Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RoutingAnalyzeRequest(BaseModel):
    include_director_remark: bool = True


# =========================================================
# REMINDERS
# =========================================================

class ReminderResponse(BaseModel):
    id:                int
    document_id:       int
    recipient_user_id: int
    reason:            ReminderReason
    due_at:            Optional[datetime] = None
    sent_at:           datetime
    is_read:           bool
    deduplication_key: str

    model_config = ConfigDict(from_attributes=True)


class ReminderCheckResponse(BaseModel):
    reminders_created: int
    reminders:         List[ReminderResponse]


# =========================================================
# WORKFLOW HISTORY
# =========================================================

class WorkflowHistoryResponse(BaseModel):
    id:                  int
    document_id:         int
    performed_by_user_id: int
    performed_by_name:   Optional[str] = None
    user:                Optional[str] = None
    action:              str
    from_role:           Optional[str] = None
    to_role:             Optional[str] = None
    remarks:             Optional[str] = None
    details:             Optional[str] = None
    created_at:          datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# NOTIFICATIONS
# =========================================================

class NotificationResponse(BaseModel):
    id:                int
    user_id:           int
    document_id:       Optional[int] = None
    workflow_event_id: Optional[int] = None
    title:             str
    message:           str
    is_read:           bool
    created_at:        datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIVE EVENTS
# =========================================================

class LiveEventMessage(BaseModel):
    event_type:  str
    document_id: Optional[int] = None
    user_id:     Optional[int] = None
    timestamp:   datetime = datetime.utcnow()
    payload:     Optional[dict] = None


# =========================================================
# DASHBOARD
# =========================================================

class DashboardResponse(BaseModel):
    role:                  str
    total_documents:       int
    pending_action:        int
    unread_notifications:  int
    unread_reminders:      int = 0
    # DS-specific
    under_director_review: Optional[int] = None
    under_hod_processing:  Optional[int] = None
    in_progress:           Optional[int] = None
    closed_documents:      Optional[int] = None
    intake_pending:        Optional[int] = None
    # Director-specific
    documents_for_review:  Optional[int] = None
    # HOD-specific
    pending_assignment:    Optional[int] = None
    # Employee-specific
    active_assignments:    Optional[int] = None