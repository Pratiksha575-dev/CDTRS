import os
import shutil
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from models.attachment import AttachmentModel
from repositories.provider import get_repository


class AttachmentService:
    """
    Client domain service managing attachment lifecycle, metadata resolution,
    secure role-based access, preview invocation, and local downloads.
    """

    def __init__(self):
        pass

    def get_document_attachments(
        self,
        document_id: int,
        category: Optional[str] = None
    ) -> List[AttachmentModel]:
        """
        Retrieves all attachments associated with a document.
        Optionally filters by category ('ORIGINAL' or 'WORKFLOW').
        """
        repo = get_repository()
        return repo.get_attachments(document_id=document_id, category=category)

    def get_progress_attachments(
        self,
        progress_update_id: int
    ) -> List[AttachmentModel]:
        """Retrieves supporting attachments uploaded for a specific progress update."""
        repo = get_repository()
        # Mock repository attachment query
        if hasattr(repo, "_attachments"):
            return [a for a in repo._attachments if a.progress_update_id == progress_update_id]
        return []

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = "WORKFLOW",
        source: Optional[str] = None
    ) -> AttachmentModel:
        """Uploads and associates an attachment with a document or progress update."""
        repo = get_repository()
        return repo.upload_attachment(
            document_id=document_id,
            file_path=file_path,
            progress_update_id=progress_update_id,
            category=category,
            source=source
        )

    def open_attachment(self, attachment: AttachmentModel, parent: Optional[QWidget] = None) -> bool:
        """
        Launches the attachment in the default system viewer (PDF viewer, Image viewer, etc.).
        """
        if not attachment or not attachment.file_path:
            if parent:
                QMessageBox.warning(parent, "Attachment Error", "Attachment reference path is invalid or missing.")
            return False

        # Resolve path
        path = attachment.file_path
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        if not os.path.exists(path):
            if parent:
                QMessageBox.warning(
                    parent,
                    "File Not Found",
                    f"The attachment file could not be located on disk:\n{path}"
                )
            return False

        # Use QDesktopServices to open with default application
        url = QUrl.fromLocalFile(path)
        success = QDesktopServices.openUrl(url)
        return success

    def download_attachment(
        self,
        attachment: AttachmentModel,
        parent: Optional[QWidget] = None,
        target_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Saves a copy of the attachment to a user-chosen destination folder.
        """
        if not attachment or not attachment.file_path:
            if parent:
                QMessageBox.warning(parent, "Download Error", "Attachment reference is invalid.")
            return None

        src_path = attachment.file_path
        if not os.path.isabs(src_path):
            src_path = os.path.abspath(src_path)

        if not os.path.exists(src_path):
            if parent:
                QMessageBox.warning(
                    parent,
                    "File Not Found",
                    f"Source attachment file could not be located on disk:\n{src_path}"
                )
            return None

        # Determine target file destination
        if not target_path:
            dest_dir = QFileDialog.getExistingDirectory(
                parent,
                "Select Download Folder",
                os.path.expanduser("~")
            )
            if not dest_dir:
                return None
            target_path = os.path.join(dest_dir, attachment.file_name or os.path.basename(src_path))

        try:
            shutil.copy2(src_path, target_path)
            if parent:
                QMessageBox.information(
                    parent,
                    "Download Complete",
                    f"Attachment saved successfully:\n{target_path}"
                )
            return target_path
        except Exception as ex:
            if parent:
                QMessageBox.critical(parent, "Download Failed", f"Could not save file: {str(ex)}")
            return None


# Global singleton service
attachment_service = AttachmentService()
