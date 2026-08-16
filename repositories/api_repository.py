import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from api.client import api_client
from api.endpoints import Endpoints
from models.attachment import AttachmentModel
from models.document import DocumentModel
from models.document_route import DocumentRouteModel
from models.enums import (
    DocumentStatusEnum,
    IngestionModeEnum,
    PriorityEnum,
    RoleEnum,
    RouteTypeEnum,
    WorkflowStageEnum,
)
from models.notification import NotificationModel
from models.progress_update import ProgressUpdateModel
from models.user import UserModel
from models.work_assignment import WorkAssignmentModel
from models.workflow_event import WorkflowEventModel
from repositories.base import BaseRepository


class APIRepository(BaseRepository):
    """
    Production repository implementation communicating with the live FastAPI V2 backend via APIClient.
    Translates frontend domain models and service calls into REST API requests against centralized Endpoints.
    """

    def __init__(self):
        self._current_user: Optional[UserModel] = None
        self._departments_cache: Dict[int, str] = {}
        self._users_cache: Dict[int, str] = {}
        self._doc_versions: Dict[int, int] = {}  # doc_id -> version for optimistic concurrency

    # =========================================================
    # ENUM & FIELD NORMALIZATION HELPERS
    # =========================================================

    @staticmethod
    def _role_to_frontend(role_str: Optional[str]) -> str:
        if not role_str:
            return RoleEnum.DIRECTOR_SECRETARY.value
        r = role_str.strip().upper()
        mapping = {
            "DS": RoleEnum.DIRECTOR_SECRETARY.value,
            "DIRECTOR": RoleEnum.DIRECTOR.value,
            "HOD": RoleEnum.HOD.value,
            "EMPLOYEE": RoleEnum.EMPLOYEE.value,
            "ADMINISTRATOR": RoleEnum.ADMINISTRATOR.value,
            "READ_ONLY": RoleEnum.READ_ONLY.value,
        }
        return mapping.get(r, RoleEnum.normalize(role_str))

    @staticmethod
    def _role_to_backend(role_str: Optional[str]) -> str:
        if not role_str:
            return "DS"
        s = role_str.strip().lower()
        if s in ("ds", "master", "director secretary"):
            return "DS"
        if s in ("director",):
            return "DIRECTOR"
        if s in ("hod",):
            return "HOD"
        if s in ("employee",):
            return "EMPLOYEE"
        return role_str.upper()

    @staticmethod
    def _status_to_frontend(status_str: Optional[str]) -> str:
        if not status_str:
            return DocumentStatusEnum.RECEIVED.value
        s = status_str.strip().upper()
        mapping = {
            "RECEIVED": DocumentStatusEnum.RECEIVED.value,
            "UNDER_DIRECTOR_REVIEW": DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value,
            "DIRECTOR_REVIEW_COMPLETED": DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
            "UNDER_HOD_PROCESSING": DocumentStatusEnum.UNDER_HOD_PROCESSING.value,
            "ASSIGNED_FOR_EXECUTION": DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value,
            "IN_PROGRESS": DocumentStatusEnum.IN_PROGRESS.value,
            "PROGRESS_UPDATED": DocumentStatusEnum.PROGRESS_UPDATED.value,
            "REVIEW_COMPLETED": DocumentStatusEnum.REVIEW_COMPLETED.value,
            "CLOSED": DocumentStatusEnum.CLOSED.value,
        }
        return mapping.get(s, status_str.title())

    @staticmethod
    def _status_to_backend(status_str: Optional[str]) -> str:
        if not status_str:
            return "RECEIVED"
        s = status_str.strip()
        mapping = {
            DocumentStatusEnum.RECEIVED.value: "RECEIVED",
            DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value: "UNDER_DIRECTOR_REVIEW",
            DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value: "DIRECTOR_REVIEW_COMPLETED",
            DocumentStatusEnum.UNDER_HOD_PROCESSING.value: "UNDER_HOD_PROCESSING",
            DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value: "ASSIGNED_FOR_EXECUTION",
            DocumentStatusEnum.IN_PROGRESS.value: "IN_PROGRESS",
            DocumentStatusEnum.PROGRESS_UPDATED.value: "PROGRESS_UPDATED",
            DocumentStatusEnum.PROGRESS_FOLLOWUP_UNDER_REVIEW.value: "PROGRESS_UPDATED",
            DocumentStatusEnum.REVIEW_COMPLETED.value: "REVIEW_COMPLETED",
            DocumentStatusEnum.CLOSED.value: "CLOSED",
        }
        return mapping.get(s, s.replace(" ", "_").upper())

    @staticmethod
    def _priority_to_frontend(p_str: Optional[str]) -> str:
        if not p_str:
            return PriorityEnum.MEDIUM.value
        p = p_str.strip().upper()
        if p in ("HIGH", "RED"):
            return PriorityEnum.HIGH.value
        if p in ("LOW", "GREEN"):
            return PriorityEnum.LOW.value
        return PriorityEnum.MEDIUM.value

    @staticmethod
    def _priority_to_backend(p_str: Optional[str]) -> str:
        norm = PriorityEnum.normalize(p_str or "Medium")
        return norm.upper()

    @staticmethod
    def _route_type_to_backend(rt_str: Optional[str]) -> str:
        if not rt_str:
            return "INITIAL_DIRECTOR_REVIEW"
        mapping = {
            RouteTypeEnum.DS_TO_DIRECTOR.value: "INITIAL_DIRECTOR_REVIEW",
            RouteTypeEnum.DIRECTOR_TO_DS.value: "RETURN_TO_DS",
            RouteTypeEnum.DS_TO_HOD.value: "POST_REVIEW_TO_HOD",
            RouteTypeEnum.DS_TO_EMPLOYEE.value: "POST_REVIEW_TO_EMPLOYEE",
            RouteTypeEnum.DS_TO_DIRECTOR_FOLLOWUP.value: "FOLLOW_UP_TO_DIRECTOR",
            "DS_TO_DIRECTOR": "INITIAL_DIRECTOR_REVIEW",
            "DIRECTOR_TO_DS": "RETURN_TO_DS",
            "DS_TO_HOD": "POST_REVIEW_TO_HOD",
            "DS_TO_EMPLOYEE": "POST_REVIEW_TO_EMPLOYEE",
            "DS_TO_DIRECTOR_FOLLOWUP": "FOLLOW_UP_TO_DIRECTOR",
        }
        return mapping.get(rt_str, rt_str)

    # =========================================================
    # CACHE & METADATA HELPERS
    # =========================================================

    def _ensure_departments_cache(self) -> None:
        if not self._departments_cache:
            try:
                depts = api_client.get(Endpoints.DEPARTMENTS_LIST)
                if isinstance(depts, list):
                    for d in depts:
                        self._departments_cache[d["id"]] = d["name"]
            except Exception:
                pass

    def _ensure_users_cache(self) -> None:
        if not self._users_cache:
            try:
                users = api_client.get(Endpoints.USERS_LIST)
                if isinstance(users, list):
                    for u in users:
                        self._users_cache[u["id"]] = u.get("full_name") or u.get("username")
            except Exception:
                pass

    def _resolve_department_name(self, dept_id: Optional[int]) -> Optional[str]:
        if not dept_id:
            return None
        self._ensure_departments_cache()
        return self._departments_cache.get(dept_id, f"Department {dept_id}")

    def _resolve_user_name(self, user_id: Optional[int]) -> Optional[str]:
        if not user_id:
            return None
        self._ensure_users_cache()
        return self._users_cache.get(user_id, f"User {user_id}")

    # =========================================================
    # MODEL CONVERSION
    # =========================================================

    def _map_doc_from_backend(self, d: Dict[str, Any], fetch_enrichments: bool = False) -> DocumentModel:
        doc_id = d.get("doc_id") or d.get("id")
        version = d.get("version", 1)
        if doc_id:
            self._doc_versions[doc_id] = version

        # Resolve department and employee names
        target_dept_id = d.get("target_department_id")
        target_dept_name = d.get("target_department_name") or self._resolve_department_name(target_dept_id)

        # Dates as ISO string
        received_date = d.get("received_date") or d.get("date")
        if isinstance(received_date, (date, datetime)):
            received_date = received_date.strftime("%Y-%m-%d")

        deadline = d.get("deadline")
        if isinstance(deadline, (date, datetime)):
            deadline = deadline.strftime("%Y-%m-%d")

        # Basic DocumentModel instance
        doc = DocumentModel(
            id=doc_id,
            reference_no=d.get("reference_no") or d.get("reference"),
            title=d.get("title") or d.get("subject", ""),
            date=received_date,
            mode=d.get("mode") or "Manual Upload",
            source=d.get("source"),
            priority=self._priority_to_frontend(d.get("priority")),
            deadline=deadline,
            status=self._status_to_frontend(d.get("status")),
            current_stage=d.get("current_stage") or "DS",
            director_remark=d.get("director_remark"),
            hod_remark=d.get("hod_remark"),
            current_owner_id=d.get("current_owner_id"),
            current_owner_name=self._resolve_user_name(d.get("current_owner_id")),
            target_department_id=target_dept_id,
            target_department_name=target_dept_name,
            created_by=d.get("created_by"),
            created_at=str(d.get("created_at")) if d.get("created_at") else None,
            updated_at=str(d.get("updated_at")) if d.get("updated_at") else None,
            version=version,
        )

        # Detailed enrichments (Routing suggestions, assignments, OCR)
        if fetch_enrichments and doc_id:
            try:
                # 1. Fetch Routing Suggestion
                sugg = api_client.get(Endpoints.DOCUMENT_ROUTING_SUGGESTION(doc_id))
                if isinstance(sugg, dict):
                    doc.suggested_department_id = sugg.get("suggested_department_id")
                    doc.suggested_department_name = sugg.get("suggested_department_name") or self._resolve_department_name(doc.suggested_department_id)
                    doc.suggested_employee_id = sugg.get("suggested_employee_id")
                    doc.suggested_employee_name = sugg.get("suggested_employee_name") or self._resolve_user_name(doc.suggested_employee_id)
                    doc.has_director_routing_instruction = bool(sugg.get("is_director_instruction", False))
                    confidence = sugg.get("routing_confidence") or 0.0
                    doc.routing_instruction_confidence = int(confidence * 100) if confidence <= 1.0 else int(confidence)
                    doc.director_routing_raw_text = sugg.get("routing_reason")
            except Exception:
                pass

            try:
                # 2. Fetch OCR text if available
                ocr_data = api_client.get(Endpoints.DOCUMENT_OCR(doc_id))
                if isinstance(ocr_data, dict):
                    doc.ocr_text = ocr_data.get("extracted_text")
            except Exception:
                pass

            try:
                # 3. Check active assignment
                assignments = api_client.get(Endpoints.DOCUMENT_ASSIGN(doc_id))
                if isinstance(assignments, list) and assignments:
                    active = next((a for a in assignments if a.get("is_active", True)), assignments[0])
                    doc.assigned_employee_id = active.get("assigned_to_user_id") or active.get("assigned_to_id")
                    doc.assigned_employee_name = self._resolve_user_name(doc.assigned_employee_id)
            except Exception:
                pass

        return doc

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        payload = {"username": username, "password": password}
        response = api_client.post(Endpoints.AUTH_LOGIN, json=payload)

        token = response.get("access_token")
        if token:
            api_client.set_auth_token(token)

        user_data = response.get("user")
        if not user_data:
            user_data = api_client.get(Endpoints.AUTH_ME)

        if user_data:
            user_data["role"] = self._role_to_frontend(user_data.get("role"))
            self._current_user = UserModel.from_dict(user_data)
            if self._current_user.id:
                self._users_cache[self._current_user.id] = self._current_user.full_name
            return self._current_user
        return None

    def get_current_user(self) -> Optional[UserModel]:
        if not self._current_user:
            try:
                user_data = api_client.get(Endpoints.AUTH_ME)
                if user_data:
                    user_data["role"] = self._role_to_frontend(user_data.get("role"))
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
            params["role"] = self._role_to_backend(role)
        if department_id:
            params["department_id"] = department_id
        try:
            data = api_client.get(Endpoints.USERS_LIST, params=params)
            users = []
            for u in data:
                u_copy = dict(u)
                u_copy["role"] = self._role_to_frontend(u_copy.get("role"))
                user_obj = UserModel.from_dict(u_copy)
                self._users_cache[user_obj.id] = user_obj.full_name
                users.append(user_obj)
            return users
        except Exception:
            return []

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    def get_inbox(self) -> List[DocumentModel]:
        """
        Retrieves role-scoped inbox queue from backend.
        DS receives intake items; Director, HOD, and Employee receive stage-filtered items.
        """
        data = api_client.get(Endpoints.DOCUMENTS_INBOX)
        return [self._map_doc_from_backend(d, fetch_enrichments=False) for d in data]

    def add_inbox_item(self, document: DocumentModel) -> DocumentModel:
        """Adds a raw intake message or document into the intake queue."""
        created = self.create_document(document, file_path=document.file_path)
        return created

    def remove_inbox_item(self, item_id: int) -> bool:
        return True

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        data = api_client.get(Endpoints.DOCUMENTS_LIST)
        docs = [self._map_doc_from_backend(d, fetch_enrichments=False) for d in data]

        # Apply client-side filters if backend returned full list
        filtered = docs
        if status and status != "All Status":
            filtered = [d for d in filtered if d.status.lower() == status.lower()]
        if department and department != "All Departments":
            filtered = [d for d in filtered if (d.target_department_name or "").lower() == department.lower()]
        if source and source != "All Sources":
            filtered = [d for d in filtered if (d.source or "").lower() == source.lower()]
        if search:
            q = search.lower()
            filtered = [
                d for d in filtered
                if q in (d.title or "").lower()
                or q in (d.reference_no or "").lower()
                or q in (d.source or "").lower()
            ]

        return filtered

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        try:
            data = api_client.get(Endpoints.DOCUMENT_DETAIL(document_id))
            if data:
                return self._map_doc_from_backend(data, fetch_enrichments=True)
            return None
        except Exception:
            return None

    def create_document(self, document: DocumentModel, file_path: Optional[str] = None) -> DocumentModel:
        today_str = date.today().strftime("%Y-%m-%d")
        rec_date = document.date or today_str
        priority_backend = self._priority_to_backend(document.priority)

        if file_path and os.path.exists(file_path):
            # Use multipart manual intake upload
            extra_data = {
                "title": document.title,
                "received_date": rec_date,
                "mode": document.mode or "Manual Upload",
                "priority": priority_backend,
                "description": document.remarks or "",
                "source": document.source or "Manual Intake",
            }
            data = api_client.upload(
                Endpoints.INTAKE_MANUAL_UPLOAD,
                file_path_or_tuple=file_path,
                field_name="file",
                extra_data=extra_data
            )
        else:
            payload = {
                "title": document.title,
                "description": document.remarks,
                "received_date": rec_date,
                "deadline": document.deadline,
                "source": document.source,
                "mode": document.mode or "Manual Upload",
                "priority": priority_backend,
            }
            data = api_client.post(Endpoints.DOCUMENT_CREATE, json=payload)

        return self._map_doc_from_backend(data, fetch_enrichments=True)

    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {
            "remarks": remarks,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.post(Endpoints.DOCUMENT_CLOSE(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

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
        backend_route_type = self._route_type_to_backend(route_type)
        payload = {
            "route_type": backend_route_type,
            "to_user_id": to_user_id,
            "to_department_id": to_department_id,
            "remarks": remarks,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.post(Endpoints.DOCUMENT_ROUTE(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        payload = {
            "director_remark": remark,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.put(Endpoints.DIRECTOR_REMARK(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {
            "remarks": remarks,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.post(Endpoints.DOCUMENT_RETURN_TO_DS(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        payload = {
            "hod_remark": remark,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.put(Endpoints.HOD_REMARK(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        payload = {
            "remarks": remarks,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.post(Endpoints.DOCUMENT_FOLLOW_UP(document_id), json=payload)
        return self._map_doc_from_backend(data, fetch_enrichments=True)

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
            "assigned_to_user_id": assigned_to_id,
            "instructions": instructions,
            "expected_version": self._doc_versions.get(document_id)
        }
        data = api_client.post(Endpoints.DOCUMENT_ASSIGN(document_id), json=payload)
        return WorkAssignmentModel(
            id=data.get("id"),
            document_id=data.get("document_id"),
            assigned_by_id=data.get("assigned_by_user_id"),
            assigned_to_id=data.get("assigned_to_user_id"),
            assigned_to_name=self._resolve_user_name(data.get("assigned_to_user_id")),
            instructions=data.get("instructions"),
            is_active=data.get("is_active", True),
            created_at=str(data.get("assigned_at")) if data.get("assigned_at") else None,
        )

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
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
        payload = {"description": description}
        data = api_client.post(Endpoints.PROGRESS_CREATE(document_id), json=payload)

        progress_obj = ProgressUpdateModel(
            id=data.get("id"),
            document_id=data.get("document_id"),
            employee_id=data.get("submitted_by_user_id"),
            employee_name=self._resolve_user_name(data.get("submitted_by_user_id")),
            description=data.get("description", ""),
            timestamp=str(data.get("created_at")) if data.get("created_at") else None,
        )

        if attachment_file_path and os.path.exists(attachment_file_path):
            self.upload_attachment(
                document_id=document_id,
                file_path=attachment_file_path,
                progress_update_id=progress_obj.id,
                category="WORKFLOW"
            )

        return progress_obj

    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        try:
            data = api_client.get(Endpoints.PROGRESS_LIST(document_id))
            updates = []
            for p in data:
                updates.append(ProgressUpdateModel(
                    id=p.get("id"),
                    document_id=p.get("document_id"),
                    employee_id=p.get("submitted_by_user_id"),
                    employee_name=self._resolve_user_name(p.get("submitted_by_user_id")),
                    description=p.get("description", ""),
                    timestamp=str(p.get("created_at")) if p.get("created_at") else None,
                ))
            return updates
        except Exception:
            return []

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = "WORKFLOW",
        source: Optional[str] = None
    ) -> AttachmentModel:
        extra_data = {
            "attachment_type": "PROGRESS_ATTACHMENT" if progress_update_id else "SUPPORTING_DOCUMENT"
        }
        if progress_update_id:
            extra_data["progress_update_id"] = str(progress_update_id)

        data = api_client.upload(
            Endpoints.ATTACHMENT_UPLOAD(document_id),
            file_path_or_tuple=file_path,
            field_name="file",
            extra_data=extra_data
        )

        uploader_id = data.get("uploaded_by_user_id") or data.get("uploaded_by") or 0
        return AttachmentModel(
            id=data.get("id"),
            document_id=data.get("document_id"),
            progress_update_id=data.get("progress_update_id"),
            uploaded_by=uploader_id,
            uploaded_by_name=self._resolve_user_name(uploader_id),
            file_name=data.get("file_name", ""),
            file_path=data.get("storage_key"),
            file_type=data.get("file_type"),
            file_size=data.get("file_size"),
            category="WORKFLOW" if data.get("progress_update_id") else "ORIGINAL",
            created_at=str(data.get("created_at")) if data.get("created_at") else None,
        )

    def get_attachments(self, document_id: int, category: Optional[str] = None) -> List[AttachmentModel]:
        try:
            data = api_client.get(Endpoints.ATTACHMENT_LIST(document_id))
            attachments = []
            for a in data:
                cat = "WORKFLOW" if a.get("progress_update_id") else "ORIGINAL"
                if category and cat.upper() != category.upper():
                    continue
                u_id = a.get("uploaded_by_user_id") or a.get("uploaded_by") or 0
                attachments.append(AttachmentModel(
                    id=a.get("id"),
                    document_id=a.get("document_id"),
                    progress_update_id=a.get("progress_update_id"),
                    uploaded_by=u_id,
                    uploaded_by_name=self._resolve_user_name(u_id),
                    file_name=a.get("file_name", ""),
                    file_path=a.get("storage_key"),
                    file_type=a.get("file_type"),
                    file_size=a.get("file_size"),
                    category=cat,
                    created_at=str(a.get("created_at")) if a.get("created_at") else None,
                ))
            return attachments
        except Exception:
            return []

    # =========================================================
    # WORKFLOW HISTORY & AUDIT
    # =========================================================

    def get_workflow_history(self, document_id: int) -> List[WorkflowEventModel]:
        try:
            data = api_client.get(Endpoints.DOCUMENT_HISTORY(document_id))
            events = []
            for e in data:
                events.append(WorkflowEventModel(
                    id=e.get("id"),
                    document_id=e.get("document_id"),
                    action=e.get("action", ""),
                    user_id=e.get("performed_by_user_id"),
                    user_name=self._resolve_user_name(e.get("performed_by_user_id")),
                    from_role=self._role_to_frontend(e.get("from_role")) if e.get("from_role") else None,
                    to_role=self._role_to_frontend(e.get("to_role")) if e.get("to_role") else None,
                    remarks=e.get("details"),
                    timestamp=str(e.get("created_at")) if e.get("created_at") else None,
                ))
            return events
        except Exception:
            return []

    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        try:
            docs = self.get_documents()
            all_events = []
            for d in docs[:20]:
                if d.id:
                    all_events.extend(self.get_workflow_history(d.id))

            if user and user != "All Users":
                all_events = [e for e in all_events if (e.user_name or "").lower() == user.lower()]
            if action and action != "All Actions":
                all_events = [e for e in all_events if (e.action or "").lower() == action.lower()]

            return all_events
        except Exception:
            return []

    # =========================================================
    # NOTIFICATIONS & REMINDERS
    # =========================================================

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        endpoint = Endpoints.NOTIFICATIONS_UNREAD if unread_only else Endpoints.NOTIFICATIONS_LIST
        try:
            data = api_client.get(endpoint)
            return [
                NotificationModel(
                    id=n.get("id"),
                    user_id=n.get("user_id"),
                    document_id=n.get("document_id"),
                    title=n.get("title", ""),
                    message=n.get("message", ""),
                    is_read=n.get("is_read", False),
                    created_at=str(n.get("created_at")) if n.get("created_at") else None,
                )
                for n in data
            ]
        except Exception:
            return []

    def mark_notification_read(self, notification_id: int) -> bool:
        try:
            api_client.patch(Endpoints.NOTIFICATION_MARK_READ(notification_id))
            return True
        except Exception:
            return False

    # =========================================================
    # DASHBOARD
    # =========================================================

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        try:
            data = api_client.get(Endpoints.DASHBOARD_STATS)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
