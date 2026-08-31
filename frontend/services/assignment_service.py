from typing import List, Optional

from models.work_assignment import WorkAssignmentModel
from repositories.provider import get_repository


class AssignmentService:
    """
    Client service managing HOD to Employee work delegation.
    """

    def __init__(self):
        pass

    def assign_employee(
        self,
        document_id: int,
        assigned_to_id: int,
        instructions: Optional[str] = None,
        requires_hod_validation: bool = False
    ) -> WorkAssignmentModel:
        """HOD delegates work on a document to an employee."""
        repo = get_repository()
        return repo.assign_employee(
            document_id=document_id,
            assigned_to_id=assigned_to_id,
            instructions=instructions,
            requires_hod_validation=requires_hod_validation
        )

    def assign_multi(self, document_id: int, assignments_list: List[dict]) -> List[dict]:
        """DS configures multi-department/employee routing."""
        repo = get_repository()
        return repo.assign_multi(document_id, assignments_list)

    def get_document_assignments(self, document_id: int) -> List[dict]:
        """Retrieves multi-assignment records for a document."""
        repo = get_repository()
        return repo.get_document_assignments(document_id)

    def update_document_assignment(self, document_id: int, assignment_id: int, update_dict: dict) -> dict:
        """HOD updates an assignment record."""
        repo = get_repository()
        return repo.update_document_assignment(document_id, assignment_id, update_dict)

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        """Retrieves assignment history for a document."""
        repo = get_repository()
        return repo.get_assignments(document_id)


# Global singleton service instance
assignment_service = AssignmentService()
