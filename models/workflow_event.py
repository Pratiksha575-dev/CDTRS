from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WorkflowEventModel:
    """
    Frontend domain model representing a chronological document-centric activity event.
    """
    id: Optional[int] = None
    document_id: int = 0
    action: str = ""
    from_role: Optional[str] = None
    to_role: Optional[str] = None
    remarks: Optional[str] = None
    details: Optional[str] = None
    performed_by: int = 0
    performed_by_name: Optional[str] = None
    timestamp: Optional[str] = None
    created_at: Optional[str] = None

    # Backward compatibility with existing workflow_history table
    @property
    def user(self) -> str:
        return self.performed_by_name or self.from_role or "System"

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        return default

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowEventModel":
        raw_time = str(data.get("timestamp") or data.get("created_at") or "")
        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            action=data.get("action", ""),
            from_role=data.get("from_role"),
            to_role=data.get("to_role"),
            remarks=data.get("remarks"),
            details=data.get("details"),
            performed_by=data.get("performed_by") or data.get("performed_by_user_id", 0),
            performed_by_name=data.get("performed_by_name") or data.get("user"),
            timestamp=raw_time,
            created_at=raw_time
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "action": self.action,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "remarks": self.remarks,
            "details": self.details,
            "performed_by": self.performed_by,
            "performed_by_name": self.performed_by_name,
            "user": self.user,
            "timestamp": self.timestamp,
            "created_at": self.created_at
        }
