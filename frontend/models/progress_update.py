from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.attachment import AttachmentModel


@dataclass
class ProgressUpdateModel:
    """
    Canonical frontend model for a progress report.

    Every progress update belongs to:
        Document -> WorkAssignment -> ProgressUpdate

    `work_assignment_id` is therefore required conceptually even though
    it remains Optional at the model level so partially populated API
    responses can still be represented safely.

    This is important when a document has multiple independent
    workstreams. Each employee's progress must remain attached to the
    specific WorkAssignment they are working on.
    """

    id: Optional[int] = None

    # Document to which this progress report belongs.
    document_id: int = 0

    # Specific workstream/assignment for this progress report.
    work_assignment_id: Optional[int] = None

    # User who submitted the progress report.
    user_id: int = 0
    user_name: Optional[str] = None

    description: str = ""
    created_at: Optional[str] = None

    attachments: List[AttachmentModel] = field(
        default_factory=list
    )

    # HOD validation workflow.
    hod_validation_required: bool = False
    hod_validation_status: str = "DIRECT_TO_DS"
    hod_review_note: Optional[str] = None
    hod_reviewed_by_user_id: Optional[int] = None
    hod_reviewer_name: Optional[str] = None
    hod_reviewed_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Optional[Dict[str, Any]],
    ) -> "ProgressUpdateModel":
        if not data:
            return cls()

        raw_attachments = data.get("attachments") or []

        parsed_attachments = [
            AttachmentModel.from_dict(att)
            if isinstance(att, dict)
            else att
            for att in raw_attachments
        ]

        return cls(
            id=data.get("id"),

            document_id=data.get(
                "document_id",
                0,
            ),

            work_assignment_id=data.get(
                "work_assignment_id"
            ),

            user_id=data.get(
                "user_id",
                data.get(
                    "submitted_by_user_id",
                    0,
                ),
            ) or 0,

            user_name=data.get(
                "user_name"
            ),

            description=data.get(
                "description",
                "",
            ),

            created_at=(
                str(data.get("created_at"))
                if data.get("created_at") is not None
                else None
            ),

            attachments=parsed_attachments,

            hod_validation_required=bool(
                data.get(
                    "hod_validation_required",
                    False,
                )
            ),

            hod_validation_status=str(
                data.get(
                    "hod_validation_status"
                )
                or "DIRECT_TO_DS"
            ),

            hod_review_note=data.get(
                "hod_review_note"
            ),

            hod_reviewed_by_user_id=data.get(
                "hod_reviewed_by_user_id"
            ),

            hod_reviewer_name=data.get(
                "hod_reviewer_name"
            ),

            hod_reviewed_at=(
                str(data.get("hod_reviewed_at"))
                if data.get("hod_reviewed_at") is not None
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,

            "document_id": self.document_id,

            "work_assignment_id": self.work_assignment_id,

            "user_id": self.user_id,
            "user_name": self.user_name,

            "description": self.description,
            "created_at": self.created_at,

            "attachments": [
                attachment.to_dict()
                for attachment in self.attachments
            ],

            "hod_validation_required": (
                self.hod_validation_required
            ),

            "hod_validation_status": (
                self.hod_validation_status
            ),

            "hod_review_note": self.hod_review_note,

            "hod_reviewed_by_user_id": (
                self.hod_reviewed_by_user_id
            ),

            "hod_reviewer_name": (
                self.hod_reviewer_name
            ),

            "hod_reviewed_at": (
                self.hod_reviewed_at
            ),
        }

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def has_work_assignment(self) -> bool:
        """
        True when this progress report is explicitly attached
        to a WorkAssignment.
        """
        return self.work_assignment_id is not None

    @property
    def is_hod_validation_pending(self) -> bool:
        """
        True when the progress report requires HOD validation
        and has not yet been completed/rejected.
        """
        if not self.hod_validation_required:
            return False

        return self.hod_validation_status.upper() in {
            "PENDING",
            "PENDING_HOD_VALIDATION",
            "SUBMITTED",
        }

    def __repr__(self) -> str:
        return (
            "ProgressUpdateModel("
            f"id={self.id}, "
            f"document_id={self.document_id}, "
            f"work_assignment_id={self.work_assignment_id}, "
            f"user_id={self.user_id}, "
            f"user_name={self.user_name!r})"
        )