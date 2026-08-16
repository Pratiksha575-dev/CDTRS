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

    def _ensure_local_copy(self, attachment: AttachmentModel, parent: Optional[QWidget] = None) -> Optional[str]:
        """
        Ensures a valid local file exists for viewing or opening.
        In API mode, streams the file from the backend download endpoint to a local cache folder.
        In Mock mode, resolves the local path or creates a dummy preview file if missing.
        """
        from config.settings import settings

        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cache", "attachments"))
        os.makedirs(cache_dir, exist_ok=True)
        sanitized_filename = "".join(c for c in (attachment.file_name or "attachment.pdf") if c.isalnum() or c in "._- ")
        cache_path = os.path.join(cache_dir, f"{attachment.id or 0}_{sanitized_filename}")

        if settings.is_api_mode and attachment.id:
            # Check if already cached
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
                return cache_path

            from api.client import api_client
            from api.endpoints import Endpoints
            try:
                endpoint = Endpoints.ATTACHMENT_DOWNLOAD(attachment.id)
                api_client.download(endpoint, cache_path)
                return cache_path
            except Exception as ex:
                if parent:
                    QMessageBox.warning(parent, "Download Error", f"Could not retrieve attachment from server: {str(ex)}")
                return None
        else:
            # Mock mode or local path resolution
            if attachment.file_path and os.path.exists(attachment.file_path):
                return os.path.abspath(attachment.file_path)

            # Generate mock preview file if not on disk
            if not os.path.exists(cache_path):
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(f"=== CDTRS ATTACHMENT PREVIEW ===\n\nFile Name: {attachment.file_name}\nCategory: {attachment.category}\nUploader ID: {attachment.uploaded_by}\nDocument ID: {attachment.document_id}\n\n[Content stream preview]")
            return cache_path

    def open_attachment(self, attachment: AttachmentModel, parent: Optional[QWidget] = None) -> bool:
        """
        Launches the attachment in the default system viewer (PDF viewer, Image viewer, etc.).
        """
        if not attachment:
            if parent:
                QMessageBox.warning(parent, "Attachment Error", "Attachment reference is invalid or missing.")
            return False

        path = self._ensure_local_copy(attachment, parent=parent)
        if not path or not os.path.exists(path):
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
        if not attachment:
            if parent:
                QMessageBox.warning(parent, "Download Error", "Attachment reference is invalid.")
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
            target_path = os.path.join(dest_dir, attachment.file_name or "attachment")

        from config.settings import settings
        if settings.is_api_mode and attachment.id:
            from api.client import api_client
            from api.endpoints import Endpoints
            try:
                endpoint = Endpoints.ATTACHMENT_DOWNLOAD(attachment.id)
                api_client.download(endpoint, target_path)
                if parent:
                    QMessageBox.information(
                        parent,
                        "Download Complete",
                        f"Attachment saved successfully:\n{target_path}"
                    )
                return target_path
            except Exception as ex:
                if parent:
                    QMessageBox.critical(parent, "Download Failed", f"Could not download attachment: {str(ex)}")
                return None
        else:
            # Mock mode local file copy
            src_path = self._ensure_local_copy(attachment, parent=parent)
            if not src_path or not os.path.exists(src_path):
                if parent:
                    QMessageBox.warning(parent, "File Error", "Could not locate attachment data to save.")
                return None

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
