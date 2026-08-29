from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DocumentRouteModel:
    """
    Frontend domain model representing a DS routing transition.
    """
    id: Optional[int] = None
    document_id: int = 0
    route_type: str = "DS_TO_DIRECTOR"
    from_user_id: int = 0
    from_user_name: Optional[str] = None
    to_user_id: Optional[int] = None
    to_user_name: Optional[str] = None
    to_department_id: Optional[int] = None
    to_department_name: Optional[str] = None
    remarks: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentRouteModel":
        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            route_type=data.get("route_type", "DS_TO_DIRECTOR"),
            from_user_id=data.get("from_user_id", 0),
            from_user_name=data.get("from_user_name"),
            to_user_id=data.get("to_user_id"),
            to_user_name=data.get("to_user_name"),
            to_department_id=data.get("to_department_id"),
            to_department_name=data.get("to_department_name"),
            remarks=data.get("remarks"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "route_type": self.route_type,
            "from_user_id": self.from_user_id,
            "from_user_name": self.from_user_name,
            "to_user_id": self.to_user_id,
            "to_user_name": self.to_user_name,
            "to_department_id": self.to_department_id,
            "to_department_name": self.to_department_name,
            "remarks": self.remarks,
            "is_active": self.is_active,
            "created_at": self.created_at
        }
