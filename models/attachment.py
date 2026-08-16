from dataclasses import dataclass
from typing import Any, Dict, Optional
import os


@dataclass
class AttachmentModel:
    """
    Frontend domain model representing a file attachment (original source dispatch or workflow progress).
    Retains the exact user identity who attached/uploaded the file (uploaded_by / attached_by_id).
    """
    id: Optional[int] = None
    document_id: int = 0
    progress_update_id: Optional[int] = None
    file_name: str = ""
    file_path: str = ""
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    category: str = "ORIGINAL"  # "ORIGINAL" or "WORKFLOW"
    source: Optional[str] = None  # e.g. "Government Mail", "Internal Outlook", "Manual Upload", "Employee Progress"
    uploaded_by: int = 0
    uploaded_by_name: Optional[str] = None
    created_at: Optional[str] = None

    @property
    def attached_by_id(self) -> int:
        """Alias for uploaded_by representing user who attached the file."""
        return self.uploaded_by

    @attached_by_id.setter
    def attached_by_id(self, val: int):
        self.uploaded_by = val

    @property
    def uploaded_by_id(self) -> int:
        """Alias for uploaded_by."""
        return self.uploaded_by

    @uploaded_by_id.setter
    def uploaded_by_id(self, val: int):
        self.uploaded_by = val

    @property
    def attached_by_name(self) -> Optional[str]:
        """Alias for uploaded_by_name."""
        return self.uploaded_by_name

    @attached_by_name.setter
    def attached_by_name(self, val: Optional[str]):
        self.uploaded_by_name = val

    @property
    def uploaded_at(self) -> Optional[str]:
        """Alias for created_at."""
        return self.created_at

    @uploaded_at.setter
    def uploaded_at(self, val: Optional[str]):
        self.created_at = val

    @property
    def extension(self) -> str:
        """Returns uppercase file extension without dot."""
        if self.file_name and "." in self.file_name:
            return self.file_name.rsplit(".", 1)[-1].upper()
        if self.file_type:
            return self.file_type.upper().replace(".", "")
        return "FILE"

    @property
    def is_previewable(self) -> bool:
        """Whether the file format can be previewed inside the application."""
        ext = self.extension.lower()
        return ext in ("pdf", "png", "jpg", "jpeg", "txt", "log", "docx")

    @property
    def formatted_size(self) -> str:
        """Returns human-readable file size."""
        if not self.file_size:
            if self.file_path and os.path.exists(self.file_path):
                size_bytes = os.path.getsize(self.file_path)
            else:
                return "145 KB"
        else:
            size_bytes = self.file_size

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttachmentModel":
        uploaded_by_val = (
            data.get("uploaded_by_user_id")
            or data.get("uploaded_by")
            or data.get("attached_by_id")
            or data.get("uploaded_by_id")
            or 0
        )
        uploaded_by_name_val = (
            data.get("uploaded_by_name")
            or data.get("attached_by_name")
        )
        created_at_val = (
            data.get("created_at")
            or data.get("uploaded_at")
        )
        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            progress_update_id=data.get("progress_update_id"),
            file_name=data.get("file_name", "attachment"),
            file_path=data.get("file_path", ""),
            file_type=data.get("file_type") or (data.get("file_name", "").rsplit(".", 1)[-1].upper() if "." in data.get("file_name", "") else "PDF"),
            file_size=data.get("file_size"),
            category=data.get("category", "ORIGINAL"),
            source=data.get("source"),
            uploaded_by=uploaded_by_val,
            uploaded_by_name=uploaded_by_name_val,
            created_at=created_at_val
        )

    def to_dict(self) -> Dict[str, Any]:
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
            "attached_by_id": self.uploaded_by,
            "uploaded_by_id": self.uploaded_by,
            "uploaded_by_name": self.uploaded_by_name,
            "attached_by_name": self.uploaded_by_name,
            "created_at": self.created_at,
            "uploaded_at": self.created_at
        }
