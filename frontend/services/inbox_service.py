from typing import List

from models.document import DocumentModel
from repositories.provider import get_repository


class InboxService:
    """Client service for raw incoming documents pending DS intake."""

    def __init__(self):
        pass

    def get_inbox_documents(self) -> List[DocumentModel]:
        return get_repository().get_inbox()


inbox_service = InboxService()
