from typing import List, Optional

from models.attachment import AttachmentModel
from models.progress_update import ProgressUpdateModel
from repositories.provider import get_repository


class ProgressService:
    """
    Client service managing Employee free-text progress notes and supporting attachments.
    """

    def __init__(self):
        pass

    def submit_progress(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        """Submits a free-text progress note with optional supporting document."""
        repo = get_repository()
        return repo.submit_progress(
            document_id=document_id,
            description=description,
            attachment_file_path=attachment_file_path
        )

    def submit_progress_update(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        """Alias for submit_progress."""
        return self.submit_progress(
            document_id=document_id,
            description=description,
            attachment_file_path=attachment_file_path
        )

    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        """Retrieves chronological progress updates for a document."""
        repo = get_repository()
        return repo.get_progress_updates(document_id)

    def hod_validate_progress(
        self,
        document_id: int,
        progress_id: int,
        action: str,
        note: Optional[str] = None
    ) -> ProgressUpdateModel:
        """HOD approves or returns an employee progress update."""
        repo = get_repository()
        return repo.hod_validate_progress(document_id, progress_id, action, note)

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None
    ) -> AttachmentModel:
        """Uploads a standalone or progress-linked attachment."""
        repo = get_repository()
        return repo.upload_attachment(
            document_id=document_id,
            file_path=file_path,
            progress_update_id=progress_update_id
        )

    def get_attachments(self, document_id: int) -> List[AttachmentModel]:
        """Retrieves all attachments associated with a document."""
        repo = get_repository()
        return repo.get_attachments(document_id)


# Global singleton service instance
progress_service = ProgressService()
