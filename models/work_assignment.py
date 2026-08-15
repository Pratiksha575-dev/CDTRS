from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WorkAssignmentModel:
    """
    Frontend domain model representing an HOD -> Employee work assignment.
    """
    id: Optional[int] = None
    document_id: int = 0
    assigned_by_id: int = 0
    assigned_by_name: Optional[str] = None
    assigned_to_id: int = 0
    assigned_to_name: Optional[str] = None
    instructions: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkAssignmentModel":
        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            assigned_by_id=data.get("assigned_by_id", 0),
            assigned_by_name=data.get("assigned_by_name"),
            assigned_to_id=data.get("assigned_to_id", 0),
            assigned_to_name=data.get("assigned_to_name"),
            instructions=data.get("instructions"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "assigned_by_id": self.assigned_by_id,
            "assigned_by_name": self.assigned_by_name,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_name": self.assigned_to_name,
            "instructions": self.instructions,
            "is_active": self.is_active,
            "created_at": self.created_at
        }
