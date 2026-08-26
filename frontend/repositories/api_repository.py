from datetime import datetime
from typing import Any, Dict, List, Optional

from api.client import api_client
from api.endpoints import Endpoints
from api.exceptions import UnauthorizedError
from models import (
    AttachmentModel,
    DocumentModel,
    NotificationModel,
    ProgressUpdateModel,
    UserModel,
    WorkAssignmentModel,
    WorkflowEventModel,
)
from models.department import DepartmentModel
from models.enums import PriorityEnum, RoleEnum, RouteTypeEnum
from repositories.base import BaseRepository


class APIRepository(BaseRepository):
    """
    Production repository implementation communicating with the live FastAPI backend via APIClient.
    Translates service calls into REST API requests against centralized Endpoints.
    """

    # Mapping frontend RouteTypeEnum values to backend RouteType enum member strings
    ROUTE_TYPE_MAP = {
        RouteTypeEnum.DS_TO_DIRECTOR.value: "INITIAL_DIRECTOR_REVIEW",
        RouteTypeEnum.DIRECTOR_TO_DS.value: "RETURN_TO_DS",
        RouteTypeEnum.DS_TO_HOD.value: "POST_REVIEW_TO_HOD",
        RouteTypeEnum.DS_TO_EMPLOYEE.value: "POST_REVIEW_TO_EMPLOYEE",
        RouteTypeEnum.DS_TO_DIRECTOR_FOLLOWUP.value: "FOLLOW_UP_TO_DIRECTOR",
        # Pass-through for exact backend enum member names
        "INITIAL_DIRECTOR_REVIEW": "INITIAL_DIRECTOR_REVIEW",
        "RETURN_TO_DS": "RETURN_TO_DS",
        "POST_REVIEW_TO_HOD": "POST_REVIEW_TO_HOD",
        "POST_REVIEW_TO_EMPLOYEE": "POST_REVIEW_TO_EMPLOYEE",
        "FOLLOW_UP_TO_DIRECTOR": "FOLLOW_UP_TO_DIRECTOR",
    }

    def __init__(self):
        self._current_user: Optional[UserModel] = None

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        """Validates credentials, acquires JWT Bearer token, and retrieves profile."""
        payload = {"username": username.strip(), "password": password}
        try:
            response = api_client.post(Endpoints.AUTH_LOGIN, json=payload)
        except UnauthorizedError:
            return None
        except Exception:
            raise

        token = response.get("access_token")
        if token:
            api_client.set_auth_token(token)

        user_data = response.get("user")
        if not user_data:
            user_data = api_client.get(Endpoints.AUTH_ME)

        if user_data:
            self._current_user = UserModel.from_dict(user_data)
            return self._current_user
        return None

    def get_current_user(self) -> Optional[UserModel]:
        """Returns currently authenticated user profile."""
        if not self._current_user and api_client._auth_token:
            try:
                user_data = api_client.get(Endpoints.AUTH_ME)
                if user_data:
                    self._current_user = UserModel.from_dict(user_data)
            except Exception:
                return None
        return self._current_user

    def logout(self) -> None:
        """Terminates active session and clears auth token."""
        try:
            api_client.post(Endpoints.AUTH_LOGOUT)
        except Exception:
            pass
        finally:
            api_client.clear_auth_token()
            self._current_user = None

    def reset_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Resets user password via backend reset endpoint requiring current password."""
        payload = {
            "username": username.strip(),
            "old_password": old_password,
            "new_password": new_password.strip()
        }
        response = api_client.post(Endpoints.AUTH_RESET_PASSWORD, json=payload)
        return bool(response)

    def get_departments(self) -> List[DepartmentModel]:
        """Retrieves list of all institutional departments from backend."""
        try:
            data = api_client.get(Endpoints.DEPARTMENTS_LIST)
            return [DepartmentModel.from_dict(d) for d in data]
        except Exception:
            # Return empty list — callers must handle gracefully.
            # Do NOT return hardcoded departments with fake IDs as they would
            # cause documents to be routed to wrong departments.
            return []

    def get_users(self, role: Optional[str] = None, department_id: Optional[int] = None) -> List[UserModel]:
        """
        Retrieves users. Uses /users, falling back to /departments/{id}/employees.
        """
        users: List[UserModel] = []
        try:
            data = api_client.get(Endpoints.USERS_LIST)
            users = [UserModel.from_dict(u) for u in data]
        except Exception:
            target_dept = department_id or (self._current_user.department_id if self._current_user else None)
            if target_dept:
                try:
                    data = api_client.get(Endpoints.DEPARTMENT_EMPLOYEES(target_dept))
                    users = [
                        UserModel(
                            id=emp.get("user_id") or emp.get("id"),
                            username=emp.get("employee_code", f"emp_{emp.get('id')}"),
                            full_name=emp.get("full_name", ""),
                            role="Employee",
                            department_id=emp.get("department_id"),
                            department_name=None,
                            is_active=emp.get("is_active", True)
                        )
                        for emp in data
                    ]
                except Exception:
                    users = []

        # Populate department_name if missing
        try:
            depts = {d.id: d.name for d in self.get_departments()}
            for u in users:
                if u.department_id and not u.department_name:
                    u.department_name = depts.get(u.department_id, "General")
        except Exception:
            pass

        if role:
            normalized_target = RoleEnum.normalize(role).lower()
            users = [u for u in users if (u.role or "").lower() == normalized_target]
        if department_id:
            users = [u for u in users if u.department_id == department_id]

        return users

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    def get_inbox(self) -> List[DocumentModel]:
        """Retrieves role-scoped inbox queue from backend."""
        data = api_client.get(Endpoints.DOCUMENTS_INBOX)
        return [DocumentModel.from_dict(d) for d in data]

    def add_inbox_item(self, document: DocumentModel) -> DocumentModel:
        """
        Adds a new incoming dispatch to the repository via the manual intake pipeline.
        Satisfies BaseRepository abstract method contract.
        """
        return self.create_document(document, file_path=document.file_path)

    def remove_inbox_item(self, item_id: int) -> bool:
        """
        Safely acknowledges intake item transition without raising errors.
        Backend transitions inbox status through document processing and routing.
        """
        return True

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        """
        Retrieves accessible documents list using /documents endpoint.
        Applies client-side filters for multi-criteria search.
        """
        try:
            data = api_client.get(Endpoints.DOCUMENTS_LIST)
        except Exception:
            data = api_client.get(Endpoints.DOCUMENTS_INBOX)

        docs = [DocumentModel.from_dict(d) for d in data]

        # Apply filtering
        if status and status != "All Status":
            docs = [d for d in docs if (d.status or "").lower() == status.lower()]
        if department and department != "All Departments":
            docs = [d for d in docs if (d.department or "").lower() == department.lower()]
        if source and source != "All Sources":
            docs = [d for d in docs if (d.source or "").lower() == source.lower()]
        if search:
            q = search.lower().strip()
            docs = [
                d for d in docs
                if q in (d.title or "").lower()
                or q in (d.reference or "").lower()
                or q in (d.source or "").lower()
                or q in (d.department or "").lower()
            ]

        return docs

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Retrieves single canonical document by ID."""
        data = api_client.get(Endpoints.DOCUMENT_DETAIL(document_id))
        return DocumentModel.from_dict(data) if data else None

    def create_document(self, document: DocumentModel, file_path: Optional[str] = None) -> DocumentModel:
        """
        Creates a new canonical document. When file_path is provided, uses the
        multipart manual-upload pipeline. Otherwise sends JSON creation payload.
        """
        raw_date = str(document.date).split()[0] if document.date else datetime.now().strftime("%Y-%m-%d")
        priority_val = PriorityEnum.normalize(document.priority).upper()

        if file_path:
            form_data = {
                "title": document.title,
                "received_date": raw_date,
                "mode": document.mode or "Manual Upload",
                "priority": priority_val,
                "source": document.source or "Manual Intake",
                "description": document.remarks or document.title or "Uploaded document"
            }
            data = api_client.upload(
                Endpoints.INTAKE_MANUAL_UPLOAD,
                file_path_or_tuple=file_path,
                field_name="file",
                extra_data=form_data
            )
        else:
            payload = {
                "title": document.title,
                "received_date": raw_date,
                "mode": document.mode or "Manual Upload",
                "priority": priority_val,
                "source": document.source or "External",
                "deadline": str(document.deadline).split()[0] if document.deadline else None,
                "description": document.remarks or document.title
            }
            data = api_client.post(Endpoints.DOCUMENT_CREATE, json=payload)

        return DocumentModel.from_dict(data)

    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Permanently closes a completed document."""
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
        """
        Routes a document. Translates frontend RouteTypeEnum values to backend
        expected enum member strings.
        """
        backend_route_type = self.ROUTE_TYPE_MAP.get(route_type, route_type)
        payload = {
            "route_type": backend_route_type,
            "to_user_id": to_user_id,
            "to_department_id": to_department_id,
            "remarks": remarks
        }
        data = api_client.post(Endpoints.DOCUMENT_ROUTE(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        """Director saves or updates a remark on the document."""
        payload = {"director_remark": remark}
        data = api_client.put(Endpoints.DIRECTOR_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Director returns reviewed document back to DS."""
        payload = {"remarks": remarks}
        data = api_client.post(Endpoints.DOCUMENT_RETURN_TO_DS(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        """HOD saves or updates department remarks on the document."""
        payload = {"hod_remark": remark}
        data = api_client.put(Endpoints.HOD_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """DS forwards employee progress update to Director as follow-up."""
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
        """
        HOD delegates work on a document to an employee.
        Sends backend expected assigned_to_user_id field.
        """
        payload = {
            "assigned_to_user_id": assigned_to_id,
            "instructions": instructions
        }
        data = api_client.post(Endpoints.DOCUMENT_ASSIGN(document_id), json=payload)
        return WorkAssignmentModel.from_dict(data)

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        """Retrieves assignment records for a document."""
        try:
            data = api_client.get(Endpoints.DOCUMENT_ASSIGN(document_id))
            return [WorkAssignmentModel.from_dict(a) for a in data]
        except Exception:
            return []

    # =========================================================
    # PROGRESS & ATTACHMENTS (Employee Reporting)
    # =========================================================

    def submit_progress(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        """
        Employee submits a progress update.
        Creates progress record via JSON, then uploads attachment if provided.
        """
        payload = {"description": description}
        data = api_client.post(Endpoints.PROGRESS_CREATE(document_id), json=payload)
        prog = ProgressUpdateModel.from_dict(data)

        if attachment_file_path:
            att = self.upload_attachment(
                document_id=document_id,
                file_path=attachment_file_path,
                progress_update_id=prog.id,
                category="WORKFLOW"
            )
            prog.attachments.append(att)

        return prog

    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        """Retrieves chronological progress updates for a document."""
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
        """
        Uploads a file attachment. Translates frontend category into backend
        expected attachment_type enum string.
        """
        if progress_update_id:
            att_type = "PROGRESS_ATTACHMENT"
        elif category == "ORIGINAL":
            att_type = "ORIGINAL"
        else:
            att_type = "SUPPORTING_DOCUMENT"

        extra_data: Dict[str, Any] = {"attachment_type": att_type}
        if progress_update_id:
            extra_data["progress_update_id"] = str(progress_update_id)

        data = api_client.upload(
            Endpoints.ATTACHMENT_UPLOAD(document_id),
            file_path_or_tuple=file_path,
            field_name="file",
            extra_data=extra_data
        )
        return AttachmentModel.from_dict(data)

    def get_attachments(self, document_id: int, category: Optional[str] = None) -> List[AttachmentModel]:
        """Retrieves all attachments associated with a document."""
        data = api_client.get(Endpoints.ATTACHMENT_LIST(document_id))
        attachments = [AttachmentModel.from_dict(a) for a in data]
        if category:
            cat_upper = category.upper()
            attachments = [a for a in attachments if (a.category or "").upper() == cat_upper]
        return attachments

    # =========================================================
    # WORKFLOW HISTORY & AUDIT
    # =========================================================

    def get_workflow_history(self, document_id: int) -> List[WorkflowEventModel]:
        """Retrieves chronological workflow events for a specific document."""
        data = api_client.get(Endpoints.DOCUMENT_HISTORY(document_id))
        return [WorkflowEventModel.from_dict(e) for e in data]

    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        """
        Retrieves system-wide activity history by aggregating document-level
        histories. Provides safe client-side aggregation without inventing endpoints.
        """
        docs = self.get_documents()
        all_events: List[WorkflowEventModel] = []
        for doc in docs:
            if doc.id:
                try:
                    events = self.get_workflow_history(doc.id)
                    all_events.extend(events)
                except Exception:
                    pass

        # Apply filtering
        if user and user != "All Users":
            u_lower = user.lower()
            all_events = [e for e in all_events if u_lower in (e.user or "").lower()]
        if action and action != "All Actions":
            a_lower = action.lower()
            all_events = [e for e in all_events if a_lower in (e.action or "").lower()]

        # Sort by timestamp descending
        all_events.sort(key=lambda e: str(e.timestamp or ""), reverse=True)
        return all_events

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        """Retrieves notification list for active user."""
        endpoint = Endpoints.NOTIFICATIONS_UNREAD if unread_only else Endpoints.NOTIFICATIONS_LIST
        data = api_client.get(endpoint)
        return [NotificationModel.from_dict(n) for n in data]

    def mark_notification_read(self, notification_id: int) -> bool:
        """Marks specific notification as read."""
        try:
            api_client.patch(Endpoints.NOTIFICATION_MARK_READ(notification_id))
            return True
        except Exception:
            return False

    # =========================================================
    # DASHBOARD
    # =========================================================

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves role-specific dashboard metrics."""
        return api_client.get(Endpoints.DASHBOARD_STATS)

    # =========================================================
    # OCR & ROUTING INTELLIGENCE
    # =========================================================

    def get_ocr_result(self, document_id: int) -> Dict[str, Any]:
        """
        Returns the OCR record for a document including:
          - ocr_status, ocr_engine, confidence, extracted_text
          - extracted_fields (list of {field_name, extracted_value, confidence})
        """
        try:
            return api_client.get(Endpoints.OCR_GET(document_id)) or {}
        except Exception:
            return {}

    def trigger_ocr(self, document_id: int) -> Dict[str, Any]:
        """
        Asks the backend to run real PaddleOCR on the stored document file.
        Called after a document is created via the intake pipeline.
        """
        try:
            return api_client.post(Endpoints.OCR_PROCESS(document_id), json={}) or {}
        except Exception:
            return {}

    def get_routing_suggestion(self, document_id: int) -> Dict[str, Any]:
        """
        Fetches the advisory routing suggestion persisted in the database.
        Returns a dict with: suggested_department_name, suggested_employee_name,
        routing_confidence (0.0–1.0), routing_reason, is_director_instruction.
        """
        try:
            return api_client.get(Endpoints.ROUTING_SUGGESTION(document_id)) or {}
        except Exception:
            return {}

    def analyze_routing(self, document_id: int) -> Dict[str, Any]:
        """
        Triggers fresh routing analysis for a document (uses OCR text +
        Director remark if present).  Returns same structure as get_routing_suggestion.
        """
        try:
            return api_client.post(
                Endpoints.ROUTING_ANALYZE(document_id),
                json={"include_director_remark": True}
            ) or {}
        except Exception:
            return {}
