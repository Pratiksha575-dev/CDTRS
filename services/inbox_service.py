from typing import List

from models.document import DocumentModel
from repositories.provider import get_repository


class InboxService:
    """
    Client service for retrieving unprocessed incoming intake documents.
    """

    def __init__(self):
        pass

    def get_inbox_documents(self) -> List[DocumentModel]:
        """Retrieves raw incoming documents pending intake registration."""
        repo = get_repository()
        return repo.get_inbox()


# Global singleton service instance
inbox_service = InboxService()