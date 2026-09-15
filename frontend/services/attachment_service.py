import os
from typing import List, Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from models.attachment import AttachmentModel
from repositories.provider import get_repository


class AttachmentService:
    """Client attachment service backed by the real repository/API only."""

    def __init__(self):
        pass

    def get_document_attachments(
        self, document_id: int, category: Optional[str] = None
    ) -> List[AttachmentModel]:
        return get_repository().get_attachments(document_id=document_id, category=category)

    def get_progress_attachments(self, progress_update_id: int) -> List[AttachmentModel]:
        # Attachment retrieval by progress update should be exposed by the
        # backend repository. Never inspect private/mock repository state.
        repo = get_repository()
        method = getattr(repo, 'get_progress_attachments', None)
        if not callable(method):
            return []
        return method(progress_update_id) or []

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = 'WORKFLOW',
        source: Optional[str] = None,
    ) -> AttachmentModel:
        if not file_path or not os.path.isfile(file_path):
            raise ValueError('A valid attachment file is required.')
        return get_repository().upload_attachment(
            document_id=document_id,
            file_path=file_path,
            progress_update_id=progress_update_id,
            category=category,
            source=source,
        )

    def _ensure_local_copy(
        self, attachment: AttachmentModel, parent: Optional[QWidget] = None
    ) -> Optional[str]:
        if not attachment or not attachment.id:
            if parent:
                QMessageBox.warning(parent, 'Attachment Error', 'Attachment reference is invalid or missing.')
            return None

        from config.settings import settings
        if not settings.is_api_mode:
            # The final application uses the real backend/API path. A local
            # file is accepted only when the model explicitly points to one.
            path = getattr(attachment, 'file_path', None)
            return os.path.abspath(path) if path and os.path.isfile(path) else None

        cache_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'data', 'cache', 'attachments')
        )
        os.makedirs(cache_dir, exist_ok=True)
        filename = getattr(attachment, 'file_name', None) or 'attachment'
        safe = ''.join(c for c in filename if c.isalnum() or c in '._- ') or 'attachment'
        cache_path = os.path.join(cache_dir, f'{attachment.id}_{safe}')

        if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 0:
            return cache_path

        from api.client import api_client
        from api.endpoints import Endpoints
        try:
            api_client.download(Endpoints.ATTACHMENT_DOWNLOAD(attachment.id), cache_path)
            return cache_path if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 0 else None
        except Exception as exc:
            if parent:
                QMessageBox.warning(parent, 'Download Error', f'Could not retrieve attachment from server: {exc}')
            return None

    def open_attachment(self, attachment: AttachmentModel, parent: Optional[QWidget] = None) -> bool:
        path = self._ensure_local_copy(attachment, parent=parent)
        if not path:
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def download_attachment(
        self, attachment: AttachmentModel, parent: Optional[QWidget] = None, target_path: Optional[str] = None
    ) -> Optional[str]:
        if not attachment:
            return None
        if not target_path:
            directory = QFileDialog.getExistingDirectory(parent, 'Select Download Folder', os.path.expanduser('~'))
            if not directory:
                return None
            target_path = os.path.join(directory, getattr(attachment, 'file_name', None) or 'attachment')

        from config.settings import settings
        if settings.is_api_mode and attachment.id:
            from api.client import api_client
            from api.endpoints import Endpoints
            try:
                api_client.download(Endpoints.ATTACHMENT_DOWNLOAD(attachment.id), target_path)
            except Exception as exc:
                if parent:
                    QMessageBox.critical(parent, 'Download Failed', f'Could not download attachment: {exc}')
                return None
        else:
            source = getattr(attachment, 'file_path', None)
            if not source or not os.path.isfile(source):
                if parent:
                    QMessageBox.warning(parent, 'File Error', 'Attachment is not available locally.')
                return None
            import shutil
            try:
                shutil.copy2(source, target_path)
            except Exception as exc:
                if parent:
                    QMessageBox.critical(parent, 'Download Failed', str(exc))
                return None

        if parent:
            QMessageBox.information(parent, 'Download Complete', f'Attachment saved successfully:\n{target_path}')
        return target_path


attachment_service = AttachmentService()
