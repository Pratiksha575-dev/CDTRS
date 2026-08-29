from typing import Any, Dict, List, Optional, Union

from models.document import DocumentModel
from models.workflow_event import WorkflowEventModel
from repositories.provider import get_repository


class WorkflowService:
    """
    Client service managing document workflow timeline, activity events, and audit logs.
    """

    def __init__(self):
        pass

    def get_history(self, document_id_or_ref: Union[int, str]) -> List[WorkflowEventModel]:
        """
        Retrieves chronological workflow history for a document.
        Supports document ID or reference string.
        """
        repo = get_repository()
        if isinstance(document_id_or_ref, int):
            return repo.get_workflow_history(document_id_or_ref)

        # Lookup document by reference if string provided
        doc = next((d for d in repo.get_documents() if d.reference == str(document_id_or_ref) or str(d.id) == str(document_id_or_ref)), None)
        if doc and doc.id is not None:
            return repo.get_workflow_history(doc.id)
        return []

    def get_workflow_history(self, document_id_or_ref: Union[int, str]) -> List[WorkflowEventModel]:
        """Alias for get_history."""
        return self.get_history(document_id_or_ref)

    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        """Retrieves system-wide audit timeline."""
        repo = get_repository()
        return repo.get_all_audit_history(user=user, action=action)

    # =========================================================
    # BACKWARD COMPATIBILITY METHODS FOR EXISTING INTAKE & INBOX
    # =========================================================

    @staticmethod
    def forward_to_director(document: Union[DocumentModel, Dict[str, Any]]) -> bool:
        """
        Backward compatibility handler for legacy DocumentIntakePage.
        Routes intake document to Director via repository.
        """
        repo = get_repository()
        doc_id = document.get("id") or document.get("doc_id")
        if doc_id:
            try:
                repo.route_document(
                    document_id=int(doc_id),
                    route_type="DS_TO_DIRECTOR",
                    # Backend resolves Director role — no hardcoded user ID needed
                    remarks=document.get("remarks")
                )
                return True
            except Exception:
                return False
        return False

    @staticmethod
    def get_director_inbox() -> List[DocumentModel]:
        """
        Backward compatibility handler for legacy DirectorInboxPage.
        Returns documents currently under Director review.
        """
        repo = get_repository()
        return [
            d for d in repo.get_documents()
            if (d.current_stage == "DIRECTOR" or d.status == "Under Director Review" or d.status == "Director Review")
        ]


# Global singleton service instance
workflow_service = WorkflowService()