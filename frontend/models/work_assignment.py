from typing import Any, Dict, List, Optional


class WorkAssignmentMemberModel:
    """
    Represents one active or completed member of a WorkAssignment.

    A team WorkAssignment can contain multiple members. Each member
    represents an independent user who is allowed to work on the
    assignment and submit progress against the same work_assignment_id.
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
        self.user_name = user_name or "Unknown User"
        self.context_membership_id = context_membership_id
        self.is_active = bool(is_active)
        self.assigned_at = assigned_at
        self.completed_at = completed_at

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]):
        if not data:
            return cls()

        return cls(
            id=data.get("id"),
            work_assignment_id=data.get("work_assignment_id"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
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

        if value is None:
            return cls()

        return cls(
            id=getattr(value, "id", None),
            work_assignment_id=getattr(
                value,
                "work_assignment_id",
                None,
            ),
            user_id=getattr(value, "user_id", None),
            user_name=getattr(value, "user_name", None),
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

    def __repr__(self) -> str:
        return (
            "WorkAssignmentMemberModel("
            f"id={self.id}, "
            f"work_assignment_id={self.work_assignment_id}, "
            f"user_id={self.user_id}, "
            f"user_name={self.user_name!r}, "
            f"is_active={self.is_active})"
        )


class WorkAssignmentModel:
    """
    Canonical frontend representation of a WorkAssignment.

    A WorkAssignment belongs to exactly one document and one routing
    branch through routing_id.

    Single-user work:
        One WorkAssignment
        assigned_to_id -> individual worker

    Team work:
        One WorkAssignment
        members -> multiple workers

    Every progress update must reference the specific work_assignment_id.
    Therefore different routing branches and different direct employees
    remain independent workstreams.
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
        department_id: Optional[int] = None,
        routing_id: Optional[int] = None,
        requires_hod_validation: bool = False,
        team_name: Optional[str] = None,
        is_team: bool = False,
        members: Optional[List[Any]] = None,
        assigned_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        change_reason: Optional[str] = None,
    ):
        self.id = id
        self.document_id = document_id

        self.assigned_by_id = assigned_by_id
        self.assigned_by_name = assigned_by_name or "Unknown User"

        self.assigned_to_id = assigned_to_id
        self.assigned_to_name = assigned_to_name

        self.instructions = instructions
        self.is_active = bool(is_active)
        self.created_at = created_at

        # Canonical routing relationship.
        self.department_id = department_id
        self.routing_id = routing_id

        self.requires_hod_validation = bool(
            requires_hod_validation
        )

        self.team_name = team_name
        self.is_team = bool(is_team)

        self.assigned_at = assigned_at or created_at
        self.completed_at = completed_at
        self.change_reason = change_reason

        self.members: List[WorkAssignmentMemberModel] = [
            WorkAssignmentMemberModel.from_any(member)
            for member in (members or [])
        ]

        # A multi-member assignment is always a team assignment.
        if len(self.members) > 1:
            self.is_team = True

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]):
        if not data:
            return cls()

        raw_members = data.get("members") or []

        return cls(
            id=data.get("id"),
            document_id=data.get("document_id"),

            assigned_by_id=data.get("assigned_by_id", data.get("assigned_by_user_id")),
            assigned_by_name=data.get("assigned_by_name"),

            assigned_to_id=data.get("assigned_to_id", data.get("assigned_to_user_id")),
            assigned_to_name=data.get("assigned_to_name"),

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

        if value is None:
            return cls()

        members = getattr(value, "members", None) or []

        return cls(
            id=getattr(value, "id", None),
            document_id=getattr(value, "document_id", None),

            assigned_by_id=getattr(
                value,
                "assigned_by_id",
                getattr(value, "assigned_by_user_id", None),
            ),
            assigned_by_name=getattr(
                value,
                "assigned_by_name",
                None,
            ),

            assigned_to_id=getattr(
                value,
                "assigned_to_id",
                getattr(value, "assigned_to_user_id", None),
            ),
            assigned_to_name=getattr(
                value,
                "assigned_to_name",
                None,
            ),

            instructions=getattr(
                value,
                "instructions",
                None,
            ),
            is_active=getattr(
                value,
                "is_active",
                True,
            ),
            created_at=getattr(
                value,
                "created_at",
                None,
            ),

            department_id=getattr(
                value,
                "department_id",
                None,
            ),
            routing_id=getattr(
                value,
                "routing_id",
                None,
            ),

            requires_hod_validation=getattr(
                value,
                "requires_hod_validation",
                False,
            ),

            team_name=getattr(
                value,
                "team_name",
                None,
            ),
            is_team=getattr(
                value,
                "is_team",
                False,
            ),

            members=members,

            assigned_at=getattr(
                value,
                "assigned_at",
                None,
            ),
            completed_at=getattr(
                value,
                "completed_at",
                None,
            ),
            change_reason=getattr(
                value,
                "change_reason",
                None,
            ),
        )

    # ------------------------------------------------------------------
    # Assignment state
    # ------------------------------------------------------------------

    @property
    def active_members(self) -> List[WorkAssignmentMemberModel]:
        """
        Return only currently active team members.
        """
        return [
            member
            for member in self.members
            if member.is_active
        ]

    @property
    def member_ids(self) -> List[int]:
        """
        IDs of all currently active members.
        """
        return [
            member.user_id
            for member in self.active_members
            if member.user_id is not None
        ]

    @property
    def member_names(self) -> List[str]:
        """
        Names of all currently active members.
        """
        return [
            member.user_name
            for member in self.active_members
            if member.user_name
        ]

    @property
    def member_count(self) -> int:
        return len(self.active_members)

    @property
    def primary_member(
        self,
    ) -> Optional[WorkAssignmentMemberModel]:
        """
        Return the first active member of a team.

        This is only a display/convenience concept. It does not mean
        that the first member owns the workstream over other members.
        """
        active = self.active_members

        if active:
            return active[0]

        return None

    # ------------------------------------------------------------------
    # User access helpers
    # ------------------------------------------------------------------

    def contains_user(self, user_id: Optional[int]) -> bool:
        """
        Return True when the given user is an active participant
        in this work assignment.
        """
        if user_id is None:
            return False

        if self.is_team:
            return user_id in self.member_ids

        return (
            self.assigned_to_id is not None
            and self.assigned_to_id == user_id
            and self.is_active
        )

    def is_assigned_to_user(
        self,
        user_id: Optional[int],
    ) -> bool:
        """
        Explicit assignment check used by UI permission decisions.
        """
        return self.contains_user(user_id)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @property
    def display_assignee(self) -> str:
        """
        Human-readable representation of the current workstream.
        """

        if self.is_team:
            names = self.member_names

            if self.team_name and names:
                return f"{self.team_name} ({len(names)} members)"

            if names:
                return f"{len(names)} team members"

            if self.team_name:
                return self.team_name

            return "Team"

        if self.assigned_to_name:
            return self.assigned_to_name

        if self.assigned_to_id is not None:
            return f"User #{self.assigned_to_id}"

        return "Not Assigned"

    @property
    def workstream_label(self) -> str:
        """
        Label suitable for a workstream selector in the document viewer.
        """

        if self.team_name:
            return self.team_name

        if self.is_team:
            return f"Team Assignment #{self.id}"

        if self.assigned_to_name:
            return self.assigned_to_name

        if self.assigned_to_id is not None:
            return f"User #{self.assigned_to_id}"

        return f"Work Assignment #{self.id}"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

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
            "created_at": self.created_at,

            "department_id": self.department_id,
            "routing_id": self.routing_id,
            "requires_hod_validation": (
                self.requires_hod_validation
            ),

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
            "WorkAssignmentModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"routing_id={self.routing_id}, "
            f"assigned_to_id={self.assigned_to_id}, "
            f"is_team={self.is_team}, "
            f"member_count={self.member_count}, "
            f"is_active={self.is_active})"
        )