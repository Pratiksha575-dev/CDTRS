from typing import Any, Dict, List, Optional

from models.document import DocumentModel
from models.enums import RouteTypeEnum
from repositories.provider import get_repository


class RoutingService:
    """
    Client service for DS-controlled document routing.

    The backend is authoritative for all routing, permissions, workflow state,
    branch state, and assignments. OCR/routing-intelligence suggestions are
    advisory only and never perform routing automatically.
    """

    def __init__(self):
        pass

    # =========================================================
    # CANONICAL BRANCH ROUTING
    # =========================================================

    def route_canonical_branches(
        self,
        document_id: int,
        branches: List[Dict[str, Any]],
        expected_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        DS explicitly creates one or more canonical routing branches.

        Supported backend branch types include:
        - DEPARTMENT_HOD
        - DIRECT_EMPLOYEE
        - TSO

        No Director remark is interpreted here.
        """
        if not branches:
            raise ValueError("At least one routing branch is required.")

        repo = get_repository()
        return repo.create_branches(
            document_id=document_id,
            branches=branches,
            expected_version=expected_version,
        )

    def assign_branch_employee(
        self,
        document_id: int,
        routing_id: int,
        assigned_to_user_id: int,
        instructions: Optional[str] = None,
        change_reason: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Assigns an employee to an existing canonical routing branch."""
        if not assigned_to_user_id:
            raise ValueError("An employee must be selected.")

        repo = get_repository()
        return repo.assign_branch_employee(
            document_id=document_id,
            routing_id=routing_id,
            assigned_to_user_id=assigned_to_user_id,
            instructions=instructions,
            change_reason=change_reason,
            expected_version=expected_version,
        )

    # =========================================================
    # LEGACY / SINGLE ROUTING COMPATIBILITY
    # =========================================================

    def route_to_director(
        self,
        document_id: int,
        remarks: Optional[str] = None,
    ) -> DocumentModel:
        """DS routes a newly registered document to the Director for review."""
        repo = get_repository()
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_DIRECTOR.value,
            remarks=remarks or "Forwarded for Director Review",
        )

    def route_to_hod(
        self,
        document_id: int,
        department_id: Optional[int] = None,
        remarks: Optional[str] = None,
        department_name: Optional[str] = None,
    ) -> DocumentModel:
        """Legacy single-route wrapper for DS -> Department/HOD."""
        repo = get_repository()

        if department_id is None and department_name:
            departments = repo.get_departments()
            for dept in departments:
                name = (dept.name or "").lower()
                target = department_name.lower().strip()
                if name == target or name in target or target in name:
                    department_id = dept.id
                    break

        if department_id is None:
            raise ValueError(
                f"Cannot route to HOD: department ID is unknown for '{department_name}'."
            )

        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_HOD.value,
            to_department_id=department_id,
            remarks=remarks,
        )

    def route_to_employee(
        self,
        document_id: int,
        employee_id: int,
        remarks: Optional[str] = None,
        employee_name: Optional[str] = None,
        requires_hod_validation: bool = False,
    ) -> DocumentModel:
        """Legacy single-route wrapper for DS -> direct Employee."""
        if not employee_id:
            raise ValueError("An employee must be selected.")

        repo = get_repository()
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_EMPLOYEE.value,
            to_user_id=employee_id,
            remarks=remarks,
            requires_hod_validation=requires_hod_validation,
        )

    def return_to_ds(
        self,
        document_id: int,
        remarks: Optional[str] = None,
    ) -> DocumentModel:
        """Director returns the reviewed document to DS."""
        repo = get_repository()
        return repo.return_to_ds(document_id=document_id, remarks=remarks)

    def forward_followup_to_director(
        self,
        document_id: int,
        remarks: Optional[str] = None,
    ) -> DocumentModel:
        """DS forwards an execution/progress follow-up to Director."""
        repo = get_repository()
        return repo.forward_followup_to_director(
            document_id=document_id,
            remarks=remarks,
        )

    def save_director_remark(
        self,
        document_id: int,
        remark: str,
    ) -> DocumentModel:
        """Director saves a natural-language remark independently of return."""
        repo = get_repository()
        return repo.save_director_remark(
            document_id=document_id,
            remark=remark,
        )

    def save_hod_remark(
        self,
        document_id: int,
        remark: str,
    ) -> DocumentModel:
        """HOD saves a remark independently of work assignment."""
        repo = get_repository()
        return repo.save_hod_remark(
            document_id=document_id,
            remark=remark,
        )

    # =========================================================
    # DIRECTOR REVIEW COMPATIBILITY
    # =========================================================

    def submit_director_review(
        self,
        document_id: int,
        decision: str,
        remark_text: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility wrapper for older UI code.

        The current workflow does NOT require a machine-readable CONTINUE/CLOSE
        decision from the Director. New UI should use save_director_remark()
        and return_to_ds() separately.
        """
        repo = get_repository()
        return repo.submit_director_review(
            document_id=document_id,
            decision=decision,
            remark_text=remark_text,
            expected_version=expected_version,
        )

    # =========================================================
    # ADVISORY ROUTING ANALYSIS
    # =========================================================

    def analyze_director_remark(self, remark: str) -> Dict[str, Any]:
        """
        Returns an advisory preview only.

        This method NEVER calls a routing endpoint and NEVER mutates workflow
        state. A DS user must explicitly choose and confirm routing through
        the canonical routing UI.
        """
        text = (remark or "").strip()

        if not text:
            return {
                "has_routing_instruction": False,
                "suggested_department": None,
                "suggested_department_id": None,
                "suggested_employee": None,
                "suggested_employee_id": None,
                "confidence": 0,
                "source": None,
                "is_advisory": True,
                "authoritative": False,
            }

        repo = get_repository()
        department = None
        department_id = None
        employee = None
        employee_id = None

        # Employee matching is deliberately suggestion-only.
        try:
            live_users = repo.get_users(role="Employee")
            lowered = text.lower()
            for user in live_users:
                name = (user.full_name or "").strip()
                if not name:
                    continue
                first_name = name.split()[0]
                if name.lower() in lowered:
                    employee = name
                    employee_id = user.id
                    department = user.department_name
                    department_id = user.department_id
                    break
                if first_name and f" {first_name.lower()} " in f" {lowered} ":
                    employee = name
                    employee_id = user.id
                    department = user.department_name
                    department_id = user.department_id
                    break
        except Exception:
            pass

        # Department matching is also suggestion-only.
        if not department:
            department_keywords = (
                ("finance", "Finance"),
                ("accounts", "Finance"),
                ("budget", "Finance"),
                ("audit", "Finance"),
                ("human resource", "HR"),
                (" hr ", "HR"),
                ("hr department", "HR"),
                ("personnel", "HR"),
                ("recruitment", "HR"),
                ("leave", "HR"),
                ("technical", "Technical"),
                ("technology", "Technical"),
                ("systems", "Technical"),
                ("engineering", "Technical"),
                ("software", "Technical"),
                ("hardware", "Technical"),
                ("network", "Technical"),
                ("cyber", "Technical"),
                ("information technology", "Technical"),
            )

            lowered_padded = f" {text.lower()} "
            for keyword, department_name in department_keywords:
                if keyword in lowered_padded:
                    department = department_name
                    try:
                        for dept in repo.get_departments():
                            if (dept.name or "").lower() == department_name.lower():
                                department_id = dept.id
                                break
                    except Exception:
                        pass
                    break

        # This flag describes only whether the advisory parser found something.
        has_suggestion = bool(department or employee)
        confidence = 96 if department and employee else 92 if has_suggestion else 0

        return {
            "has_routing_instruction": has_suggestion,
            "suggested_department": department if has_suggestion else None,
            "suggested_department_id": department_id if has_suggestion else None,
            "suggested_employee": employee if has_suggestion else None,
            "suggested_employee_id": employee_id if has_suggestion else None,
            "confidence": confidence,
            "source": "Director Remark" if has_suggestion else None,
            "is_advisory": True,
            "authoritative": False,
        }


# Global singleton service instance
routing_service = RoutingService()
