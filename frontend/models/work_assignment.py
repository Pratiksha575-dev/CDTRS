from datetime import datetime
from typing import Any, Dict, List, Optional


class WorkAssignmentMemberModel:
    """
    Represents one employee/member inside a WorkAssignment team.

    A WorkAssignment can contain one or many members. The first/primary
    member may also be represented by WorkAssignment.assigned_to_id for
    backward compatibility with older frontend code.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        work_assignment_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        context_membership_id: Optional[int] = None,
        is_active: bool = True,
        assigned_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ):
        self.id = id
        self.work_assignment_id = work_assignment_id
        self.user_id = user_id
        self.user_name = user_name or "Unknown Employee"
        self.context_membership_id = context_membership_id
        self.is_active = is_active
        self.assigned_at = assigned_at
        self.completed_at = completed_at

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]):
        if not data:
            return cls()

        return cls(
            id=data.get("id"),
            work_assignment_id=data.get(
                "work_assignment_id",
                data.get("assignment_id"),
            ),
            user_id=data.get(
                "user_id",
                data.get("assigned_to_user_id"),
            ),
            user_name=data.get(
                "user_name",
                data.get(
                    "full_name",
                    data.get(
                        "assigned_to_name",
                        data.get("assigned_to_user_name"),
                    ),
                ),
            ),
            context_membership_id=data.get("context_membership_id"),
            is_active=data.get("is_active", True),
            assigned_at=data.get("assigned_at"),
            completed_at=data.get("completed_at"),
        )

    @classmethod
    def from_any(cls, value: Any):
        if isinstance(value, cls):
            return value

        if isinstance(value, dict):
            return cls.from_dict(value)

        return cls(
            id=getattr(value, "id", None),
            work_assignment_id=getattr(
                value,
                "work_assignment_id",
                getattr(value, "assignment_id", None),
            ),
            user_id=getattr(
                value,
                "user_id",
                getattr(value, "assigned_to_user_id", None),
            ),
            user_name=getattr(
                value,
                "user_name",
                getattr(value, "full_name", None),
            ),
            context_membership_id=getattr(
                value,
                "context_membership_id",
                None,
            ),
            is_active=getattr(value, "is_active", True),
            assigned_at=getattr(value, "assigned_at", None),
            completed_at=getattr(value, "completed_at", None),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "work_assignment_id": self.work_assignment_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "context_membership_id": self.context_membership_id,
            "is_active": self.is_active,
            "assigned_at": self.assigned_at,
            "completed_at": self.completed_at,
        }

    @property
    def employee_id(self) -> Optional[int]:
        """Backward-compatible alias."""
        return self.user_id

    @property
    def employee_name(self) -> str:
        """Backward-compatible alias."""
        return self.user_name

    def __repr__(self) -> str:
        return (
            f"WorkAssignmentMemberModel("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"user_name={self.user_name!r}, "
            f"is_active={self.is_active})"
        )


class WorkAssignmentModel:
    """
    Frontend representation of a backend WorkAssignment.

    Supports both:
      1. Legacy single-employee assignments
      2. New team assignments containing multiple members

    The backend remains authoritative for assignment state.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        document_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None,
        assigned_by_name: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        assigned_to_name: Optional[str] = None,
        instructions: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[str] = None,

        # New canonical assignment fields
        department_id: Optional[int] = None,
        routing_id: Optional[int] = None,
        requires_hod_validation: bool = False,
        team_name: Optional[str] = None,
        is_team: bool = False,
        members: Optional[List[Any]] = None,

        # Additional lifecycle fields returned by backend
        assigned_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        change_reason: Optional[str] = None,
    ):
        self.id = id
        self.document_id = document_id

        self.assigned_by_id = assigned_by_id
        self.assigned_by_name = assigned_by_name or "Unknown"

        # Legacy / compatibility primary assignee
        self.assigned_to_id = assigned_to_id
        self.assigned_to_name = assigned_to_name or (
            "Not Assigned" if assigned_to_id is None else "Unknown Employee"
        )

        self.instructions = instructions
        self.is_active = is_active
        self.created_at = created_at

        # Canonical routing/assignment fields
        self.department_id = department_id
        self.routing_id = routing_id
        self.requires_hod_validation = bool(requires_hod_validation)

        self.team_name = team_name
        self.is_team = bool(is_team)

        self.assigned_at = assigned_at or created_at
        self.completed_at = completed_at
        self.change_reason = change_reason

        # Team members
        self.members: List[WorkAssignmentMemberModel] = []

        if members:
            self.members = [
                WorkAssignmentMemberModel.from_any(member)
                for member in members
            ]

        # If multiple members exist, this is a team even when backend did
        # not explicitly include is_team.
        if len(self.members) > 1:
            self.is_team = True

        # If the backend supplied members but omitted the compatibility
        # primary assignee, derive it from the first member.
        if self.members and self.assigned_to_id is None:
            primary = self.members[0]
            self.assigned_to_id = primary.user_id
            self.assigned_to_name = primary.user_name

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]):
        if not data:
            return cls()

        raw_members = (
            data.get("members")
            or data.get("assignment_members")
            or data.get("team_members")
            or []
        )

        # Some backend responses may expose member objects through
        # a nested assignment object.
        if not raw_members and isinstance(data.get("assignment"), dict):
            raw_members = (
                data["assignment"].get("members")
                or data["assignment"].get("assignment_members")
                or []
            )

        return cls(
            id=data.get("id"),
            document_id=data.get(
                "document_id",
                data.get("doc_id"),
            ),

            assigned_by_id=data.get(
                "assigned_by_id",
                data.get("assigned_by_user_id"),
            ),
            assigned_by_name=data.get(
                "assigned_by_name",
                data.get("assigned_by_user_name"),
            ),

            assigned_to_id=data.get(
                "assigned_to_id",
                data.get("assigned_to_user_id"),
            ),
            assigned_to_name=data.get(
                "assigned_to_name",
                data.get(
                    "assigned_to_user_name",
                    data.get("assigned_to_name"),
                ),
            ),

            instructions=data.get("instructions"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),

            department_id=data.get("department_id"),
            routing_id=data.get("routing_id"),
            requires_hod_validation=data.get(
                "requires_hod_validation",
                False,
            ),

            team_name=data.get("team_name"),
            is_team=data.get("is_team", False),

            members=raw_members,

            assigned_at=data.get("assigned_at"),
            completed_at=data.get("completed_at"),
            change_reason=data.get("change_reason"),
        )

    @classmethod
    def from_any(cls, value: Any):
        if isinstance(value, cls):
            return value

        if isinstance(value, dict):
            return cls.from_dict(value)

        members = getattr(value, "members", None)

        return cls(
            id=getattr(value, "id", None),
            document_id=getattr(
                value,
                "document_id",
                getattr(value, "doc_id", None),
            ),

            assigned_by_id=getattr(
                value,
                "assigned_by_id",
                getattr(value, "assigned_by_user_id", None),
            ),
            assigned_by_name=getattr(
                value,
                "assigned_by_name",
                getattr(value, "assigned_by_user_name", None),
            ),

            assigned_to_id=getattr(
                value,
                "assigned_to_id",
                getattr(value, "assigned_to_user_id", None),
            ),
            assigned_to_name=getattr(
                value,
                "assigned_to_name",
                getattr(value, "assigned_to_user_name", None),
            ),

            instructions=getattr(value, "instructions", None),
            is_active=getattr(value, "is_active", True),
            created_at=getattr(value, "created_at", None),

            department_id=getattr(value, "department_id", None),
            routing_id=getattr(value, "routing_id", None),
            requires_hod_validation=getattr(
                value,
                "requires_hod_validation",
                False,
            ),

            team_name=getattr(value, "team_name", None),
            is_team=getattr(value, "is_team", False),
            members=members or [],

            assigned_at=getattr(value, "assigned_at", None),
            completed_at=getattr(value, "completed_at", None),
            change_reason=getattr(value, "change_reason", None),
        )

    # ------------------------------------------------------------------
    # Team helpers
    # ------------------------------------------------------------------

    @property
    def active_members(self) -> List[WorkAssignmentMemberModel]:
        return [
            member
            for member in self.members
            if member.is_active
        ]

    @property
    def member_ids(self) -> List[int]:
        return [
            member.user_id
            for member in self.active_members
            if member.user_id is not None
        ]

    @property
    def member_names(self) -> List[str]:
        return [
            member.user_name
            for member in self.active_members
            if member.user_name
        ]

    @property
    def member_count(self) -> int:
        return len(self.active_members)

    @property
    def primary_member(self) -> Optional[WorkAssignmentMemberModel]:
        if self.active_members:
            return self.active_members[0]

        if self.members:
            return self.members[0]

        return None

    @property
    def display_assignee(self) -> str:
        """
        Human-readable assignment label suitable for tables/cards.
        """

        names = self.member_names

        if len(names) == 1:
            return names[0]

        if len(names) > 1:
            if self.team_name:
                return f"{self.team_name} ({len(names)} members)"

            return f"{len(names)} team members"

        if self.assigned_to_name and self.assigned_to_name != "Not Assigned":
            return self.assigned_to_name

        return "Not Assigned"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,

            "assigned_by_id": self.assigned_by_id,
            "assigned_by_name": self.assigned_by_name,

            # Backward-compatible primary assignee
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_name": self.assigned_to_name,

            "instructions": self.instructions,
            "is_active": self.is_active,
            "created_at": self.created_at,

            # Canonical assignment information
            "department_id": self.department_id,
            "routing_id": self.routing_id,
            "requires_hod_validation": self.requires_hod_validation,

            "team_name": self.team_name,
            "is_team": self.is_team,

            "members": [
                member.to_dict()
                for member in self.members
            ],

            "assigned_at": self.assigned_at,
            "completed_at": self.completed_at,
            "change_reason": self.change_reason,
        }

    def __repr__(self) -> str:
        return (
            f"WorkAssignmentModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"assigned_to_id={self.assigned_to_id}, "
            f"is_team={self.is_team}, "
            f"member_count={self.member_count}, "
            f"is_active={self.is_active})"
        )