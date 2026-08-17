from typing import Any, Dict, List, Optional, Union

from models.document import DocumentModel
from models.enums import DocumentStatusEnum, WorkflowStageEnum
from models.notification import NotificationModel
from repositories.provider import get_repository


class NotificationService:
    """
    Client service managing in-app user notifications, read receipts,
    and centralized workflow action reminder resolution.
    """

    def __init__(self):
        pass

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        """Retrieves user notifications."""
        repo = get_repository()
        return repo.get_notifications(user_id=user_id, unread_only=unread_only)

    def mark_as_read(self, notification_id: int) -> bool:
        """Marks a notification as read."""
        repo = get_repository()
        return repo.mark_notification_read(notification_id)

    # =========================================================
    # CENTRALIZED ACTION REMINDER RESOLUTION
    # =========================================================

    def resolve_reminder_recipient(
        self,
        document: Union[DocumentModel, int, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Determines the single authoritative downstream reminder recipient
        strictly based on the document's CURRENT workflow state.

        RULE 1 (EMPLOYEE ASSIGNED):
        If assigned_employee_id != None, reminder goes exclusively to that employee.
        (Never additionally sent to HOD).

        RULE 2 (NO EMPLOYEE, BUT DEPARTMENT EXISTS):
        If department exists and no employee assigned, resolves the HOD responsible
        for that department.

        RULE 3 (NO DEPARTMENT & NO EMPLOYEE):
        Returns None. Unassigned/unrouted document.

        RULE 4 (CLOSED):
        Returns None. CLOSED is the only terminal completed state.
        """
        if isinstance(document, int):
            from services.document_service import document_service
            doc = document_service.get_document(document)
        elif isinstance(document, dict):
            doc = DocumentModel.from_dict(document)
        else:
            doc = document

        if not doc:
            return None

        # Rule 4: CLOSED -> Never generate reminder
        status_val = (doc.status or "").lower()
        stage_val = (doc.current_stage or "").lower()
        if status_val == DocumentStatusEnum.CLOSED.value.lower() or stage_val == WorkflowStageEnum.CLOSED.value.lower():
            return None

        repo = get_repository()
        all_users = repo.get_users()

        # Rule 1: Assigned Employee
        if doc.assigned_employee_id is not None:
            emp_user = next((u for u in all_users if u.id == doc.assigned_employee_id), None)
            if emp_user:
                return {
                    "recipient_type": "EMPLOYEE",
                    "user_id": emp_user.id,
                    "user_name": emp_user.full_name,
                    "role": "Employee",
                    "department_name": emp_user.department_name or doc.target_department_name,
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title
                }
            elif doc.assigned_employee_name and doc.assigned_employee_name != "Not Assigned":
                return {
                    "recipient_type": "EMPLOYEE",
                    "user_id": doc.assigned_employee_id,
                    "user_name": doc.assigned_employee_name,
                    "role": "Employee",
                    "department_name": doc.target_department_name,
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title
                }

        # Rule 2: Department exists, No Employee -> Resolve Department HOD
        dept_id = doc.target_department_id
        dept_name = doc.target_department_name or getattr(doc, "department", None)
        if dept_name in ("Not Specified", "-", "General", None):
            dept_name = None

        if dept_id or dept_name:
            hod_users = [u for u in all_users if (u.role or "").lower() in ("hod", "head of department")]
            matching_hod = None
            if dept_id:
                matching_hod = next((u for u in hod_users if u.department_id == dept_id), None)
            if not matching_hod and dept_name:
                matching_hod = next((u for u in hod_users if (u.department_name or "").lower() == dept_name.lower()), None)

            if matching_hod:
                return {
                    "recipient_type": "HOD",
                    "user_id": matching_hod.id,
                    "user_name": matching_hod.full_name,
                    "role": "HOD",
                    "department_name": matching_hod.department_name or dept_name,
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title
                }

        # Rule 3: No department and no employee
        return None

    def send_action_reminder(
        self,
        document_id: int,
        message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatches an official action reminder to the single resolved recipient.
        Logs an audit trail event and notifies the recipient.
        """
        repo = get_repository()
        doc = repo.get_document(document_id)
        if not doc:
            return None

        recipient = self.resolve_reminder_recipient(doc)
        if not recipient:
            return None

        default_msg = f"Action Reminder: Pending action required for document {doc.reference} ({doc.title})."
        rem_msg = message or default_msg

        if hasattr(repo, "_send_notification"):
            repo._send_notification(
                user_id=recipient["user_id"],
                document=doc,
                title="Action Reminder",
                message=rem_msg
            )

        if hasattr(repo, "_log_event"):
            repo._log_event(
                document_id=doc.id,
                action="Action Reminder Sent",
                from_role="DS",
                to_role=recipient["role"],
                remarks=f"Reminder dispatched to {recipient['user_name']} ({recipient['role']})."
            )

        from services.event_bus import event_bus
        event_bus.notify_workflow_updated(doc.id)
        return recipient

    def send_all_due_reminders(self) -> List[Dict[str, Any]]:
        """
        Scans all active, non-closed documents and dispatches reminders to their
        currently resolved recipients according to standard routing rules.
        """
        repo = get_repository()
        all_docs = repo.get_documents()
        due_docs = [
            d for d in all_docs
            if (d.status or "").lower() != DocumentStatusEnum.CLOSED.value.lower()
            and (d.current_stage or "").lower() != WorkflowStageEnum.CLOSED.value.lower()
            and (d.priority or "").lower() in ("red", "orange", "high", "urgent", "medium")
        ]

        dispatched = []
        for d in due_docs:
            rec = self.send_action_reminder(d.id)
            if rec:
                dispatched.append({"document": d, "recipient": rec})
        return dispatched


# Global singleton service instance
notification_service = NotificationService()
