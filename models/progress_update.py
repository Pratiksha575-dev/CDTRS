from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.attachment import AttachmentModel


@dataclass
class ProgressUpdateModel:
    """
    Frontend domain model representing an Employee progress report entry.
    Supports free-text descriptions and optional supporting file attachments.
    """
    id: Optional[int] = None
    document_id: int = 0
    user_id: int = 0
    user_name: Optional[str] = None
    description: str = ""
    created_at: Optional[str] = None
    attachments: List[AttachmentModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressUpdateModel":
        raw_attachments = data.get("attachments") or []
        parsed_attachments = [
            AttachmentModel.from_dict(att) if isinstance(att, dict) else att
            for att in raw_attachments
        ]

        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            user_id=data.get("user_id") or data.get("submitted_by_user_id", 0),
            user_name=data.get("user_name"),
            description=data.get("description", ""),
            created_at=str(data.get("created_at") or ""),
            attachments=parsed_attachments
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "description": self.description,
            "created_at": self.created_at,
            "attachments": [att.to_dict() for att in self.attachments]
        }
