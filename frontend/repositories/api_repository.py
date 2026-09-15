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

    # Canonical routing types.
    #
    # Operational routing is represented by DocumentDepartmentRouting
    # branches. Director review/return/follow-up are separate workflow
    # actions and use their dedicated endpoints below.
    ROUTE_TYPE_MAP = {
        RouteTypeEnum.DEPARTMENT_HOD.value: RouteTypeEnum.DEPARTMENT_HOD.value,
        RouteTypeEnum.DIRECT_EMPLOYEE.value: RouteTypeEnum.DIRECT_EMPLOYEE.value,
        RouteTypeEnum.TSO.value: RouteTypeEnum.TSO.value,
        "DS_TO_DIRECTOR": "INITIAL_DIRECTOR_REVIEW",
        "DIRECTOR_TO_DS": "RETURN_TO_DS",
        "DS_TO_HOD": "POST_REVIEW_TO_HOD",
        "DS_TO_EMPLOYEE": "POST_REVIEW_TO_EMPLOYEE",
        "DS_TO_DIRECTOR_FOLLOWUP": "FOLLOW_UP_TO_DIRECTOR",
    }

    def __init__(self):
        self._current_user: Optional[UserModel] = None

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        """
        Authenticate against the real backend and preserve the complete
        context membership collection returned by the backend.

        This is important because ContextManager/AuthService use the
        authenticated UserModel as the source for the workspace selector.
        A profile-only /auth/me response must not discard the memberships
        returned by /auth/login or /auth/contexts.
        """
        payload = {"username": username.strip(), "password": password}

        try:
            response = api_client.post(Endpoints.AUTH_LOGIN, json=payload) or {}
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

        if not user_data:
            return None

        # The backend may provide memberships directly in the login response,
        # or under /auth/me as context_memberships.
        active_context_id = (
            response.get("active_context_id")
            or response.get("active_context_membership_id")
            or user_data.get("active_context_id")
            or user_data.get("active_context_membership_id")
        )

        contexts = (
            response.get("contexts")
            or response.get("context_memberships")
            or user_data.get("contexts")
            or user_data.get("context_memberships")
            or []
        )

        # If login did not include memberships, explicitly retrieve the real
        # backend context collection. Never manufacture contexts locally.
        if not contexts and token:
            try:
                contexts = self.get_user_contexts()
            except Exception:
                contexts = []

        if contexts:
            user_data["context_memberships"] = contexts

        if active_context_id is None and contexts:
            active = next(
                (
                    c for c in contexts
                    if c.get("is_active") is True
                    or c.get("active") is True
                ),
                None,
            )
            if active:
                active_context_id = active.get("id")

        if active_context_id is not None:
            user_data["active_context_id"] = active_context_id
            user_data["active_context_membership_id"] = active_context_id
            api_client.set_active_context_id(int(active_context_id))

        self._current_user = UserModel.from_dict(user_data)
        return self._current_user

    def get_current_user(self) -> Optional[UserModel]:
        """
        Return the authenticated user while preserving the complete context
        membership state used by the workspace selector.
        """
        if not self._current_user and api_client._auth_token:
            try:
                user_data = api_client.get(Endpoints.AUTH_ME)
                if not user_data:
                    return None

                contexts = (
                    user_data.get("context_memberships")
                    or user_data.get("contexts")
                    or []
                )

                # /auth/me may return no memberships in some backend versions.
                if not contexts:
                    try:
                        contexts = api_client.get(Endpoints.AUTH_CONTEXTS) or []
                    except Exception:
                        contexts = []

                if contexts:
                    user_data["context_memberships"] = contexts

                active_id = (
                    user_data.get("active_context_id")
                    or user_data.get("active_context_membership_id")
                    or api_client.get_active_context_id()
                )

                if active_id is None and contexts:
                    # Prefer the backend-marked active membership; otherwise
                    # leave selection to ContextManager.
                    active = next(
                        (
                            c for c in contexts
                            if c.get("is_active") is True
                            or c.get("active") is True
                        ),
                        None,
                    )
                    if active:
                        active_id = active.get("id")

                if active_id is not None:
                    user_data["active_context_id"] = active_id
                    user_data["active_context_membership_id"] = active_id
                    api_client.set_active_context_id(int(active_id))

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

    def get_user_contexts(self) -> List[Dict[str, Any]]:
        """Retrieves all active work context memberships for the current user."""
        try:
            contexts = api_client.get(Endpoints.AUTH_CONTEXTS) or []
            if self._current_user is not None:
                self._current_user.set_contexts(contexts)
            return contexts
        except Exception:
            return []

    def switch_context(self, context_membership_id: int) -> Dict[str, Any]:
        """
        Switches the active operational context.

        The backend validates the membership. The client then places the
        selected membership ID in X-Work-Context-Id for subsequent requests.
        """
        payload = {"context_membership_id": int(context_membership_id)}
        result = api_client.post(Endpoints.AUTH_SWITCH_CONTEXT, json=payload) or {}

        selected_id = result.get("id") or context_membership_id
        api_client.set_active_context_id(int(selected_id))

        if self._current_user is not None:
            self._current_user.set_active_context(int(selected_id))
            contexts = self._current_user.get_contexts()
            for context in contexts:
                context.is_active = (context.id == int(selected_id))

        return result

    def get_active_context_id(self) -> Optional[int]:
        """Return the membership ID currently attached to API requests."""
        return api_client.get_active_context_id()

    def clear_active_context(self) -> None:
        """Clear only the client-side active context."""
        api_client.set_active_context_id(None)

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

    def get_users(
        self,
        role: Optional[str] = None,
        department_id: Optional[int] = None
    ) -> List[UserModel]:
        """
        Retrieve users from the backend.

        `role` is treated as a compatibility filter for callers that still use
        the repository's role argument. When context memberships are present,
        their context types are also considered so a person such as a TSO who
        additionally has an EMPLOYEE context is not incorrectly excluded.

        Department filtering remains a user/employee lookup filter; operational
        document authorization is always enforced by the backend.
        """
        users: List[UserModel] = []
        raw_users: List[Dict[str, Any]] = []

        try:
            data = api_client.get(Endpoints.USERS_LIST) or []
            raw_users = data if isinstance(data, list) else []
            users = [UserModel.from_dict(u) for u in raw_users]
        except Exception:
            target_dept = department_id
            if target_dept is None and self._current_user is not None:
                target_dept = getattr(self._current_user, "department_id", None)

            if target_dept is not None:
                try:
                    data = api_client.get(
                        Endpoints.DEPARTMENT_EMPLOYEES(target_dept)
                    ) or []
                    raw_users = data if isinstance(data, list) else []
                    users = [
                        UserModel(
                            id=emp.get("user_id") or emp.get("id"),
                            username=emp.get(
                                "employee_code",
                                f"emp_{emp.get('id')}"
                            ),
                            full_name=emp.get("full_name", ""),
                            role="Employee",
                            department_id=emp.get("department_id"),
                            department_name=emp.get("department_name"),
                            is_active=emp.get("is_active", True),
                        )
                        for emp in raw_users
                    ]
                except Exception:
                    users = []
                    raw_users = []

        # Fill department names from the authoritative department endpoint
        # only when the user payload did not already contain one.
        try:
            depts = {
                d.id: d.name
                for d in self.get_departments()
            }
            for u in users:
                uid = getattr(u, "department_id", None)
                if uid and not getattr(u, "department_name", None):
                    u.department_name = depts.get(uid, "General")
        except Exception:
            pass

        if role:
            normalized_target = RoleEnum.normalize(role).lower()

            filtered: List[UserModel] = []
            for index, user in enumerate(users):
                base_role = str(
                    getattr(user, "role", "") or ""
                ).lower()

                matches = base_role == normalized_target

                # Context membership data can establish an operational role
                # independently of the persisted base User.role.
                raw = raw_users[index] if index < len(raw_users) else {}
                memberships = (
                    raw.get("context_memberships")
                    or raw.get("contexts")
                    or []
                )

                if not matches:
                    for membership in memberships:
                        context_type = str(
                            membership.get("context_type")
                            or membership.get("type")
                            or membership.get("role")
                            or ""
                        ).lower()
                        if RoleEnum.normalize(context_type).lower() == normalized_target:
                            matches = True
                            break

                if matches:
                    filtered.append(user)

            users = filtered

        if department_id is not None:
            users = [
                u for u in users
                if getattr(u, "department_id", None) == department_id
            ]

        return users

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    def get_inbox(self) -> List[DocumentModel]:
        """
        Retrieve the document inbox for the active operational context.

        DS intake items are intentionally not mixed into the generic document
        inbox. Call get_intake_items() for the Outlook/intake queue.
        """
        data = api_client.get(Endpoints.DOCUMENTS_INBOX) or []
        return [DocumentModel.from_dict(d) for d in data]

    def get_intake_items(self) -> List[Dict[str, Any]]:
        """Retrieves raw incoming intake items from /intake."""
        try:
            return api_client.get(Endpoints.INTAKE_LIST) or []
        except Exception:
            return []

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
            docs = [
                d for d in docs
                if (getattr(d, "status", None) or "").lower() == status.lower()
            ]
        def _document_department_text(doc: DocumentModel) -> str:
            # Document-level department is no longer an operational routing
            # source of truth. These advisory fields are safe for display/filter
            # when supplied by the backend.
            suggested = getattr(doc, "suggested_department_name", None)
            if suggested:
                return str(suggested)

            routings = (
                getattr(doc, "department_routings", None)
                or getattr(doc, "routing_branches", None)
                or getattr(doc, "branches", None)
                or []
            )
            names: List[str] = []
            for branch in routings:
                if isinstance(branch, dict):
                    name = (
                        branch.get("target_department_name")
                        or branch.get("department_name")
                    )
                else:
                    name = (
                        getattr(branch, "target_department_name", None)
                        or getattr(branch, "department_name", None)
                    )
                if name and str(name) not in names:
                    names.append(str(name))
            return ", ".join(names)

        if department and department != "All Departments":
            target = department.lower()
            docs = [
                d for d in docs
                if target in _document_department_text(d).lower()
            ]

        if source and source != "All Sources":
            docs = [
                d for d in docs
                if (getattr(d, "source", None) or "").lower()
                == source.lower()
            ]

        if search:
            q = search.lower().strip()
            docs = [
                d for d in docs
                if q in (getattr(d, "title", None) or "").lower()
                or q in (getattr(d, "reference", None) or "").lower()
                or q in (getattr(d, "source", None) or "").lower()
                or q in _document_department_text(d).lower()
                or q in (getattr(d, "suggested_employee_name", None) or "").lower()
            ]

        return docs

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Retrieves single canonical document by ID."""
        data = api_client.get(Endpoints.DOCUMENT_DETAIL(document_id))
        return DocumentModel.from_dict(data) if data else None

    def create_document(
        self,
        document: DocumentModel,
        file_path: Optional[str] = None
    ) -> DocumentModel:
        """
        Create a canonical document through the live backend.

        If file_path is supplied, use the DS manual-intake multipart endpoint.
        Otherwise use the canonical JSON /documents endpoint.

        Routing fields here are advisory suggestions only. Operational routing
        is created separately through the canonical branch endpoints.
        """
        raw_date = (
            str(getattr(document, "date", "")).split()[0]
            if getattr(document, "date", None)
            else datetime.now().strftime("%Y-%m-%d")
        )
        priority_val = PriorityEnum.normalize(
            getattr(document, "priority", None)
        ).upper()

        if file_path:
            form_data = {
                "title": getattr(document, "title", "") or "Untitled document",
                "received_date": raw_date,
                "mode": getattr(document, "mode", None) or "Manual Upload",
                "priority": priority_val,
                "source": getattr(document, "source", None) or "Manual Intake",
                "description": (
                    getattr(document, "remarks", None)
                    or getattr(document, "description", None)
                    or getattr(document, "title", None)
                    or "Uploaded document"
                ),
                "ocr_text": getattr(document, "ocr_text", None) or "",
                "suggested_department_id": (
                    str(document.suggested_department_id)
                    if getattr(document, "suggested_department_id", None)
                    else ""
                ),
                "suggested_department_name": (
                    getattr(document, "suggested_department_name", None) or ""
                ),
                "suggested_employee_id": (
                    str(document.suggested_employee_id)
                    if getattr(document, "suggested_employee_id", None)
                    else ""
                ),
                "suggested_employee_name": (
                    getattr(document, "suggested_employee_name", None) or ""
                ),
            }

            data = api_client.upload(
                Endpoints.INTAKE_MANUAL_UPLOAD,
                file_path_or_tuple=file_path,
                field_name="file",
                extra_data=form_data,
            )
        else:
            payload = {
                "title": getattr(document, "title", "") or "Untitled document",
                "received_date": raw_date,
                "mode": getattr(document, "mode", None) or "External",
                "source": getattr(document, "source", None) or "External",
                "deadline": (
                    str(getattr(document, "deadline", "")).split()[0]
                    if getattr(document, "deadline", None)
                    else None
                ),
                "description": (
                    getattr(document, "remarks", None)
                    or getattr(document, "description", None)
                    or getattr(document, "title", None)
                    or "Document"
                ),
                "priority": priority_val,
                "suggested_department_id": getattr(
                    document, "suggested_department_id", None
                ),
                "suggested_department_name": getattr(
                    document, "suggested_department_name", None
                ),
                "suggested_employee_id": getattr(
                    document, "suggested_employee_id", None
                ),
                "suggested_employee_name": getattr(
                    document, "suggested_employee_name", None
                ),
                "ocr_text": getattr(document, "ocr_text", None),
                "confidence": getattr(document, "confidence", None),
            }
            data = api_client.post(Endpoints.DOCUMENT_CREATE, json=payload)

        if not data:
            raise RuntimeError("Backend returned an empty document response.")

        return DocumentModel.from_dict(data)

    def close_document(self, document_id: int, remarks: Optional[str] = None, expected_version: Optional[int] = None) -> DocumentModel:
        """Permanently closes a completed document."""
        payload = {"remarks": remarks, "expected_version": expected_version}
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
        remarks: Optional[str] = None,
        requires_hod_validation: bool = False,
        expected_version: Optional[int] = None,
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
            "remarks": remarks,
            "requires_hod_validation": requires_hod_validation,
            "expected_version": expected_version,
        }
        data = api_client.post(Endpoints.DOCUMENT_ROUTE(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_director_remark(self, document_id: int, remark: str, expected_version: Optional[int] = None) -> DocumentModel:
        """Director saves or updates a remark on the document."""
        payload = {"director_remark": remark, "expected_version": expected_version}
        data = api_client.put(Endpoints.DIRECTOR_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None, expected_version: Optional[int] = None) -> DocumentModel:
        """Director returns reviewed document back to DS."""
        payload = {"remarks": remarks, "expected_version": expected_version}
        data = api_client.post(Endpoints.DOCUMENT_RETURN_TO_DS(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def save_hod_remark(self, document_id: int, remark: str, expected_version: Optional[int] = None) -> DocumentModel:
        """HOD saves or updates department remarks on the document."""
        payload = {"hod_remark": remark, "expected_version": expected_version}
        data = api_client.put(Endpoints.HOD_REMARK(document_id), json=payload)
        return DocumentModel.from_dict(data)

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None, expected_version: Optional[int] = None) -> DocumentModel:
        """DS forwards employee progress update to Director as follow-up."""
        payload = {"remarks": remarks, "expected_version": expected_version}
        data = api_client.post(Endpoints.DOCUMENT_FOLLOW_UP(document_id), json=payload)
        return DocumentModel.from_dict(data)

    # =========================================================
    # WORK ASSIGNMENT (HOD -> Employee Delegation)
    # =========================================================

    def assign_employee(
        self,
        document_id: int,
        assigned_to_id: int,
        instructions: Optional[str] = None,
        requires_hod_validation: bool = False,
        routing_id: Optional[int] = None,
        change_reason: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> WorkAssignmentModel:
        """
        HOD delegates work on a document to an employee.
        Sends backend expected assigned_to_user_id and requires_hod_validation fields.
        """
        payload = {
            "assigned_to_user_id": assigned_to_id,
            "instructions": instructions,
            "requires_hod_validation": requires_hod_validation,
            "routing_id": routing_id,
            "change_reason": change_reason,
            "expected_version": expected_version,
        }
        data = api_client.post(Endpoints.DOCUMENT_ASSIGN(document_id), json=payload)
        return WorkAssignmentModel.from_dict(data)

    def hod_assign_team(
        self, document_id: int, member_user_ids: List[int], routing_id: Optional[int] = None,
        team_name: Optional[str] = None, instructions: Optional[str] = None,
        requires_hod_validation: bool = False, expected_version: Optional[int] = None,
    ) -> WorkAssignmentModel:
        payload = {
            "member_user_ids": member_user_ids, "routing_id": routing_id,
            "team_name": team_name, "instructions": instructions,
            "requires_hod_validation": requires_hod_validation, "expected_version": expected_version,
        }
        data = api_client.post(Endpoints.DOCUMENT_HOD_ASSIGN_TEAM(document_id), json=payload)
        return WorkAssignmentModel.from_dict(data)

    def ds_assign_team(
        self, document_id: int, member_user_ids: List[int], routing_id: Optional[int] = None,
        team_name: Optional[str] = None, instructions: Optional[str] = None,
        requires_hod_validation: bool = False, expected_version: Optional[int] = None,
    ) -> WorkAssignmentModel:
        payload = {
            "member_user_ids": member_user_ids, "routing_id": routing_id,
            "team_name": team_name, "instructions": instructions,
            "requires_hod_validation": requires_hod_validation, "expected_version": expected_version,
        }
        data = api_client.post(Endpoints.DOCUMENT_DS_ASSIGN_TEAM(document_id), json=payload)
        return WorkAssignmentModel.from_dict(data)

    def assign_multi(self, document_id: int, assignments_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """DS configures multi-department/employee routing."""
        payload = {"assignments": assignments_list}
        return api_client.post(Endpoints.DOCUMENT_ASSIGN_MULTI(document_id), json=payload) or []

    def get_document_assignments(self, document_id: int) -> List[Dict[str, Any]]:
        """Retrieves multi-assignment records for a document."""
        try:
            return api_client.get(Endpoints.DOCUMENT_ASSIGNMENTS(document_id)) or []
        except Exception:
            return []

    def update_document_assignment(self, document_id: int, assignment_id: int, update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """HOD updates an assignment record."""
        return api_client.patch(Endpoints.DOCUMENT_ASSIGNMENT_UPDATE(document_id, assignment_id), json=update_dict) or {}

    def hod_validate_progress(
        self,
        document_id: int,
        progress_id: int,
        action: str,
        note: Optional[str] = None
    ) -> ProgressUpdateModel:
        """
        HOD validates an employee progress update.

        The active HOD membership is propagated automatically by APIClient via
        X-Work-Context-Id; it is deliberately not duplicated in the JSON body.
        """
        payload = {"action": action, "note": note}
        data = api_client.post(
            Endpoints.PROGRESS_HOD_VALIDATE(document_id, progress_id),
            json=payload,
        )
        return ProgressUpdateModel.from_dict(data)

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        """Retrieves assignment records for a document."""
        try:
            data = api_client.get(Endpoints.DOCUMENT_ASSIGNMENTS(document_id))
            return [WorkAssignmentModel.from_dict(a) for a in data]
        except Exception:
            return []

    def create_branches(
        self,
        document_id: int,
        branches: List[Dict[str, Any]],
        expected_version: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """DS creates one or more canonical routing branches."""
        payload = {
            "branches": branches,
            "expected_version": expected_version
        }
        return api_client.post(Endpoints.DOCUMENT_BRANCHES(document_id), json=payload) or []

    def get_document_branches(self, document_id: int) -> List[Dict[str, Any]]:
        """Retrieves canonical routing branches for a document."""
        try:
            return api_client.get(Endpoints.DOCUMENT_BRANCHES(document_id)) or []
        except Exception:
            return []

    def assign_branch_employee(
        self,
        document_id: int,
        routing_id: int,
        assigned_to_user_id: int,
        instructions: Optional[str] = None,
        change_reason: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Assigns staff responsibility on a canonical branch."""
        payload = {
            "assigned_to_user_id": assigned_to_user_id,
            "instructions": instructions,
            "change_reason": change_reason,
            "expected_version": expected_version
        }
        return api_client.post(Endpoints.DOCUMENT_BRANCH_ASSIGN(document_id, routing_id), json=payload) or {}

    def submit_director_review(
        self,
        document_id: int,
        decision: str,
        remark_text: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Director submits machine-readable decision (CONTINUE or CLOSE)."""
        payload = {
            "decision": decision,
            "remark_text": remark_text,
            "expected_version": expected_version
        }
        return api_client.post(Endpoints.DOCUMENT_DIRECTOR_REVIEW(document_id), json=payload) or {}

    def get_active_tso(self) -> Optional[Dict[str, Any]]:
        """Admin retrieves current active TSO membership."""
        try:
            return api_client.get(Endpoints.ADMIN_TSO)
        except Exception:
            return None

    def activate_tso(self, user_id: int) -> Dict[str, Any]:
        """Admin assigns a user as the single active TSO."""
        return api_client.post(Endpoints.ADMIN_ACTIVATE_TSO(user_id)) or {}

    # =========================================================
    # PROGRESS & ATTACHMENTS (Employee Reporting)
    # =========================================================

    def submit_progress(
        self,
        document_id: int,
        description: str,
        work_assignment_id: Optional[int] = None,
        attachment_file_path: Optional[str] = None,
    ) -> ProgressUpdateModel:
        """
        Employee submits a progress update.
        Creates progress record via JSON, then uploads attachment if provided.
        """
        payload = {"description": description, "work_assignment_id": work_assignment_id}
        # APIClient automatically sends the selected EMPLOYEE/TSO context
        # through X-Work-Context-Id. The backend binds the progress update to
        # the corresponding WorkAssignment.
        data = api_client.post(
            Endpoints.PROGRESS_CREATE(document_id),
            json=payload,
        )
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
        Retrieves system-wide activity history using the batch history endpoint with graceful fallback.
        """
        all_events: List[WorkflowEventModel] = []
        try:
            data = api_client.get(Endpoints.DOCUMENTS_HISTORY_ALL)
            if isinstance(data, list):
                all_events = [WorkflowEventModel.from_dict(e) for e in data]
        except Exception:
            docs = self.get_documents()
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

    # =========================================================
    # OUTLOOK INTAKE & WORKFLOW REMINDERS
    # =========================================================

    def sync_outlook(self) -> Dict[str, Any]:
        """
        Calls backend to synchronize incoming emails and attachments from DS Outlook mailbox.
        """
        try:
            return api_client.post(Endpoints.INTAKE_SYNC_OUTLOOK, json={}) or {}
        except Exception as ex:
            return {
                "status": "error",
                "synced_count": 0,
                "ignored_duplicates": 0,
                "message": f"Failed to sync Outlook mailbox: {str(ex)}"
            }

    def send_document_reminder(self, document_id: int, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Dispatches an official action reminder via backend API to current responsible user.
        """
        payload = {"message": message} if message else {}
        return api_client.post(Endpoints.DOCUMENT_REMIND(document_id), json=payload)
