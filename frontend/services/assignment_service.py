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
    ) -> WorkAssignmentModel:
        """HOD delegates work to one employee."""
        if not assigned_to_id:
            raise ValueError("An employee must be selected.")

        repo = get_repository()
        return repo.assign_employee(
            document_id=document_id,
            assigned_to_id=assigned_to_id,
            instructions=instructions,
            requires_hod_validation=requires_hod_validation,
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
    # LEGACY MULTI-ASSIGNMENT COMPATIBILITY
    # =========================================================

    def assign_multi(
        self,
        document_id: int,
        assignments_list: List[dict],
    ) -> List[dict]:
        """
        Legacy multi-assignment wrapper.

        New DS routing should prefer canonical branches via
        RoutingService.route_canonical_branches().
        """
        repo = get_repository()
        return repo.assign_multi(document_id, assignments_list)

    # =========================================================
    # ASSIGNMENT RETRIEVAL / UPDATE
    # =========================================================

    def get_document_assignments(
        self,
        document_id: int,
    ) -> List[dict]:
        """Retrieve assignment records for a document."""
        repo = get_repository()
        return repo.get_document_assignments(document_id)

    def update_document_assignment(
        self,
        document_id: int,
        assignment_id: int,
        update_dict: Dict[str, Any],
    ) -> dict:
        """Update an existing assignment through the backend."""
        repo = get_repository()
        return repo.update_document_assignment(
            document_id,
            assignment_id,
            update_dict,
        )

    def get_assignments(
        self,
        document_id: int,
    ) -> List[WorkAssignmentModel]:
        """Retrieve assignment history for a document."""
        repo = get_repository()
        return repo.get_assignments(document_id)


# Global singleton service instance
assignment_service = AssignmentService()
