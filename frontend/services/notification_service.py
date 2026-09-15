from typing import Any, Dict, List, Optional, Union

from models.document import DocumentModel
from models.notification import NotificationModel
from repositories.provider import get_repository


class NotificationService:
    """Client notification service scoped to the active backend context."""

    def __init__(self):
        pass

    def get_notifications(self, user_id: Optional[int] = None, unread_only: bool = False) -> List[NotificationModel]:
        return get_repository().get_notifications(user_id=user_id, unread_only=unread_only)

    def mark_as_read(self, notification_id: int) -> bool:
        return get_repository().mark_notification_read(notification_id)

    def _coerce_document(self, document: Union[DocumentModel, int, Dict[str, Any]]) -> Optional[DocumentModel]:
        if isinstance(document, DocumentModel):
            return document
        if isinstance(document, int):
            return get_repository().get_document(document)
        if isinstance(document, dict):
            return DocumentModel.from_dict(document)
        return None

    def _user(self, user_id: Optional[int]):
        if not user_id:
            return None
        try:
            return next((u for u in get_repository().get_users() if u.id == user_id), None)
        except Exception:
            return None

    def resolve_reminder_recipients(
        self, document: Union[DocumentModel, int, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve responsibility strictly from canonical routing/assignment data."""
        doc = self._coerce_document(document)
        if not doc or not doc.id:
            return []

        repo = get_repository()
        recipients: List[Dict[str, Any]] = []
        seen = set()

        try:
            assignments = doc.active_work_assignments
        except Exception:
            assignments = []

        for assignment in assignments or []:
            members = getattr(assignment, 'active_members', None) or getattr(assignment, 'members', None) or []
            member_ids = []
            for member in members:
                uid = getattr(member, 'user_id', None)
                if uid and uid not in member_ids:
                    member_ids.append(uid)
            primary = getattr(assignment, 'assigned_to_id', None)
            if primary and primary not in member_ids:
                member_ids.append(primary)

            for uid in member_ids:
                if uid in seen:
                    continue
                user = self._user(uid)
                if not user:
                    continue
                recipients.append({
                    'recipient_type': 'EMPLOYEE',
                    'user_id': uid,
                    'user_name': user.full_name,
                    'role': getattr(user, 'role', None) or 'Employee',
                    'department_name': getattr(user, 'department_name', None),
                    'document_id': doc.id,
                    'document_reference': doc.reference,
                    'document_title': doc.title,
                    'assignment_id': getattr(assignment, 'id', None),
                    'team_name': getattr(assignment, 'team_name', None),
                })
                seen.add(uid)

        if recipients:
            return recipients

        # No WorkAssignment: a DEPARTMENT_HOD branch means the HOD(s) of that
        # routed department are responsible. This is still branch-derived.
        try:
            branches = repo.get_document_branches(doc.id) or []
        except Exception:
            branches = []

        for branch in branches:
            if isinstance(branch, dict):
                btype = str(branch.get('branch_type') or '').upper()
                active = branch.get('is_active', True)
                dept_id = branch.get('department_id')
            else:
                btype = str(getattr(branch, 'branch_type', '') or '').upper()
                active = getattr(branch, 'is_active', True)
                dept_id = getattr(branch, 'department_id', None)
            if not active or btype != 'DEPARTMENT_HOD' or not dept_id:
                continue
            try:
                hods = [u for u in repo.get_users(role='HOD', department_id=dept_id) if getattr(u, 'is_active', True)]
            except Exception:
                hods = []
            for hod in hods:
                if hod.id in seen:
                    continue
                recipients.append({
                    'recipient_type': 'HOD', 'user_id': hod.id, 'user_name': hod.full_name,
                    'role': 'HOD', 'department_name': getattr(hod, 'department_name', None),
                    'document_id': doc.id, 'document_reference': doc.reference, 'document_title': doc.title,
                    'routing_id': getattr(branch, 'id', None) if not isinstance(branch, dict) else branch.get('id'),
                })
                seen.add(hod.id)
        return recipients

    def resolve_reminder_recipient(self, document: Union[DocumentModel, int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        recipients = self.resolve_reminder_recipients(document)
        return recipients[0] if recipients else None

    def send_action_reminder(self, document_id: int, message: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            result = get_repository().send_document_reminder(document_id, message=message)
            if result and result.get('status') == 'success':
                from services.event_bus import event_bus
                event_bus.notify_workflow_updated(document_id)
                return {
                    'recipient_type': 'RESPONSIBLE_USER',
                    'user_id': result.get('recipient_user_id'),
                    'user_name': result.get('recipient_name'),
                    'recipient_email': result.get('recipient_email'),
                    'role': result.get('recipient_role'),
                    'channel_used': result.get('channel_used'),
                    'email_dispatched': result.get('email_dispatched', False),
                    'document_id': document_id,
                    'message': result.get('message'),
                }
        except Exception:
            return None
        return None

    def send_all_due_reminders(self) -> List[Dict[str, Any]]:
        docs = get_repository().get_documents() or []
        dispatched = []
        for doc in docs:
            status = str(getattr(doc, 'status', '') or '').lower()
            priority = str(getattr(doc, 'priority', '') or '').lower()
            if status == 'closed' or priority not in {'red', 'orange', 'high', 'urgent', 'medium'}:
                continue
            result = self.send_action_reminder(doc.id) if doc.id else None
            if result:
                dispatched.append({'document': doc, 'recipient': result})
        return dispatched


notification_service = NotificationService()
