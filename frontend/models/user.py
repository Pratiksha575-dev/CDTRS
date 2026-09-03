from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import json


from models.enums import RoleEnum


@dataclass
class UserModel:
    """
    Frontend domain model representing an authenticated CDTRS user.
    """
    id: int
    username: str
    full_name: str
    role: str
    employee_code: Optional[str] = None
    designation: Optional[str] = None
    managed_depts: List[str] = field(default_factory=list)
    email: Optional[str] = None
    outlook_email: Optional[str] = None
    gov_email: Optional[str] = None
    preferred_mail_channel: str = "outlook"
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        """Constructs UserModel from API response dictionary."""
        raw_role = data.get("role", "Employee")
        managed = data.get("managed_depts") or []
        if isinstance(managed, str):
            try:
                managed = json.loads(managed) if managed.startswith("[") else [managed]
            except Exception:
                managed = [managed] if managed else []

        return cls(
            id=data.get("id") or 0,
            username=data.get("username", ""),
            full_name=data.get("full_name") or data.get("username", ""),
            role=RoleEnum.normalize(str(raw_role)),
            employee_code=data.get("employee_code"),
            designation=data.get("designation"),
            managed_depts=managed if isinstance(managed, list) else [],
            email=data.get("email"),
            outlook_email=data.get("outlook_email"),
            gov_email=data.get("gov_email"),
            preferred_mail_channel=data.get("preferred_mail_channel", "outlook"),
            department_id=data.get("department_id"),
            department_name=data.get("department_name") or data.get("department"),
            is_active=bool(data.get("is_active", True)),
            created_at=str(data.get("created_at") or "") if data.get("created_at") else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes UserModel to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "employee_code": self.employee_code,
            "designation": self.designation,
            "managed_depts": self.managed_depts,
            "email": self.email,
            "outlook_email": self.outlook_email,
            "gov_email": self.gov_email,
            "preferred_mail_channel": self.preferred_mail_channel,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "is_active": self.is_active,
            "created_at": self.created_at
        }

