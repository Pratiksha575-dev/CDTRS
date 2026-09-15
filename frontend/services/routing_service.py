from typing import Any, Dict, List, Optional

from models.document import DocumentModel
from models.enums import RouteTypeEnum
from repositories.provider import get_repository


class RoutingService:
    """
    Client service for DS-controlled document routing.

    The backend is authoritative for all routing, permissions, workflow state,
    branch state, and assignments.

    Canonical routing is represented through DocumentDepartmentRouting branches.

    OCR/routing-intelligence suggestions are advisory only and never perform
    routing automatically.
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

        Supported branch types:
            - DEPARTMENT_HOD
            - DIRECT_EMPLOYEE
            - TSO

        Each branch should contain the fields expected by the backend
        BranchCreate schema:
            branch_type
            department_id
            target_user_id
            requires_hod_validation
            instructions

        The backend is responsible for validating:
            - current workflow state
            - DS permissions
            - department membership
            - target user validity
            - active status
            - optimistic concurrency
        """
        if not branches:
            raise ValueError("At least one routing branch is required.")

        repo = get_repository()

        return repo.create_branches(
            document_id=document_id,
            branches=branches,
            expected_version=expected_version,
        )

    def route_to_hod_canonical(
        self,
        document_id: int,
        department_id: int,
        instructions: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Canonical DS -> Department/HOD routing.

        IMPORTANT:
        target_user_id is intentionally NOT supplied.

        HOD access is determined from the routed department branch and
        the HOD's department/work-context membership.
        """
        if not department_id:
            raise ValueError("A department must be selected.")

        branch = {
            "branch_type": "DEPARTMENT_HOD",
            "department_id": department_id,
            "target_user_id": None,
            "requires_hod_validation": False,
            "instructions": instructions,
        }

        return self.route_canonical_branches(
            document_id=document_id,
            branches=[branch],
            expected_version=expected_version,
        )

    def route_to_employee_canonical(
        self,
        document_id: int,
        employee_id: int,
        instructions: Optional[str] = None,
        requires_hod_validation: bool = False,
        expected_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Canonical DS -> direct Employee routing.

        Unlike DEPARTMENT_HOD routing, a direct employee branch contains
        target_user_id.
        """
        if not employee_id:
            raise ValueError("An employee must be selected.")

        branch = {
            "branch_type": "DIRECT_EMPLOYEE",
            "department_id": None,
            "target_user_id": employee_id,
            "requires_hod_validation": requires_hod_validation,
            "instructions": instructions,
        }

        return self.route_canonical_branches(
            document_id=document_id,
            branches=[branch],
            expected_version=expected_version,
        )

    def route_to_tso_canonical(
        self,
        document_id: int,
        tso_user_id: int,
        instructions: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Canonical DS -> TSO routing.
        """
        if not tso_user_id:
            raise ValueError("A TSO must be selected.")

        branch = {
            "branch_type": "TSO",
            "department_id": None,
            "target_user_id": tso_user_id,
            "requires_hod_validation": False,
            "instructions": instructions,
        }

        return self.route_canonical_branches(
            document_id=document_id,
            branches=[branch],
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
        """
        Assigns an employee to an existing canonical routing branch.

        The repository/backend remains responsible for deciding whether the
        current user is permitted to assign that particular branch.
        """
        if not routing_id:
            raise ValueError("A routing branch must be selected.")

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

    def get_document_branches(
        self,
        document_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns the canonical routing branches for a document.
        """
        repo = get_repository()

        return repo.get_document_branches(
            document_id=document_id,
        )

    # =========================================================
    # WORKFLOW TRANSITIONS
    # =========================================================

    def route_to_director(
        self,
        document_id: int,
        remarks: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """
        DS routes a newly registered document to the Director for review.

        This is a workflow transition, not a department-routing branch.
        """
        repo = get_repository()

        return repo.route_document(
            document_id=document_id,
            route_type="INITIAL_DIRECTOR_REVIEW",
            remarks=remarks or "Forwarded for Director Review",
            expected_version=expected_version,
        )

    def route_to_hod(
        self, document_id: int, department_id: Optional[int] = None,
        remarks: Optional[str] = None, department_name: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """Compatibility wrapper for single DS -> HOD routing."""
        if department_id is None and department_name:
            for dept in get_repository().get_departments():
                name = (dept.name or "").strip().lower()
                target = department_name.strip().lower()
                if name == target or name in target or target in name:
                    department_id = dept.id
                    break
        if department_id is None:
            raise ValueError("A department must be selected for HOD routing.")
        return get_repository().route_document(
            document_id=document_id,
            route_type="POST_REVIEW_TO_HOD",
            to_department_id=int(department_id),
            remarks=remarks,
            expected_version=expected_version,
        )

    def route_to_employee(
        self, document_id: int, employee_id: int, remarks: Optional[str] = None,
        employee_name: Optional[str] = None, requires_hod_validation: bool = False,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """Compatibility wrapper for single DS -> employee routing."""
        if not employee_id:
            raise ValueError("An employee must be selected.")
        return get_repository().route_document(
            document_id=document_id,
            route_type="POST_REVIEW_TO_EMPLOYEE",
            to_user_id=int(employee_id),
            remarks=remarks,
            requires_hod_validation=requires_hod_validation,
            expected_version=expected_version,
        )

    def return_to_ds(
        self,
        document_id: int,
        remarks: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """
        Director returns the reviewed document to DS.
        """
        repo = get_repository()

        return repo.return_to_ds(
            document_id=document_id,
            remarks=remarks,
            expected_version=expected_version,
        )

    def forward_followup_to_director(
        self,
        document_id: int,
        remarks: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """
        DS forwards an execution/progress follow-up to Director.
        """
        repo = get_repository()

        return repo.forward_followup_to_director(
            document_id=document_id,
            remarks=remarks,
            expected_version=expected_version,
        )

    def save_director_remark(
        self,
        document_id: int,
        remark: str,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """
        Director saves a natural-language remark independently of return.
        """
        repo = get_repository()

        return repo.save_director_remark(
            document_id=document_id,
            remark=remark,
            expected_version=expected_version,
        )

    def save_hod_remark(
        self,
        document_id: int,
        remark: str,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        """
        HOD saves a remark independently of work assignment.
        """
        repo = get_repository()

        return repo.save_hod_remark(
            document_id=document_id,
            remark=remark,
            expected_version=expected_version,
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

        The current workflow keeps Director review as a backend-authoritative
        workflow operation. Newer UI code may use the dedicated remark and
        return/follow-up methods where appropriate.
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

    def analyze_director_remark(
        self,
        remark: str,
    ) -> Dict[str, Any]:
        """
        Returns an advisory routing preview only.

        This method NEVER calls a routing endpoint and NEVER mutates workflow
        state.

        A DS user must explicitly choose and confirm routing through the
        canonical routing UI.
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

        # -----------------------------------------------------
        # Employee matching is deliberately suggestion-only.
        # -----------------------------------------------------
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

        # -----------------------------------------------------
        # Department matching is also suggestion-only.
        # -----------------------------------------------------
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
                            if (
                                (dept.name or "").lower()
                                == department_name.lower()
                            ):
                                department_id = dept.id
                                break
                    except Exception:
                        pass

                    break

        # -----------------------------------------------------
        # This flag describes only advisory parser output.
        # -----------------------------------------------------
        has_suggestion = bool(department or employee)

        confidence = (
            96
            if department and employee
            else 92
            if has_suggestion
            else 0
        )

        return {
            "has_routing_instruction": has_suggestion,
            "suggested_department": department if has_suggestion else None,
            "suggested_department_id": (
                department_id if has_suggestion else None
            ),
            "suggested_employee": employee if has_suggestion else None,
            "suggested_employee_id": (
                employee_id if has_suggestion else None
            ),
            "confidence": confidence,
            "source": "Director Remark" if has_suggestion else None,
            "is_advisory": True,
            "authoritative": False,
        }


# Global singleton service instance
routing_service = RoutingService()