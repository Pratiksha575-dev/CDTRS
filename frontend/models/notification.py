from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class NotificationModel:
    """
    Frontend domain model representing an in-app user activity alert.
    """
    id: Optional[int] = None
    user_id: int = 0
    document_id: Optional[int] = None
    document_reference: Optional[str] = None
    title: str = ""
    message: str = ""
    is_read: bool = False
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationModel":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", 0),
            document_id=data.get("document_id"),
            document_reference=data.get("document_reference") or data.get("reference"),
            title=data.get("title", ""),
            message=data.get("message", ""),
            is_read=data.get("is_read", False),
            created_at=data.get("created_at")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "document_reference": self.document_reference,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at
        }
