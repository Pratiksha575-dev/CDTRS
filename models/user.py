from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class UserModel:
    """
    Frontend domain model representing an authenticated CDTRS user.
    """
    id: int
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        """Constructs UserModel from API response dictionary."""
        return cls(
            id=data.get("id") or 0,
            username=data.get("username", ""),
            full_name=data.get("full_name", data.get("username", "")),
            role=data.get("role", "Employee"),
            email=data.get("email"),
            department_id=data.get("department_id"),
            department_name=data.get("department_name") or data.get("department"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes UserModel to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "is_active": self.is_active,
            "created_at": self.created_at
        }
