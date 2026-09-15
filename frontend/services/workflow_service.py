from typing import Any, Dict, List, Optional, Union

from models.workflow_event import WorkflowEventModel
from repositories.provider import get_repository


class WorkflowService:
    """Client service for workflow timeline and audit history."""

    def __init__(self):
        pass

    def get_history(self, document_id_or_ref: Union[int, str]) -> List[WorkflowEventModel]:
        repo = get_repository()
        if isinstance(document_id_or_ref, int):
            return repo.get_workflow_history(document_id_or_ref)
        reference = str(document_id_or_ref).strip()
        if not reference:
            return []
        doc = next(
            (d for d in repo.get_documents()
             if str(getattr(d, 'reference', '')) == reference
             or str(getattr(d, 'id', '')) == reference),
            None,
        )
        return repo.get_workflow_history(doc.id) if doc and doc.id is not None else []

    def get_workflow_history(self, document_id_or_ref: Union[int, str]) -> List[WorkflowEventModel]:
        return self.get_history(document_id_or_ref)

    def get_all_audit_history(
        self, user: Optional[str] = None, action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        return get_repository().get_all_audit_history(user=user, action=action)


workflow_service = WorkflowService()
