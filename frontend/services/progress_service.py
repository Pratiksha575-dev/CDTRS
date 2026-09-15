from typing import List, Optional

from models.attachment import AttachmentModel
from models.progress_update import ProgressUpdateModel
from repositories.provider import get_repository


class ProgressService:
    """
    Service layer for document progress updates.

    Progress is always associated with a specific WorkAssignment.
    This keeps independent routing branches and workers isolated from
    one another.
    """

    def __init__(self):
        pass

    def submit_progress(
        self,
        document_id: int,
        description: str,
        work_assignment_id: Optional[int] = None,
        attachment_file_path: Optional[str] = None,
    ) -> ProgressUpdateModel:
        """
        Submit a progress report for a specific work assignment.

        `work_assignment_id` identifies the exact workstream on which
        the current user is reporting progress.

        The backend remains responsible for validating that the
        authenticated user is actually assigned to that work assignment.
        """
        repo = get_repository()

        return repo.submit_progress(
            document_id=document_id,
            description=description,
            work_assignment_id=work_assignment_id,
            attachment_file_path=attachment_file_path,
        )

    def submit_progress_update(
        self,
        document_id: int,
        description: str,
        work_assignment_id: Optional[int] = None,
        attachment_file_path: Optional[str] = None,
    ) -> ProgressUpdateModel:
        """
        Submit a progress update for a specific WorkAssignment.

        This is the explicit update-oriented entry point used by
        callers that prefer the longer method name.
        """
        return self.submit_progress(
            document_id=document_id,
            description=description,
            work_assignment_id=work_assignment_id,
            attachment_file_path=attachment_file_path,
        )

    def get_progress_updates(
        self,
        document_id: int,
    ) -> List[ProgressUpdateModel]:
        """
        Retrieve all progress updates for a document.

        Each returned ProgressUpdateModel contains its
        `work_assignment_id`, allowing the UI to separate progress
        by workstream.
        """
        repo = get_repository()
        return repo.get_progress_updates(document_id)

    def hod_validate_progress(
        self,
        document_id: int,
        progress_id: int,
        action: str,
        note: Optional[str] = None,
    ) -> ProgressUpdateModel:
        """
        HOD approves or returns a progress update.
        """
        repo = get_repository()

        return repo.hod_validate_progress(
            document_id=document_id,
            progress_id=progress_id,
            action=action,
            note=note,
        )

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
    ) -> AttachmentModel:
        """
        Upload a standalone document attachment or attach a file to
        an existing progress update.
        """
        repo = get_repository()

        return repo.upload_attachment(
            document_id=document_id,
            file_path=file_path,
            progress_update_id=progress_update_id,
        )

    def get_attachments(
        self,
        document_id: int,
    ) -> List[AttachmentModel]:
        """
        Retrieve all attachments associated with a document.
        """
        repo = get_repository()
        return repo.get_attachments(document_id)


# Global service instance.
progress_service = ProgressService()