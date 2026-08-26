from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from models import (
    AttachmentModel,
    DocumentModel,
    DocumentRouteModel,
    NotificationModel,
    ProgressUpdateModel,
    UserModel,
    WorkAssignmentModel,
    WorkflowEventModel,
)
from models.department import DepartmentModel


class BaseRepository(ABC):
    """
    Abstract repository protocol defining data access operations for CDTRS V2.
    Implemented by APIRepository (FastAPI live client) and MockRepository (in-memory test store).
    """

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        """Validates credentials and establishes authenticated user session."""
        pass

    @abstractmethod
    def get_current_user(self) -> Optional[UserModel]:
        """Returns currently authenticated user profile or None."""
        pass

    @abstractmethod
    def logout(self) -> None:
        """Terminates active user session and clears authentication tokens."""
        pass

    @abstractmethod
    def reset_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Resets the password for the specified user after verifying current password."""
        pass

    @abstractmethod
    def get_users(self, role: Optional[str] = None, department_id: Optional[int] = None) -> List[UserModel]:
        """Retrieves list of users filtered by role or department."""
        pass

    @abstractmethod
    def get_departments(self) -> List[DepartmentModel]:
        """Retrieves list of all institutional departments."""
        pass

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    @abstractmethod
    def get_inbox(self) -> List[DocumentModel]:
        """Retrieves incoming/unprocessed documents for DS intake."""
        pass

    @abstractmethod
    def add_inbox_item(self, document: DocumentModel) -> DocumentModel:
        """Adds a newly arrived dispatch or communication to the raw intake queue."""
        pass

    @abstractmethod
    def remove_inbox_item(self, item_id: int) -> bool:
        """Removes an incoming intake item after it has been processed and registered."""
        pass

    @abstractmethod
    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        """Retrieves documents repository with optional filtering."""
        pass

    @abstractmethod
    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Retrieves single canonical document by ID or reference."""
        pass

    @abstractmethod
    def create_document(self, document: DocumentModel, file_path: Optional[str] = None) -> DocumentModel:
        """Creates a new document in the repository."""
        pass

    @abstractmethod
    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Closes a completed document (DS action)."""
        pass

    # =========================================================
    # ROUTING (DS Decisions & Director Return)
    # =========================================================

    @abstractmethod
    def route_document(
        self,
        document_id: int,
        route_type: str,
        to_user_id: Optional[int] = None,
        to_department_id: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> DocumentModel:
        """Performs a routing transition (DS -> Director, DS -> HOD, DS -> Employee, etc.)."""
        pass

    @abstractmethod
    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        """Saves/updates Director remark on document without returning it."""
        pass

    @abstractmethod
    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Director workflow action returning reviewed document back to DS."""
        pass

    @abstractmethod
    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        """Saves/updates HOD remark on document without assigning."""
        pass

    @abstractmethod
    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """DS forwards employee progress update to Director as follow-up."""
        pass

    # =========================================================
    # WORK ASSIGNMENT (HOD -> Employee Delegation)
    # =========================================================

    @abstractmethod
    def assign_employee(
        self,
        document_id: int,
        assigned_to_id: int,
        instructions: Optional[str] = None
    ) -> WorkAssignmentModel:
        """HOD delegates work on a document to an employee."""
        pass

    @abstractmethod
    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        """Retrieves assignment records for a document."""
        pass

    # =========================================================
    # PROGRESS & ATTACHMENTS (Employee Reporting)
    # =========================================================

    @abstractmethod
    def submit_progress(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        """Employee submits a free-text progress update with optional attachment."""
        pass

    @abstractmethod
    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        """Retrieves chronological progress updates for a document."""
        pass

    @abstractmethod
    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = "WORKFLOW",
        source: Optional[str] = None
    ) -> AttachmentModel:
        """Uploads a supporting attachment linked to document or progress update."""
        pass

    @abstractmethod
    def get_attachments(self, document_id: int, category: Optional[str] = None) -> List[AttachmentModel]:
        """Retrieves all attachments associated with a document."""
        pass

    # =========================================================
    # WORKFLOW HISTORY & AUDIT
    # =========================================================

    @abstractmethod
    def get_workflow_history(self, document_id: int) -> List[WorkflowEventModel]:
        """Retrieves chronological workflow events for a specific document."""
        pass

    @abstractmethod
    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        """Retrieves system-wide activity history with filtering."""
        pass

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    @abstractmethod
    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        """Retrieves notification list for active user."""
        pass

    @abstractmethod
    def mark_notification_read(self, notification_id: int) -> bool:
        """Marks specific notification as read."""
        pass

    # =========================================================
    # DASHBOARD
    # =========================================================

    @abstractmethod
    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves role-specific dashboard metrics and document queues."""
        pass

    # =========================================================
    # OCR & ROUTING INTELLIGENCE
    # =========================================================

    @abstractmethod
    def get_ocr_result(self, document_id: int) -> Dict[str, Any]:
        """Returns the OCR record for a document (status, extracted text, fields)."""
        pass

    @abstractmethod
    def trigger_ocr(self, document_id: int) -> Dict[str, Any]:
        """Triggers server-side OCR processing on the stored document file."""
        pass

    @abstractmethod
    def get_routing_suggestion(self, document_id: int) -> Dict[str, Any]:
        """Returns the advisory routing suggestion generated from OCR + Director remarks."""
        pass

    @abstractmethod
    def analyze_routing(self, document_id: int) -> Dict[str, Any]:
        """Generates (or refreshes) the routing suggestion for a document."""
        pass
