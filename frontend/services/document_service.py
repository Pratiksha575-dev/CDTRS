from typing import Any, Dict, Optional, Union, List

from models.document import DocumentModel
from repositories.provider import get_repository


class DocumentService:
    """Client domain service for the canonical document lifecycle.

    The repository/API layer is authoritative for authentication, active work
    context, permissions, routing state, and optimistic concurrency.
    """

    def __init__(self):
        pass

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[DocumentModel]:
        return get_repository().get_documents(
            status=status, department=department, source=source, search=search
        )

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        return get_repository().get_document(document_id)

    def get_inbox(self) -> List[DocumentModel]:
        return get_repository().get_inbox()

    def add_inbox_item(self, document_data: Union[DocumentModel, Dict[str, Any]]) -> DocumentModel:
        model = DocumentModel.from_dict(document_data) if isinstance(document_data, dict) else document_data
        return get_repository().add_inbox_item(model)

    def remove_inbox_item(self, item_id: int) -> bool:
        return get_repository().remove_inbox_item(item_id)

    def create_document(
        self,
        document_data: Union[DocumentModel, Dict[str, Any]],
        file_path: Optional[str] = None,
    ) -> DocumentModel:
        model = DocumentModel.from_dict(document_data) if isinstance(document_data, dict) else document_data
        return get_repository().create_document(model, file_path=file_path)

    def close_document(
        self,
        document_id: int,
        remarks: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DocumentModel:
        return get_repository().close_document(
            document_id, remarks=remarks, expected_version=expected_version
        )


document_service = DocumentService()
