from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.enums import DocumentStatusEnum, PriorityEnum
from models.work_assignment import WorkAssignmentModel


@dataclass
class DocumentModel:
    """
    Canonical frontend domain model for a CDTRS document.

    A Document is the common container for the complete lifecycle.

    Operational routing is represented through canonical WorkAssignments.
    A document may have multiple independent workstreams at the same time.

    Examples:

        Document
        ├── HOD Department A
        │      └── WorkAssignment -> Employee A
        │
        ├── HOD Department B
        │      └── WorkAssignment -> Employee B
        │
        └── TSO
               └── WorkAssignment -> TSO

    There is intentionally NO single frontend owner, target department,
    or single operational stage. Those concepts become ambiguous as soon
    as a document has parallel routes.
    """

    # ================================================================
    # DOCUMENT IDENTITY
    # ================================================================

    id: Optional[int] = None
    reference_no: Optional[str] = None
    title: str = ""

    date: Optional[str] = None
    mode: str = "Government Mail"
    source: Optional[str] = None
    priority: str = "Medium"
    deadline: Optional[str] = None

    # Document-level lifecycle status only.
    #
    # This is NOT a representation of which department/person currently
    # owns the document.
    status: str = "Received"
    version: Optional[int] = None
    description: Optional[str] = None
    source_message_id: Optional[int] = None
    ocr_status: Optional[str] = None
    closed_at: Optional[str] = None
    branches: List[Dict[str, Any]] = field(default_factory=list)

    # ================================================================
    # DOCUMENT-LEVEL REVIEW INFORMATION
    # ================================================================

    director_remark: Optional[str] = None
    hod_remark: Optional[str] = None

    remarks: Optional[str] = None
    action: Optional[str] = None

    has_prior_director_remark: bool = False

    # ================================================================
    # ADVISORY ROUTING / INTELLIGENCE
    # ================================================================
    #
    # These are suggestions only. They are NOT actual routing.
    # Actual routing exists in canonical routing branches/work assignments.

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

    # ================================================================
    # FILE / OCR
    # ================================================================

    file_path: Optional[str] = None
    file_type: Optional[str] = None
    format: Optional[str] = None
    ocr_text: Optional[str] = None

    # ================================================================
    # ATTACHMENTS
    # ================================================================

    attachment_count: int = 0
    attachments_list: List[str] = field(default_factory=list)

    # ================================================================
    # CANONICAL OPERATIONAL DATA
    # ================================================================

    work_assignments: List[WorkAssignmentModel] = field(
        default_factory=list
    )

    # ================================================================
    # AUDIT / TIMESTAMPS
    # ================================================================

    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ================================================================
    # BASIC DERIVED INFORMATION
    # ================================================================

    @property
    def reference(self) -> str:
        """Human-readable document reference."""
        return self.reference_no or (
            f"CDTRS-2026-{self.id:03d}" if self.id else "-"
        )

    @property
    def subject(self) -> str:
        """Human-readable subject alias."""
        return self.title

    @property
    def received(self) -> str:
        """Human-readable received date."""
        return self.date or ""

    # ================================================================
    # WORK ASSIGNMENT HELPERS
    # ================================================================

    @property
    def active_work_assignments(self) -> List[WorkAssignmentModel]:
        """
        All currently active operational workstreams.

        This is the authoritative frontend representation of
        operational responsibility.
        """
        return [
            assignment
            for assignment in self.work_assignments
            if assignment.is_active
        ]

    @property
    def team_assignments(self) -> List[WorkAssignmentModel]:
        """
        Active collaborative assignments.

        A team assignment is one WorkAssignment containing multiple
        active members.
        """
        return [
            assignment
            for assignment in self.active_work_assignments
            if assignment.is_team or assignment.member_count > 1
        ]

    @property
    def team_assignment(self) -> Optional[WorkAssignmentModel]:
        """
        Return the first active team assignment.

        This is only a convenience helper. It must NOT be used to
        represent the document's complete operational assignment state.
        """
        assignments = self.team_assignments
        return assignments[0] if assignments else None

    @property
    def assignment_count(self) -> int:
        """Number of active workstreams."""
        return len(self.active_work_assignments)

    @property
    def assigned_member_count(self) -> int:
        """
        Number of unique active users participating in active
        work assignments.
        """
        return len(self.all_assigned_user_ids)

    @property
    def all_assigned_user_ids(self) -> List[int]:
        """
        Return unique active user IDs across all active work assignments.

        This includes:
          - single-person work assignments
          - team members
        """
        ids: List[int] = []

        for assignment in self.active_work_assignments:
            for user_id in assignment.member_ids:
                if user_id is not None and user_id not in ids:
                    ids.append(user_id)

            # A single-user assignment can be represented directly by
            # assigned_to_id without a member row.
            if (
                assignment.assigned_to_id is not None
                and assignment.assigned_to_id not in ids
            ):
                ids.append(assignment.assigned_to_id)

        return ids

    @property
    def all_assigned_user_names(self) -> List[str]:
        """
        Return unique names across all active work assignments.
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

        return names

    @property
    def has_active_work(self) -> bool:
        """True when at least one active workstream exists."""
        return bool(self.active_work_assignments)

    @property
    def has_team_assignment(self) -> bool:
        """True when at least one active team workstream exists."""
        return bool(self.team_assignments)

    # ================================================================
    # WORKSTREAM LOOKUP HELPERS
    # ================================================================

    def get_work_assignment(
        self,
        assignment_id: Optional[int],
    ) -> Optional[WorkAssignmentModel]:
        """
        Find one work assignment by ID.
        """
        if assignment_id is None:
            return None

        for assignment in self.work_assignments:
            if assignment.id == assignment_id:
                return assignment

        return None

    def get_active_work_assignment(
        self,
        assignment_id: Optional[int],
    ) -> Optional[WorkAssignmentModel]:
        """
        Find one active work assignment by ID.
        """
        assignment = self.get_work_assignment(assignment_id)

        if assignment and assignment.is_active:
            return assignment

        return None

    def get_work_assignments_for_user(
        self,
        user_id: Optional[int],
    ) -> List[WorkAssignmentModel]:
        """
        Return all active workstreams in which the given user participates.

        A user participates when they are:
          - the direct assigned_to user, or
          - an active team member.
        """
        if user_id is None:
            return []

        result: List[WorkAssignmentModel] = []

        for assignment in self.active_work_assignments:
            if assignment.assigned_to_id == user_id:
                result.append(assignment)
                continue

            if user_id in assignment.member_ids:
                result.append(assignment)

        return result

    # ================================================================
    # API → DOMAIN MODEL
    # ================================================================

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentModel":
        """
        Construct the canonical frontend document model from API data.

        Only canonical operational data is retained for routing and
        assignment behavior.
        """

        if not data:
            return cls()

        raw_date = (
            data.get("date")
            or data.get("received_date")
            or data.get("received")
        )

        raw_deadline = data.get("deadline")

        raw_status = data.get("status", "Received")

        raw_priority = data.get("priority", "Medium")

        # ------------------------------------------------------------
        # Work assignments
        # ------------------------------------------------------------

        raw_work_assignments = (
            data.get("work_assignments")
            or data.get("assignments")
            or []
        )

        work_assignments: List[WorkAssignmentModel] = []

        raw_branches = data.get("branches") or []
        branch_department_by_id = {}
        if isinstance(raw_branches, list):
            for branch in raw_branches:
                if isinstance(branch, dict) and branch.get("id") is not None:
                    branch_department_by_id[branch.get("id")] = branch.get("department_id")

        if isinstance(raw_work_assignments, list):
            for assignment in raw_work_assignments:
                if not assignment:
                    continue

                try:
                    parsed = WorkAssignmentModel.from_any(assignment)
                    if parsed.department_id is None and parsed.routing_id in branch_department_by_id:
                        parsed.department_id = branch_department_by_id[parsed.routing_id]
                    work_assignments.append(parsed)
                except Exception:
                    continue

        # ------------------------------------------------------------
        # Construct document
        # ------------------------------------------------------------

        return cls(
            id=data.get("id") or data.get("doc_id"),

            reference_no=(
                data.get("reference_no")
                or data.get("reference")
            ),

            title=(
                data.get("title")
                or data.get("subject")
                or ""
            ),

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

            version=data.get("version"),
            description=data.get("description"),
            source_message_id=data.get("source_message_id"),
            ocr_status=(str(data.get("ocr_status")) if data.get("ocr_status") is not None else None),
            closed_at=(str(data.get("closed_at")) if data.get("closed_at") is not None else None),
            branches=[dict(b) for b in raw_branches if isinstance(b, dict)],

            director_remark=(
                data.get("director_remark")
                or data.get("director_remarks")
            ),

            hod_remark=(
                data.get("hod_remark")
                or data.get("hod_remarks")
            ),

            remarks=data.get("remarks"),

            action=data.get("action"),

            # --------------------------------------------------------
            # Advisory routing only
            # --------------------------------------------------------

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
                    data.get(
                        "is_director_instruction",
                        False,
                    ),
                )
            ),

            director_routing_raw_text=(
                data.get("director_routing_raw_text")
                or data.get("routing_reason")
            ),

            routing_instruction_confidence=(
                cls._parse_instruction_confidence(data)
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

            # --------------------------------------------------------
            # Files / OCR
            # --------------------------------------------------------

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

            # --------------------------------------------------------
            # Attachments
            # --------------------------------------------------------

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

            # --------------------------------------------------------
            # Canonical operational assignments
            # --------------------------------------------------------

            work_assignments=work_assignments,

            # --------------------------------------------------------
            # Audit
            # --------------------------------------------------------

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

    # ================================================================
    # ROUTING INTELLIGENCE HELPERS
    # ================================================================

    @staticmethod
    def _parse_instruction_confidence(
        data: Dict[str, Any],
    ) -> int:
        """
        Normalize routing instruction confidence to an integer
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

    # ================================================================
    # DOMAIN MODEL → DICTIONARY
    # ================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the canonical frontend model.

        Routing/assignment information is represented exclusively through
        work_assignments. No synthetic single-owner or single-department
        values are generated.
        """

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
            "version": self.version,
            "description": self.description,
            "source_message_id": self.source_message_id,
            "ocr_status": self.ocr_status,
            "closed_at": self.closed_at,
            "branches": self.branches,

            "director_remark": self.director_remark,
            "hod_remark": self.hod_remark,

            "remarks": self.remarks,
            "action": self.action,

            # Advisory routing intelligence
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

            # Files / OCR
            "file_path": self.file_path,
            "file_type": self.file_type,
            "format": self.format,
            "ocr_text": self.ocr_text,

            "has_prior_director_remark": (
                self.has_prior_director_remark
            ),

            "attachment_count": self.attachment_count,
            "attachments_list": self.attachments_list,

            # Canonical operational state
            "work_assignments": [
                assignment.to_dict()
                for assignment in self.work_assignments
            ],

            # Useful derived values
            "has_active_work": self.has_active_work,
            "has_team_assignment": self.has_team_assignment,
            "assignment_count": self.assignment_count,
            "assigned_member_count": self.assigned_member_count,
            "all_assigned_user_ids": self.all_assigned_user_ids,
            "all_assigned_user_names": self.all_assigned_user_names,

            # Audit
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,

            # Safe identity aliases
            "reference": self.reference,
            "subject": self.subject,
            "received": self.received,
        }

    def __repr__(self) -> str:
        return (
            f"DocumentModel("
            f"id={self.id}, "
            f"reference_no={self.reference_no!r}, "
            f"status={self.status!r}, "
            f"active_workstreams={self.assignment_count})"
        )