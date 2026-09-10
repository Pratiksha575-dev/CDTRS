from typing import Any, Dict, List, Optional, Union

from models.document import DocumentModel
from models.enums import DocumentStatusEnum, WorkflowStageEnum
from models.notification import NotificationModel
from repositories.provider import get_repository


class NotificationService:
    """
    Client service for in-app notifications and workflow reminders.

    The backend remains authoritative for actual notification delivery.
    Local recipient resolution is only a UI/helper view of the current
    document state.
    """

    def __init__(self):
        pass

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False,
    ) -> List[NotificationModel]:
        """Retrieve notifications for the active user/context."""
        repo = get_repository()
        return repo.get_notifications(
            user_id=user_id,
            unread_only=unread_only,
        )

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        repo = get_repository()
        return repo.mark_notification_read(notification_id)

    # =========================================================
    # REMINDER RECIPIENT RESOLUTION
    # =========================================================

    def _coerce_document(
        self,
        document: Union[DocumentModel, int, Dict[str, Any]],
    ) -> Optional[DocumentModel]:
        if isinstance(document, int):
            from services.document_service import document_service
            return document_service.get_document(document)

        if isinstance(document, dict):
            return DocumentModel.from_dict(document)

        return document

    def _is_closed(self, doc: DocumentModel) -> bool:
        status_val = (doc.status or "").lower()
        stage_val = (doc.current_stage or "").lower()

        return (
            status_val == DocumentStatusEnum.CLOSED.value.lower()
            or stage_val == WorkflowStageEnum.CLOSED.value.lower()
        )

    def resolve_reminder_recipients(
        self,
        document: Union[DocumentModel, int, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Resolve the currently responsible downstream users.

        For team assignments, every active team member is represented.
        For a single assignment, the assigned employee is represented.
        If no employee is assigned but a department branch is active, the
        responsible HOD is represented.

        This method does not send notifications and does not change workflow.
        """
        doc = self._coerce_document(document)

        if not doc or self._is_closed(doc):
            return []

        repo = get_repository()

        # Team-aware path. DocumentModel exposes active assignment/member
        # helpers while retaining legacy single-assignee compatibility.
        recipients: List[Dict[str, Any]] = []
        seen_ids = set()

        for assignment in getattr(doc, "active_work_assignments", []) or []:
            members = getattr(assignment, "active_members", []) or []

            # A team assignment is represented by its member rows.
            for member in members:
                user_id = getattr(member, "user_id", None)
                if not user_id or user_id in seen_ids:
                    continue

                user = None
                try:
                    user = next(
                        (u for u in repo.get_users() if u.id == user_id),
                        None,
                    )
                except Exception:
                    pass

                if user:
                    user_name = user.full_name
                    role = getattr(user, "role", None) or "Employee"
                    department_name = (
                        getattr(user, "department_name", None)
                        or doc.target_department_name
                    )
                else:
                    user_name = getattr(member, "user_name", None) or "Employee"
                    role = "Employee"
                    department_name = doc.target_department_name

                recipients.append({
                    "recipient_type": "EMPLOYEE",
                    "user_id": user_id,
                    "user_name": user_name,
                    "role": role,
                    "department_name": department_name,
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title,
                    "assignment_id": getattr(assignment, "id", None),
                    "team_name": getattr(assignment, "team_name", None),
                })
                seen_ids.add(user_id)

            # Compatibility: an assignment may have a primary assignee even
            # when member rows are absent in an older response.
            primary_id = getattr(assignment, "assigned_to_user_id", None)
            if primary_id and primary_id not in seen_ids:
                try:
                    user = next(
                        (u for u in repo.get_users() if u.id == primary_id),
                        None,
                    )
                except Exception:
                    user = None

                recipients.append({
                    "recipient_type": "EMPLOYEE",
                    "user_id": primary_id,
                    "user_name": (
                        getattr(user, "full_name", None)
                        or getattr(assignment, "assigned_to_name", None)
                        or "Employee"
                    ),
                    "role": getattr(user, "role", None) or "Employee",
                    "department_name": (
                        getattr(user, "department_name", None)
                        or doc.target_department_name
                    ),
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title,
                    "assignment_id": getattr(assignment, "id", None),
                    "team_name": getattr(assignment, "team_name", None),
                })
                seen_ids.add(primary_id)

        if recipients:
            return recipients

        # Legacy/single employee compatibility.
        if doc.assigned_employee_id is not None:
            try:
                all_users = repo.get_users()
                emp_user = next(
                    (u for u in all_users if u.id == doc.assigned_employee_id),
                    None,
                )
            except Exception:
                emp_user = None

            if emp_user:
                return [{
                    "recipient_type": "EMPLOYEE",
                    "user_id": emp_user.id,
                    "user_name": emp_user.full_name,
                    "role": getattr(emp_user, "role", None) or "Employee",
                    "department_name": (
                        getattr(emp_user, "department_name", None)
                        or doc.target_department_name
                    ),
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title,
                }]

            if doc.assigned_employee_name and doc.assigned_employee_name != "Not Assigned":
                return [{
                    "recipient_type": "EMPLOYEE",
                    "user_id": doc.assigned_employee_id,
                    "user_name": doc.assigned_employee_name,
                    "role": "Employee",
                    "department_name": doc.target_department_name,
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title,
                }]

        # No employee: resolve department HOD.
        dept_id = doc.target_department_id
        dept_name = doc.target_department_name or getattr(doc, "department", None)

        if dept_name in ("Not Specified", "-", "General", None):
            dept_name = None

        if dept_id or dept_name:
            try:
                all_users = repo.get_users()
            except Exception:
                all_users = []

            hod_users = [
                u for u in all_users
                if (getattr(u, "role", "") or "").lower()
                in ("hod", "head of department")
            ]

            matching_hod = None

            if dept_id:
                matching_hod = next(
                    (u for u in hod_users if u.department_id == dept_id),
                    None,
                )

            if not matching_hod and dept_name:
                matching_hod = next(
                    (
                        u for u in hod_users
                        if (getattr(u, "department_name", "") or "").lower()
                        == dept_name.lower()
                    ),
                    None,
                )

            if matching_hod:
                return [{
                    "recipient_type": "HOD",
                    "user_id": matching_hod.id,
                    "user_name": matching_hod.full_name,
                    "role": "HOD",
                    "department_name": (
                        matching_hod.department_name or dept_name
                    ),
                    "document_id": doc.id,
                    "document_reference": doc.reference,
                    "document_title": doc.title,
                }]

        return []

    def resolve_reminder_recipient(
        self,
        document: Union[DocumentModel, int, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Backward-compatible singular recipient helper.

        For a team, this returns the first active member only. Actual
        notification delivery should use the backend reminder endpoint,
        which remains authoritative.
        """
        recipients = self.resolve_reminder_recipients(document)
        return recipients[0] if recipients else None

    # =========================================================
    # OFFICIAL REMINDER DELIVERY
    # =========================================================

    def send_action_reminder(
        self,
        document_id: int,
        message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatch an official reminder through the backend.

        The backend decides the authoritative recipient/delivery channel.
        """
        repo = get_repository()

        try:
            res = repo.send_document_reminder(
                document_id,
                message=message,
            )

            if res and res.get("status") == "success":
                from services.event_bus import event_bus
                event_bus.notify_workflow_updated(document_id)

                return {
                    "recipient_type": "RESPONSIBLE_USER",
                    "user_id": res.get("recipient_user_id"),
                    "user_name": res.get("recipient_name"),
                    "recipient_email": res.get("recipient_email"),
                    "role": res.get("recipient_role"),
                    "channel_used": res.get("channel_used"),
                    "email_dispatched": res.get("email_dispatched", False),
                    "document_id": document_id,
                    "message": res.get("message"),
                }

            return None

        except Exception:
            return None

    def send_all_due_reminders(self) -> List[Dict[str, Any]]:
        """Dispatch reminders for active, non-closed priority documents."""
        repo = get_repository()
        all_docs = repo.get_documents()

        due_docs = [
            d for d in all_docs
            if (d.status or "").lower()
            != DocumentStatusEnum.CLOSED.value.lower()
            and (d.current_stage or "").lower()
            != WorkflowStageEnum.CLOSED.value.lower()
            and (d.priority or "").lower()
            in ("red", "orange", "high", "urgent", "medium")
        ]

        dispatched = []

        for doc in due_docs:
            result = self.send_action_reminder(doc.id)
            if result:
                dispatched.append({
                    "document": doc,
                    "recipient": result,
                })

        return dispatched


# Global singleton service instance
notification_service = NotificationService()
