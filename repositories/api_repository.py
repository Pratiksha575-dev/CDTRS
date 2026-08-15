from typing import Any, Dict, List, Optional

from api.client import api_client
from api.endpoints import Endpoints
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
from repositories.base import BaseRepository


class APIRepository(BaseRepository):
    """
    Production repository implementation communicating with the live FastAPI backend via APIClient.
    Translates service calls into REST API requests against centralized Endpoints.
    """

    def __init__(self):
        self._current_user: Optional[UserModel] = None

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        payload = {"username": username, "password": password}
        response = api_client.post(Endpoints.AUTH_LOGIN, json=payload)

        # Standard FastAPI OAuth2 / JWT login response returns access_token
        token = response.get("access_token")
        if token:
            api_client.set_auth_token(token)

        # If user profile is nested in login response or fetched via /auth/me
        user_data = response.get("user")
        if not user_data:
            user_data = api_client.get(Endpoints.AUTH_ME)

        if user_data:
            self._current_user = UserModel.from_dict(user_data)
            return self._current_user
        return None

    def get_current_user(self) -> Optional[UserModel]:
        if not self._current_user:
            try:
                user_data = api_client.get(Endpoints.AUTH_ME)
                if user_data:
                    self._current_user = UserModel.from_dict(user_data)
            except Exception:
                return None
        return self._current_user

    def logout(self) -> None:
        try:
            api_client.post(Endpoints.AUTH_LOGOUT)
        except Exception:
            pass
        finally:
            api_client.clear_auth_token()
            self._current_user = None

    def get_users(self, role: Optional[str] = None, department_id: Optional[int] = None) -> List[UserModel]:
        params = {}
        if role:
            params["role"] = role
        if department_id:
            params["department_id"] = department_id
        data = api_client.get(Endpoints.USERS_LIST, params=params)
        return [UserModel.from_dict(u) for u in data]

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    def get_inbox(self) -> List[DocumentModel]:
        data = api_client.get(Endpoints.DOCUMENTS_INBOX)
        return [DocumentModel.from_dict(d) for d in data]

    def remove_inbox_item(self, item_id: int) -> bool:
        # Calls DELETE on intake item endpoint if supported, or returns True
        try:
            api_client.delete(f"{Endpoints.DOCUMENTS_INBOX}/{item_id}")
            return True
        except Exception:
            return True

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        params = {}
        if status and status != "All Status":
            params["status"] = status
        if department and department != "All Departments":
            params["department"] = department
        if source and source != "All Sources":
            params["source"] = source
        if search:
            params["search"] = search

        data = api_client.get(Endpoints.DOCUMENTS_LIST, params=params)
        return [DocumentModel.from_dict(d) for d in data]

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        data = api_client.get(Endpoints.DOCUMENT_DETAIL(document_id))
        return DocumentModel.from_dict(data) if data else None

    def create_document(self, document: DocumentModel, file_path: Optional[str] = None) -> DocumentModel:
        if file_path:
            # Multipart upload with intake document payload
            data = api_client.upload(
                Endpoints.DOCUMENT_CREATE,
                file_path_or_tuple=file_path,
                field_name="file",
                extra_data=document.to_dict()
            )
        else:
            data = api_client.post(Endpoints.DOCUMENT_CREATE, json=document.to_dict())
        return DocumentModel.from_dict(data)

    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {"remarks": remarks}
        data = api_client.post(Endpoints.DOCUMENT_CLOSE(document_id), json=payload)
        return DocumentModel.from_dict(data)

    # =========================================================
    # ROUTING (DS Decisions & Director Return)
    # =========================================================

    def route_document(
        self,
        document_id: int,
        route_type: str,
        to_user_id: Optional[int] = None,
        to_department_id: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> DocumentModel:
        payload = {
            "route_type": route_type,
            "to_user_id": to_user_id,
            "to_department_id": to_department_id,
            "remarks": remarks
        }
        data = api_client.post(Endpoints.DOCUMENT_ROUTE(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        payload = {"director_remark": remark}
        data = api_client.put(Endpoints.DIRECTOR_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {"remarks": remarks}
        data = api_client.post(Endpoints.DOCUMENT_RETURN_TO_DS(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        payload = {"hod_remark": remark}
        data = api_client.put(Endpoints.HOD_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {"remarks": remarks}
        data = api_client.post(Endpoints.DOCUMENT_FOLLOW_UP(document_id), json=payload)
        return DocumentModel.from_dict(data)

    # =========================================================
    # WORK ASSIGNMENT (HOD -> Employee Delegation)
    # =========================================================

    def assign_employee(
        self,
        document_id: int,
        assigned_to_id: int,
        instructions: Optional[str] = None
    ) -> WorkAssignmentModel:
        payload = {
            "assigned_to_id": assigned_to_id,
            "instructions": instructions
        }
        data = api_client.post(Endpoints.DOCUMENT_ASSIGN(document_id), json=payload)
        return WorkAssignmentModel.from_dict(data)

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        data = api_client.get(Endpoints.DOCUMENT_ASSIGN(document_id))
        return [WorkAssignmentModel.from_dict(a) for a in data]

    # =========================================================
    # PROGRESS & ATTACHMENTS (Employee Reporting)
    # =========================================================

    def submit_progress(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        payload = {"description": description}
        if attachment_file_path:
            data = api_client.upload(
                Endpoints.PROGRESS_CREATE(document_id),
                file_path_or_tuple=attachment_file_path,
                field_name="file",
                extra_data=payload
            )
        else:
            data = api_client.post(Endpoints.PROGRESS_CREATE(document_id), json=payload)
        return ProgressUpdateModel.from_dict(data)

    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        data = api_client.get(Endpoints.PROGRESS_LIST(document_id))
        return [ProgressUpdateModel.from_dict(p) for p in data]

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = "WORKFLOW",
        source: Optional[str] = None
    ) -> AttachmentModel:
        extra = {"category": category}
        if progress_update_id:
            extra["progress_update_id"] = progress_update_id
        if source:
            extra["source"] = source
        data = api_client.upload(
            Endpoints.ATTACHMENT_UPLOAD(document_id),
            file_path_or_tuple=file_path,
            field_name="file",
            extra_data=extra
        )
        return AttachmentModel.from_dict(data)

    def get_attachments(self, document_id: int, category: Optional[str] = None) -> List[AttachmentModel]:
        params = {"category": category} if category else None
        data = api_client.get(Endpoints.ATTACHMENT_LIST(document_id), params=params)
        return [AttachmentModel.from_dict(a) for a in data]

    # =========================================================
    # WORKFLOW HISTORY & AUDIT
    # =========================================================

    def get_workflow_history(self, document_id: int) -> List[WorkflowEventModel]:
        data = api_client.get(Endpoints.DOCUMENT_HISTORY(document_id))
        return [WorkflowEventModel.from_dict(e) for e in data]

    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        params = {}
        if user and user != "All Users":
            params["user"] = user
        if action and action != "All Actions":
            params["action"] = action
        data = api_client.get("/history", params=params)
        return [WorkflowEventModel.from_dict(e) for e in data]

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        endpoint = Endpoints.NOTIFICATIONS_UNREAD if unread_only else Endpoints.NOTIFICATIONS_LIST
        data = api_client.get(endpoint)
        return [NotificationModel.from_dict(n) for n in data]

    def mark_notification_read(self, notification_id: int) -> bool:
        data = api_client.patch(Endpoints.NOTIFICATION_MARK_READ(notification_id))
        return bool(data.get("success", True))

    # =========================================================
    # DASHBOARD
    # =========================================================

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        params = {"role": role} if role else {}
        return api_client.get(Endpoints.DASHBOARD_STATS, params=params)
