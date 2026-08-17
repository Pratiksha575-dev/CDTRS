from typing import Any, Dict, List, Optional, Union

from models.document import DocumentModel
from repositories.provider import get_repository


class DocumentService:
    """
    Client service for canonical document lifecycle, search, retrieval, and intake.
    """

    def __init__(self):
        pass

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        """Retrieves documents repository with optional filtering."""
        repo = get_repository()
        return repo.get_documents(status=status, department=department, source=source, search=search)

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Retrieves a single document by ID."""
        repo = get_repository()
        return repo.get_document(document_id)

    def get_inbox(self) -> List[DocumentModel]:
        """Retrieves intake documents pending initial registration."""
        repo = get_repository()
        return repo.get_inbox()

    def add_inbox_item(self, document_data: Union[DocumentModel, Dict[str, Any]]) -> DocumentModel:
        """Adds incoming communication to intake queue."""
        repo = get_repository()
        if isinstance(document_data, dict):
            model = DocumentModel.from_dict(document_data)
        else:
            model = document_data
        return repo.add_inbox_item(model)

    def remove_inbox_item(self, item_id: int) -> bool:
        """Removes an incoming intake item after registration."""
        repo = get_repository()
        return repo.remove_inbox_item(item_id)

    def create_document(
        self,
        document_data: Union[DocumentModel, Dict[str, Any]],
        file_path: Optional[str] = None
    ) -> DocumentModel:
        """Creates a new document via repository."""
        repo = get_repository()
        if isinstance(document_data, dict):
            model = DocumentModel.from_dict(document_data)
        else:
            model = document_data
        return repo.create_document(model, file_path=file_path)

    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Closes a completed document (DS action)."""
        repo = get_repository()
        return repo.close_document(document_id, remarks=remarks)


# Global singleton service instance
document_service = DocumentService()