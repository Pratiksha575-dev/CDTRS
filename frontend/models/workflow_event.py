from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WorkflowEventModel:
    """
    Frontend domain model representing a chronological document activity event.

    The backend action identifier is preserved in `action`.
    `display_action` provides the human-readable label used by the UI.

    WorkflowEventModel is an audit/history model only. It does not represent
    current document ownership, routing state, or active work context.
    """

    id: Optional[int] = None
    document_id: int = 0

    action: str = ""

    from_role: Optional[str] = None
    to_role: Optional[str] = None

    remarks: Optional[str] = None
    details: Optional[str] = None

    performed_by: Optional[int] = None
    performed_by_name: Optional[str] = None

    timestamp: Optional[str] = None
    created_at: Optional[str] = None

    # Backend workflow action -> UI label.
    ACTION_LABELS = {
        "DOCUMENT_RECEIVED": "Document Ingested",
        "DOCUMENT_INGESTED": "Document Ingested",
        "ATTACHMENT_UPLOADED": "Attachment Uploaded",

        "ROUTED_DS_TO_DIRECTOR": "Routed to Director",
        "ROUTED_INITIAL_DIRECTOR_REVIEW": "Routed to Director",

        "DIRECTOR_REMARK_SAVED": "Director Review Completed",

        "RETURNED_TO_DS": "Returned to DS",
        "RETURN_TO_DS": "Returned to DS",

        "ROUTED_DS_TO_HOD": "Routed to Department",
        "ROUTED_POST_REVIEW_TO_HOD": "Routed to Department",

        "ROUTED_DS_TO_EMPLOYEE": "Routed to Staff",
        "ROUTED_POST_REVIEW_TO_EMPLOYEE": "Routed to Staff",

        "HOD_REMARK_SAVED": "HOD Remark Saved",

        "EMPLOYEE_ASSIGNED": "Assigned to Staff",
        "ASSIGNED_TO_EMPLOYEE": "Assigned to Staff",

        # Team / multi-member assignment events.
        "DS_TEAM_ASSIGNED": "DS Assigned Team",
        "HOD_TEAM_ASSIGNED": "HOD Assigned Team",
        "HOD_WORK_ASSIGNED": "HOD Assigned Work",
        "HOD_ASSIGNMENT_UPDATED": "HOD Updated Assignment",
        "HOD_TEAM_CREATED": "HOD Created Team",
        "HOD_ASSIGNMENT_COMPLETED": "HOD Assignment Completed",

        "PROGRESS_UPDATED": "Progress Update",
        "PROGRESS_SUBMITTED": "Progress Update",

        "FOLLOW_UP_TO_DIRECTOR": "Follow-up to Director",
        "FOLLOW_UP_FORWARDED_TO_DIRECTOR": "Follow-up to Director",

        "DOCUMENT_CLOSED": "Document Closed",
    }

    @property
    def display_action(self) -> str:
        """Return the human-readable action label used by the UI."""
        action = str(self.action or "").upper()

        return self.ACTION_LABELS.get(
            action,
            action.replace("_", " ").title(),
        )

    @property
    def actor_name(self) -> str:
        """
        Return the backend-provided actor name.

        Do not invent an actor when the backend does not provide one.
        """
        return self.performed_by_name or "System"

    def get(self, key: str, default: Any = None) -> Any:
        """
        Dictionary-style access retained for UI code that reads models
        generically.
        """
        if hasattr(self, key):
            value = getattr(self, key)
            return value if value is not None else default

        return default

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style indexing for existing UI consumers."""
        if hasattr(self, key):
            return getattr(self, key)

        raise KeyError(key)

    @staticmethod
    def _format_timestamp(value: Any) -> str:
        """Normalize the backend timestamp for display."""
        if value is None:
            return ""

        raw_time = str(value)

        if not raw_time:
            return ""

        if "T" in raw_time:
            return raw_time.replace("T", " ")[:16]

        return raw_time[:16]

    @classmethod
    def from_dict(
        cls,
        data: Optional[Dict[str, Any]],
    ) -> "WorkflowEventModel":
        """Create a model from a backend workflow-event response."""

        if not data:
            return cls()

        raw_time = str(
            data.get("timestamp")
            or data.get("created_at")
            or ""
        )

        raw_action = str(
            data.get("action")
            or ""
        )

        performed_by = (
            data.get("performed_by")
            if data.get("performed_by") is not None
            else data.get("performed_by_user_id")
        )

        performed_by_name = (
            data.get("performed_by_name")
            or data.get("actor_name")
            or data.get("user_name")
        )

        remarks = (
            data.get("remarks")
            or data.get("details")
        )

        details = (
            data.get("details")
            or data.get("remarks")
        )

        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),

            # Preserve the canonical backend action.
            action=raw_action,

            from_role=data.get("from_role"),
            to_role=data.get("to_role"),

            remarks=remarks,
            details=details,

            performed_by=performed_by,
            performed_by_name=performed_by_name,

            timestamp=cls._format_timestamp(raw_time),
            created_at=raw_time,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the workflow event for frontend use."""

        return {
            "id": self.id,
            "document_id": self.document_id,
            "action": self.action,
            "display_action": self.display_action,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "remarks": self.remarks,
            "details": self.details,
            "performed_by": self.performed_by,
            "performed_by_name": self.performed_by_name,
            "actor_name": self.actor_name,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            "WorkflowEventModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"action={self.action!r}, "
            f"performed_by={self.performed_by})"
        )