from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import json

from models.enums import RoleEnum


@dataclass
class ContextMembershipModel:
    """One operational identity/context available to the authenticated user."""
    id: int
    user_id: int
    context_type: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextMembershipModel":
        raw_type = data.get("context_type") or data.get("role") or data.get("type") or "EMPLOYEE"
        context_type = str(raw_type).strip()
        try:
            context_type = RoleEnum.normalize(context_type)
        except Exception:
            pass
        return cls(
            id=int(data.get("id") or 0),
            user_id=int(data.get("user_id") or 0),
            context_type=context_type,
            department_id=data.get("department_id"),
            department_name=data.get("department_name") or data.get("department"),
            department_code=data.get("department_code"),
            is_active=bool(data.get("is_active", True)),
            created_at=str(data.get("created_at")) if data.get("created_at") is not None else None,
            updated_at=str(data.get("updated_at")) if data.get("updated_at") is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "context_type": self.context_type,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "department_code": self.department_code,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @property
    def role(self) -> str:
        return self.context_type


@dataclass
class UserModel:
    """
    Authenticated CDTRS user.

    ``role`` remains for compatibility. Operational permissions/scope come
    from the active WorkContextMembership.
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
    context_memberships: List[ContextMembershipModel] = field(default_factory=list)
    active_context_id: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        raw_role = data.get("role", "Employee")

        managed = data.get("managed_depts") or []
        if isinstance(managed, str):
            try:
                managed = json.loads(managed) if managed.startswith("[") else [managed]
            except Exception:
                managed = [managed] if managed else []
        if not isinstance(managed, list):
            managed = []

        raw_contexts = data.get("context_memberships") or data.get("contexts") or []
        contexts = [
            ContextMembershipModel.from_dict(c)
            for c in raw_contexts
            if isinstance(c, dict)
        ]

        active_context_id = (
            data.get("active_context_id")
            or data.get("active_context_membership_id")
        )
        if active_context_id is None:
            active = next((c for c in contexts if c.is_active), None)
            if active:
                active_context_id = active.id

        return cls(
            id=int(data.get("id") or 0),
            username=data.get("username", ""),
            full_name=data.get("full_name") or data.get("username", ""),
            role=RoleEnum.normalize(str(raw_role)),
            employee_code=data.get("employee_code"),
            designation=data.get("designation"),
            managed_depts=managed,
            email=data.get("email"),
            outlook_email=data.get("outlook_email"),
            gov_email=data.get("gov_email"),
            preferred_mail_channel=data.get("preferred_mail_channel", "outlook"),
            department_id=data.get("department_id"),
            department_name=data.get("department_name") or data.get("department"),
            is_active=bool(data.get("is_active", True)),
            created_at=str(data.get("created_at")) if data.get("created_at") is not None else None,
            context_memberships=contexts,
            active_context_id=int(active_context_id) if active_context_id is not None else None,
        )

    def get_contexts(self) -> List[ContextMembershipModel]:
        return list(self.context_memberships)

    def set_contexts(self, contexts: List[Dict[str, Any]]) -> None:
        self.context_memberships = [
            ContextMembershipModel.from_dict(c)
            for c in contexts
            if isinstance(c, dict)
        ]
        if self.active_context_id is not None and self.set_active_context(self.active_context_id):
            return
        active = next(
            (c for c in self.context_memberships if c.is_active),
            self.context_memberships[0] if self.context_memberships else None,
        )
        if active:
            self.active_context_id = active.id
            self._apply_active_context(active)

    @property
    def active_context(self) -> Optional[ContextMembershipModel]:
        if self.active_context_id is not None:
            for context in self.context_memberships:
                if context.id == self.active_context_id:
                    return context
        return next((c for c in self.context_memberships if c.is_active), None)

    @property
    def active_role(self) -> str:
        context = self.active_context
        return context.context_type if context else self.role

    def set_active_context(self, context_id: int) -> bool:
        selected = None
        for context in self.context_memberships:
            context.is_active = context.id == int(context_id)
            if context.is_active:
                selected = context
        if selected is None:
            return False
        self.active_context_id = selected.id
        self._apply_active_context(selected)
        return True

    def _apply_active_context(self, context: ContextMembershipModel) -> None:
        self.role = RoleEnum.normalize(context.context_type)
        self.department_id = context.department_id
        self.department_name = context.department_name

    def to_dict(self) -> Dict[str, Any]:
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
            "created_at": self.created_at,
            "active_context_id": self.active_context_id,
            "active_context_membership_id": self.active_context_id,
            "context_memberships": [c.to_dict() for c in self.context_memberships],
        }
