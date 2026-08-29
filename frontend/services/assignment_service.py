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
        instructions: Optional[str] = None
    ) -> WorkAssignmentModel:
        """HOD delegates work on a document to an employee."""
        repo = get_repository()
        return repo.assign_employee(
            document_id=document_id,
            assigned_to_id=assigned_to_id,
            instructions=instructions
        )

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        """Retrieves assignment history for a document."""
        repo = get_repository()
        return repo.get_assignments(document_id)


# Global singleton service instance
assignment_service = AssignmentService()
