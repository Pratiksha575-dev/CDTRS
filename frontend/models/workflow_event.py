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
        raw_action = str(data.get("action", ""))

        action_map = {
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
            "PROGRESS_UPDATED": "Progress Update",
            "PROGRESS_SUBMITTED": "Progress Update",
            "FOLLOW_UP_TO_DIRECTOR": "Follow-up to Director",
            "FOLLOW_UP_FORWARDED_TO_DIRECTOR": "Follow-up to Director",
            "DOCUMENT_CLOSED": "Document Closed",
        }
        clean_action = action_map.get(raw_action.upper(), raw_action.replace("_", " ").title())

        display_time = raw_time
        if "T" in raw_time:
            display_time = raw_time.replace("T", " ")[:16]
        elif len(raw_time) > 16:
            display_time = raw_time[:16]

        actor_name = data.get("performed_by_name") or data.get("user")
        if not actor_name or actor_name == "System":
            from_r = data.get("from_role")
            if from_r in ("DS", "ds_user"):
                actor_name = "Director Secretary"
            elif from_r in ("DIRECTOR", "director"):
                actor_name = "The Director"
            elif from_r in ("HOD", "hod"):
                actor_name = "Head of Department"
            elif from_r:
                actor_name = str(from_r).title()
            else:
                actor_name = "Director Secretary"
        else:
            actor_name = (
                str(actor_name)
                .replace(" (DS)", "")
                .replace(" (DIRECTOR)", "")
                .replace(" (HOD)", "")
                .replace(" (EMPLOYEE)", "")
                .replace(" (System)", "")
            )

        return cls(
            id=data.get("id"),
            document_id=data.get("document_id", 0),
            action=clean_action,
            from_role=data.get("from_role"),
            to_role=data.get("to_role"),
            remarks=data.get("remarks") or data.get("details"),
            details=data.get("details") or data.get("remarks"),
            performed_by=data.get("performed_by") or data.get("performed_by_user_id", 0),
            performed_by_name=actor_name,
            timestamp=display_time,
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
