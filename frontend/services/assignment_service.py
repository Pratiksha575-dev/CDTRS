from typing import Any, Dict, List, Optional

from models.work_assignment import WorkAssignmentModel
from repositories.provider import get_repository


class AssignmentService:
    """
    Client service for employee work assignment/delegation.

    Routing and assignment permissions remain backend-authoritative.
    This service only forwards explicit user actions to the repository.
    """

    def __init__(self):
        pass

    # =========================================================
    # SINGLE EMPLOYEE ASSIGNMENT
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
        HOD delegates work to one employee on a canonical routing branch.

        routing_id identifies the DocumentDepartmentRouting branch.
        The repository/backend remains authoritative for role,
        department, branch, and concurrency validation.
        """
        if not assigned_to_id:
            raise ValueError("An employee must be selected.")

        if routing_id is None:
            raise ValueError(
                "routing_id is required for canonical employee assignment."
            )

        repo = get_repository()

        return repo.assign_employee(
            document_id=document_id,
            assigned_to_id=assigned_to_id,
            instructions=instructions,
            requires_hod_validation=requires_hod_validation,
            routing_id=int(routing_id),
            change_reason=change_reason,
            expected_version=expected_version,
        )

    # =========================================================
    # TEAM ASSIGNMENTS
    # =========================================================

    def hod_assign_team(
        self,
        document_id: int,
        member_user_ids: List[int],
        routing_id: Optional[int] = None,
        team_name: Optional[str] = None,
        instructions: Optional[str] = None,
        requires_hod_validation: bool = False,
        expected_version: Optional[int] = None,
    ) -> WorkAssignmentModel:
        """
        HOD creates a multi-member team assignment.

        Backend validates that HOD-selected employees are eligible for
        the routed department/branch.
        """
        if not member_user_ids:
            raise ValueError("At least one team member must be selected.")

        repo = get_repository()

        return repo.hod_assign_team(
            document_id=document_id,
            member_user_ids=member_user_ids,
            routing_id=routing_id,
            team_name=team_name,
            instructions=instructions,
            requires_hod_validation=requires_hod_validation,
            expected_version=expected_version,
        )

    def ds_assign_team(
        self,
        document_id: int,
        member_user_ids: List[int],
        routing_id: Optional[int] = None,
        team_name: Optional[str] = None,
        instructions: Optional[str] = None,
        requires_hod_validation: bool = False,
        expected_version: Optional[int] = None,
    ) -> WorkAssignmentModel:
        """
        DS creates a multi-member work assignment.

        This is useful for cross-department teams and direct DS-managed
        assignments. Backend remains responsible for scope validation.
        """
        if not member_user_ids:
            raise ValueError("At least one team member must be selected.")

        repo = get_repository()

        return repo.ds_assign_team(
            document_id=document_id,
            member_user_ids=member_user_ids,
            routing_id=routing_id,
            team_name=team_name,
            instructions=instructions,
            requires_hod_validation=requires_hod_validation,
            expected_version=expected_version,
        )

    # =========================================================
    # CANONICAL BRANCH ASSIGNMENT
    # =========================================================

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
        Assign an employee directly to a canonical routing branch.

        This is the preferred assignment method for new workflow code.
        The backend validates whether the current user is allowed to
        assign staff on the specified branch.
        """
        if not routing_id:
            raise ValueError("A routing branch must be selected.")

        if not assigned_to_user_id:
            raise ValueError("An employee must be selected.")

        repo = get_repository()

        return repo.assign_branch_employee(
            document_id=document_id,
            routing_id=int(routing_id),
            assigned_to_user_id=int(assigned_to_user_id),
            instructions=instructions,
            change_reason=change_reason,
            expected_version=expected_version,
        )

    # =========================================================
    # BRANCH RETRIEVAL
    # =========================================================

    def get_document_branches(
        self,
        document_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the canonical routing branches for a document.
        """
        repo = get_repository()
        return repo.get_document_branches(document_id)

    # =========================================================
    # ASSIGNMENT RETRIEVAL / UPDATE
    # =========================================================

    def get_document_assignments(
        self,
        document_id: int,
    ) -> List[dict]:
        """
        Retrieve assignment records for a document.
        """
        repo = get_repository()
        return repo.get_document_assignments(document_id)

    def update_document_assignment(
        self,
        document_id: int,
        assignment_id: int,
        update_dict: Dict[str, Any],
    ) -> dict:
        """
        Update an existing assignment through the backend.

        New workflow code should prefer immutable assignment history and
        canonical branch-specific operations where applicable.
        """
        repo = get_repository()

        return repo.update_document_assignment(
            document_id,
            assignment_id,
            update_dict,
        )



# Global singleton service instance
assignment_service = AssignmentService()