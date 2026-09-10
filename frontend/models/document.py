from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.enums import DocumentStatusEnum, PriorityEnum, WorkflowStageEnum
from models.work_assignment import WorkAssignmentModel


@dataclass
class DocumentModel:
    """
    Canonical frontend domain model for a CDTRS document.

    One document remains the single canonical record throughout its
    lifecycle. Routing and work assignments are represented separately.

    Backward-compatible fields such as assigned_employee_id/name and
    doc_assignments are intentionally retained because existing UI
    components still use them.
    """

    id: Optional[int] = None
    reference_no: Optional[str] = None
    title: str = ""
    date: Optional[str] = None
    mode: str = "Government Mail"
    source: Optional[str] = None
    priority: str = "Medium"
    deadline: Optional[str] = None
    status: str = "Received"
    current_stage: str = "DS"

    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None

    current_owner_id: Optional[int] = None
    current_owner_name: Optional[str] = None

    target_department_id: Optional[int] = None
    target_department_name: Optional[str] = None

    # Backward-compatible primary employee fields.
    assigned_employee_id: Optional[int] = None
    assigned_employee_name: Optional[str] = None

    remarks: Optional[str] = None
    action: Optional[str] = None

    # Advisory routing/intelligence fields.
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_employee_id: Optional[int] = None
    suggested_employee_name: Optional[str] = None

    has_director_routing_instruction: bool = False
    director_routing_raw_text: Optional[str] = None
    routing_instruction_confidence: int = 0
    routing_confidence: Optional[float] = None
    confidence: Optional[float] = None
    routing_reason: Optional[str] = None
    is_director_instruction: bool = False

    file_path: Optional[str] = None
    file_type: Optional[str] = None
    format: Optional[str] = None
    ocr_text: Optional[str] = None

    has_prior_director_remark: bool = False

    attachment_count: int = 0
    attachments_list: List[str] = field(default_factory=list)

    # Legacy assignment representation retained for compatibility.
    doc_assignments: List[Dict[str, Any]] = field(default_factory=list)

    # Canonical work assignments.
    work_assignments: List[WorkAssignmentModel] = field(
        default_factory=list
    )

    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Backward-Compatibility Properties
    # ------------------------------------------------------------------

    @property
    def reference(self) -> str:
        """Alias for reference_no."""
        return self.reference_no or (
            f"CDTRS-2026-{self.id:03d}" if self.id else "-"
        )

    @property
    def subject(self) -> str:
        """Alias for title."""
        return self.title

    @property
    def received(self) -> str:
        """Alias for date."""
        return self.date or ""

    @property
    def department(self) -> str:
        """Alias for canonical confirmed target department."""
        return self.target_department_name or "Not Specified"

    @property
    def employee(self) -> str:
        """
        Backward-compatible primary employee display.

        For team assignments, return a useful team summary instead of
        exposing only the first employee.
        """
        team = self.team_assignment

        if team:
            return team.display_assignee

        return self.assigned_employee_name or "Not Assigned"

    # ------------------------------------------------------------------
    # Assignment helpers
    # ------------------------------------------------------------------

    @property
    def active_work_assignments(self) -> List[WorkAssignmentModel]:
        """Returns currently active work assignments."""
        return [
            assignment
            for assignment in self.work_assignments
            if assignment.is_active
        ]

    @property
    def team_assignments(self) -> List[WorkAssignmentModel]:
        """Returns active assignments containing multiple members."""
        return [
            assignment
            for assignment in self.active_work_assignments
            if assignment.is_team or assignment.member_count > 1
        ]

    @property
    def team_assignment(self) -> Optional[WorkAssignmentModel]:
        """
        Returns the first active team assignment, if one exists.
        """
        assignments = self.team_assignments
        return assignments[0] if assignments else None

    @property
    def all_assigned_employee_ids(self) -> List[int]:
        """
        Returns unique active employee/user IDs across all work
        assignments.
        """
        ids: List[int] = []

        for assignment in self.active_work_assignments:
            for user_id in assignment.member_ids:
                if user_id not in ids:
                    ids.append(user_id)

            # Compatibility fallback for older single assignments.
            if (
                assignment.assigned_to_id is not None
                and assignment.assigned_to_id not in ids
            ):
                ids.append(assignment.assigned_to_id)

        # If assignment data is not available, preserve legacy field.
        if not ids and self.assigned_employee_id is not None:
            ids.append(self.assigned_employee_id)

        return ids

    @property
    def all_assigned_employee_names(self) -> List[str]:
        """
        Returns unique active employee names across all work assignments.
        """
        names: List[str] = []

        for assignment in self.active_work_assignments:
            for name in assignment.member_names:
                if name and name not in names:
                    names.append(name)

            if (
                assignment.assigned_to_name
                and assignment.assigned_to_name != "Not Assigned"
                and assignment.assigned_to_name not in names
            ):
                names.append(assignment.assigned_to_name)

        if (
            not names
            and self.assigned_employee_name
            and self.assigned_employee_name != "Not Assigned"
        ):
            names.append(self.assigned_employee_name)

        return names

    @property
    def has_team_assignment(self) -> bool:
        """True when the document has at least one active team assignment."""
        return bool(self.team_assignments)

    @property
    def assignment_count(self) -> int:
        """Number of active work assignments."""
        return len(self.active_work_assignments)

    @property
    def assigned_member_count(self) -> int:
        """Number of unique employees across active assignments."""
        return len(self.all_assigned_employee_ids)

    # ------------------------------------------------------------------
    # Dictionary compatibility
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        Dictionary-like safe getter for seamless transition from legacy
        dictionary-based UI code.
        """
        if hasattr(self, key):
            value = getattr(self, key)
            return value if value is not None else default

        return default

    # ------------------------------------------------------------------
    # API → Domain Model
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentModel":
        """
        Factory constructor for API/JSON dictionaries.

        Accepts both current canonical backend field names and older
        frontend-compatible names.
        """

        raw_date = (
            data.get("date")
            or data.get("received_date")
            or data.get("received")
        )

        raw_deadline = data.get("deadline")

        raw_status = data.get("status", "Received")
        raw_priority = data.get("priority", "Medium")
        raw_stage = data.get("current_stage") or data.get("stage", "DS")

        # --------------------------------------------------------------
        # Work assignments
        # --------------------------------------------------------------

        raw_work_assignments = (
            data.get("work_assignments")
            or data.get("assignments")
            or []
        )

        work_assignments: List[WorkAssignmentModel] = []

        if isinstance(raw_work_assignments, list):
            for assignment in raw_work_assignments:
                try:
                    work_assignments.append(
                        WorkAssignmentModel.from_any(assignment)
                    )
                except Exception:
                    # Keep malformed optional assignment payloads from
                    # preventing the document itself from loading.
                    continue

        # --------------------------------------------------------------
        # Construct document
        # --------------------------------------------------------------

        document = cls(
            id=data.get("id") or data.get("doc_id"),

            reference_no=(
                data.get("reference_no")
                or data.get("reference")
            ),

            title=data.get("title") or data.get("subject", ""),

            date=(
                str(raw_date)
                if raw_date is not None
                else None
            ),

            mode=(
                data.get("mode")
                or data.get("ingestion_mode")
                or "Government Mail"
            ),

            source=data.get("source"),

            priority=PriorityEnum.normalize(
                str(raw_priority)
            ),

            deadline=(
                str(raw_deadline)
                if raw_deadline is not None
                else None
            ),

            status=DocumentStatusEnum.normalize(
                str(raw_status)
            ),

            current_stage=str(raw_stage).upper(),

            director_remark=(
                data.get("director_remark")
                or data.get("director_remarks")
            ),

            hod_remark=(
                data.get("hod_remark")
                or data.get("hod_remarks")
            ),

            current_owner_id=data.get("current_owner_id"),
            current_owner_name=data.get("current_owner_name"),

            target_department_id=data.get(
                "target_department_id"
            ),

            target_department_name=(
                data.get("target_department_name")
                or data.get("department")
            ),

            assigned_employee_id=data.get(
                "assigned_employee_id"
            ),

            assigned_employee_name=(
                data.get("assigned_employee_name")
                or data.get("employee")
            ),

            remarks=data.get("remarks"),
            action=data.get("action"),

            suggested_department_id=data.get(
                "suggested_department_id"
            ),

            suggested_department_name=data.get(
                "suggested_department_name"
            ),

            suggested_employee_id=data.get(
                "suggested_employee_id"
            ),

            suggested_employee_name=data.get(
                "suggested_employee_name"
            ),

            has_director_routing_instruction=bool(
                data.get(
                    "has_director_routing_instruction",
                    data.get("is_director_instruction", False),
                )
            ),

            director_routing_raw_text=(
                data.get("director_routing_raw_text")
                or data.get("routing_reason")
            ),

            routing_instruction_confidence=cls._parse_instruction_confidence(
                data
            ),

            routing_confidence=(
                float(data.get("routing_confidence"))
                if data.get("routing_confidence") is not None
                else (
                    float(data.get("confidence"))
                    if data.get("confidence") is not None
                    else None
                )
            ),

            confidence=(
                float(data.get("confidence"))
                if data.get("confidence") is not None
                else (
                    float(data.get("routing_confidence"))
                    if data.get("routing_confidence") is not None
                    else None
                )
            ),

            routing_reason=data.get("routing_reason"),

            is_director_instruction=bool(
                data.get(
                    "is_director_instruction",
                    data.get(
                        "has_director_routing_instruction",
                        False,
                    ),
                )
            ),

            file_path=data.get("file_path"),

            file_type=(
                data.get("file_type")
                or data.get("format")
            ),

            format=(
                data.get("format")
                or data.get("file_type")
                or "PDF"
            ),

            ocr_text=data.get("ocr_text"),

            has_prior_director_remark=bool(
                data.get("has_prior_director_remark", False)
            ),

            attachment_count=int(
                data.get("attachment_count", 0) or 0
            ),

            attachments_list=(
                data.get("attachments_list")
                or []
            ),

            doc_assignments=(
                data.get("doc_assignments")
                or []
            ),

            work_assignments=work_assignments,

            created_by=data.get("created_by"),

            created_at=(
                str(data.get("created_at"))
                if data.get("created_at") is not None
                else None
            ),

            updated_at=(
                str(data.get("updated_at"))
                if data.get("updated_at") is not None
                else None
            ),
        )

        # --------------------------------------------------------------
        # Compatibility synchronization
        # --------------------------------------------------------------
        #
        # If the canonical assignment list exists, expose its primary
        # member through the old single-assignee fields as well.
        #
        # This lets old UI code continue functioning while newer UI
        # components can use work_assignments directly.

        document._sync_primary_assignment_fields()

        return document

    @staticmethod
    def _parse_instruction_confidence(
        data: Dict[str, Any]
    ) -> int:
        """
        Normalizes routing instruction confidence to an integer
        percentage.
        """
        raw = data.get("routing_instruction_confidence")

        if raw is not None:
            try:
                return int(float(raw))
            except Exception:
                return 0

        routing_confidence = data.get("routing_confidence")

        if routing_confidence is not None:
            try:
                value = float(routing_confidence)

                if value <= 1.0:
                    return round(value * 100)

                return round(value)
            except Exception:
                return 0

        confidence = data.get("confidence")

        if confidence is not None:
            try:
                value = float(confidence)

                if value <= 1.0:
                    return round(value * 100)

                return round(value)
            except Exception:
                return 0

        return 0

    def _sync_primary_assignment_fields(self) -> None:
        """
        Synchronizes legacy single-assignee fields from the active
        canonical work assignments.

        This does NOT replace the full assignment list.
        """

        active = self.active_work_assignments

        if not active:
            return

        # Prefer the first active assignment as the compatibility
        # primary assignment.
        primary = active[0]

        if self.assigned_employee_id is None:
            self.assigned_employee_id = primary.assigned_to_id

        if (
            not self.assigned_employee_name
            or self.assigned_employee_name == "Not Assigned"
        ):
            self.assigned_employee_name = primary.assigned_to_name

        if self.target_department_id is None:
            self.target_department_id = primary.department_id

    # ------------------------------------------------------------------
    # Domain Model → API/Dictionary
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the domain model back to a Python dictionary."""

        return {
            "id": self.id,

            "reference_no": self.reference_no,
            "title": self.title,
            "date": self.date,
            "mode": self.mode,
            "source": self.source,
            "priority": self.priority,
            "deadline": self.deadline,
            "status": self.status,
            "current_stage": self.current_stage,

            "director_remark": self.director_remark,
            "hod_remark": self.hod_remark,

            "current_owner_id": self.current_owner_id,
            "current_owner_name": self.current_owner_name,

            "target_department_id": self.target_department_id,
            "target_department_name": self.target_department_name,

            # Legacy compatibility
            "assigned_employee_id": self.assigned_employee_id,
            "assigned_employee_name": self.assigned_employee_name,

            "remarks": self.remarks,
            "action": self.action,

            # Advisory routing
            "suggested_department_id": self.suggested_department_id,
            "suggested_department_name": self.suggested_department_name,
            "suggested_employee_id": self.suggested_employee_id,
            "suggested_employee_name": self.suggested_employee_name,

            "has_director_routing_instruction": (
                self.has_director_routing_instruction
            ),
            "director_routing_raw_text": (
                self.director_routing_raw_text
            ),
            "routing_instruction_confidence": (
                self.routing_instruction_confidence
            ),
            "routing_confidence": self.routing_confidence,
            "confidence": self.confidence,
            "routing_reason": self.routing_reason,
            "is_director_instruction": (
                self.is_director_instruction
            ),

            "file_path": self.file_path,
            "file_type": self.file_type,
            "format": self.format,
            "ocr_text": self.ocr_text,

            "has_prior_director_remark": (
                self.has_prior_director_remark
            ),

            "attachment_count": self.attachment_count,
            "attachments_list": self.attachments_list,

            # Legacy assignment representation
            "doc_assignments": self.doc_assignments,

            # Canonical assignments
            "work_assignments": [
                assignment.to_dict()
                for assignment in self.work_assignments
            ],

            # Convenience fields for UI consumers
            "has_team_assignment": self.has_team_assignment,
            "assignment_count": self.assignment_count,
            "assigned_member_count": self.assigned_member_count,
            "all_assigned_employee_ids": (
                self.all_assigned_employee_ids
            ),
            "all_assigned_employee_names": (
                self.all_assigned_employee_names
            ),

            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,

            # Existing aliases
            "reference": self.reference,
            "subject": self.subject,
            "received": self.received,
            "department": self.department,
            "employee": self.employee,
        }