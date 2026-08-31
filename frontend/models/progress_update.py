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
    hod_validation_required: bool = False
    hod_validation_status: str = "DIRECT_TO_DS"
    hod_review_note: Optional[str] = None
    hod_reviewed_by_user_id: Optional[int] = None
    hod_reviewer_name: Optional[str] = None
    hod_reviewed_at: Optional[str] = None

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
            attachments=parsed_attachments,
            hod_validation_required=bool(data.get("hod_validation_required", False)),
            hod_validation_status=str(data.get("hod_validation_status") or "DIRECT_TO_DS"),
            hod_review_note=data.get("hod_review_note"),
            hod_reviewed_by_user_id=data.get("hod_reviewed_by_user_id"),
            hod_reviewer_name=data.get("hod_reviewer_name"),
            hod_reviewed_at=str(data.get("hod_reviewed_at")) if data.get("hod_reviewed_at") else None
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "description": self.description,
            "created_at": self.created_at,
            "attachments": [att.to_dict() for att in self.attachments],
            "hod_validation_required": self.hod_validation_required,
            "hod_validation_status": self.hod_validation_status,
            "hod_review_note": self.hod_review_note,
            "hod_reviewed_by_user_id": self.hod_reviewed_by_user_id,
            "hod_reviewer_name": self.hod_reviewer_name,
            "hod_reviewed_at": self.hod_reviewed_at
        }
