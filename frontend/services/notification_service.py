"""Notifications and reminders for the active work context.

Notifications are context-aware on the server: a user wearing their HOD hat
sees HOD notifications, not the ones raised for their Employee hat.  Nothing
is filtered locally.
"""

from typing import Any, Dict, List, Optional, Union

from models import NotificationModel, WorkItemModel
from models.document import DocumentModel
from repositories.provider import get_repository


class NotificationService:

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    def get_notifications(self, unread_only: bool = False) -> List[NotificationModel]:
        return get_repository().get_notifications(unread_only=unread_only)

    def get_unread(self) -> List[NotificationModel]:
        return get_repository().get_notifications(unread_only=True)

    def unread_count(self) -> int:
        try:
            return len(self.get_unread())
        except Exception:
            return 0

    def mark_as_read(self, notification_id: int) -> bool:
        return get_repository().mark_notification_read(notification_id)

    def mark_all_read(self) -> int:
        return get_repository().mark_all_notifications_read()

    # =========================================================
    # REMINDERS
    # =========================================================

    def get_reminders(self) -> List[Dict[str, Any]]:
        return get_repository().get_reminders()

    def check_deadlines(self) -> Dict[str, Any]:
        """Ask the backend to raise reminders for work that is due soon or
        overdue.  Reminders are per work item, so each person is told about
        their own deadline rather than the document's."""
        return get_repository().check_reminders()

    def resolve_reminder_recipients(
        self, document: Union[DocumentModel, int, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Who currently holds open work on this document.

        Derived strictly from live work items, so a reminder always reaches
        the person actually holding the work - not a stale assignee.
        """
        doc: Optional[DocumentModel]
        if isinstance(document, DocumentModel):
            doc = document
        elif isinstance(document, int):
            doc = get_repository().get_document(document)
        elif isinstance(document, dict):
            doc = DocumentModel.from_dict(document)
        else:
            doc = None

        if not doc or not doc.id:
            return []

        recipients: List[Dict[str, Any]] = []
        seen = set()
        for item in doc.all_work_items:
            if item.is_finished or item.assigned_to_user_id in seen:
                continue
            seen.add(item.assigned_to_user_id)
            recipients.append({
                "user_id": item.assigned_to_user_id,
                "name": item.assignee_name,
                "work_item_id": item.id,
                "branch": item.branch_label,
                "stage": item.stage_label,
                "deadline": item.deadline_display,
                "deadline_state": item.deadline_state,
            })
        return recipients

    def send_reminder(
        self,
        document_id: int,
        work_item_id: Optional[int] = None,
        recipient_user_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        return get_repository().send_document_reminder(
            document_id, work_item_id, recipient_user_id, message
        )


notification_service = NotificationService()
