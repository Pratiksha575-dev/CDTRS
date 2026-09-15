from dataclasses import dataclass
from typing import Any, Dict, Optional
import os


@dataclass
class AttachmentModel:
    """
    Frontend domain model for a document attachment.

    An attachment belongs to a document and may optionally belong to a
    specific ProgressUpdate.

    Operational ownership is not stored here. The uploader is represented
    only by uploaded_by / uploaded_by_name.
    """

    id: Optional[int] = None
    document_id: Optional[int] = None
    progress_update_id: Optional[int] = None

    file_name: str = ""
    file_path: str = ""
    file_type: Optional[str] = None
    file_size: Optional[int] = None

    category: str = "ORIGINAL"
    source: Optional[str] = None

    uploaded_by: Optional[int] = None
    uploaded_by_name: Optional[str] = None

    created_at: Optional[str] = None

    @property
    def extension(self) -> str:
        """Return the file extension without the leading dot."""
        if self.file_name and "." in self.file_name:
            return self.file_name.rsplit(".", 1)[-1].upper()

        if self.file_type:
            return self.file_type.upper().replace(".", "")

        return "FILE"

    @property
    def is_previewable(self) -> bool:
        """Return whether the frontend supports inline preview."""
        return self.extension.lower() in {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "txt",
            "log",
            "docx",
        }

    @property
    def formatted_size(self) -> str:
        """
        Return a human-readable file size.

        Never invent a size. If neither the backend nor a locally available
        file provides the size, return an explicit unknown value.
        """
        size_bytes = self.file_size

        if size_bytes is None and self.file_path:
            try:
                if os.path.isfile(self.file_path):
                    size_bytes = os.path.getsize(self.file_path)
            except (OSError, TypeError):
                size_bytes = None

        if size_bytes is None:
            return "Unknown size"

        try:
            size_bytes = int(size_bytes)
        except (TypeError, ValueError):
            return "Unknown size"

        if size_bytes < 0:
            return "Unknown size"

        if size_bytes < 1024:
            return f"{size_bytes} B"

        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"

        return f"{size_bytes / (1024 * 1024):.1f} MB"

    @classmethod
    def from_dict(
        cls,
        data: Optional[Dict[str, Any]],
    ) -> "AttachmentModel":
        """Build an attachment model from the backend response."""

        if not data:
            return cls()

        raw_category = (
            data.get("category")
            or data.get("attachment_type")
            or "ORIGINAL"
        )

        category = str(raw_category).upper()

        if category == "PROGRESS_ATTACHMENT":
            category = "WORKFLOW"

        elif category in {
            "EMAIL_ATTACHMENT",
            "SUPPORTING_DOCUMENT",
        }:
            category = "ORIGINAL"

        elif category not in {"ORIGINAL", "WORKFLOW"}:
            category = (
                "WORKFLOW"
                if data.get("progress_update_id") is not None
                else "ORIGINAL"
            )

        file_name = data.get("file_name") or "attachment"

        file_type = data.get("file_type")

        if not file_type and "." in file_name:
            file_type = file_name.rsplit(".", 1)[-1].upper()

        return cls(
            id=data.get("id"),
            document_id=data.get("document_id"),
            progress_update_id=data.get("progress_update_id"),
            file_name=file_name,
            file_path=data.get("file_path")
            or data.get("storage_key")
            or "",
            file_type=file_type,
            file_size=data.get("file_size"),
            category=category,
            source=data.get("source"),
            uploaded_by=data.get("uploaded_by"),
            uploaded_by_name=data.get("uploaded_by_name"),
            created_at=(
                str(data.get("created_at"))
                if data.get("created_at") is not None
                else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the canonical attachment model."""

        return {
            "id": self.id,
            "document_id": self.document_id,
            "progress_update_id": self.progress_update_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type or self.extension,
            "file_size": self.file_size,
            "category": self.category,
            "source": self.source,
            "uploaded_by": self.uploaded_by,
            "uploaded_by_name": self.uploaded_by_name,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            "AttachmentModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"progress_update_id={self.progress_update_id}, "
            f"file_name={self.file_name!r}, "
            f"category={self.category!r}, "
            f"uploaded_by={self.uploaded_by})"
        )