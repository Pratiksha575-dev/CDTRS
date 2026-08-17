from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.enums import DocumentStatusEnum, PriorityEnum, WorkflowStageEnum


@dataclass
class DocumentModel:
    """
    Canonical frontend domain model for a CDTRS document.
    Maintains document identity across its entire lifecycle across all roles.
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
    assigned_employee_id: Optional[int] = None
    assigned_employee_name: Optional[str] = None
    remarks: Optional[str] = None
    action: Optional[str] = None
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_employee_id: Optional[int] = None
    suggested_employee_name: Optional[str] = None
    has_director_routing_instruction: bool = False
    director_routing_raw_text: Optional[str] = None
    routing_instruction_confidence: int = 0
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    format: Optional[str] = None
    ocr_text: Optional[str] = None
    has_prior_director_remark: bool = False
    attachment_count: int = 0
    attachments_list: List[str] = field(default_factory=list)
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # --- Backward-Compatibility Properties for UI Components ---

    @property
    def reference(self) -> str:
        """Alias for reference_no."""
        return self.reference_no or (f"CDTRS-2026-{self.id:03d}" if self.id else "-")

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
        """Alias for canonical confirmed target_department_name."""
        return self.target_department_name or "Not Specified"

    @property
    def employee(self) -> str:
        """Alias for canonical confirmed assigned_employee_name."""
        return self.assigned_employee_name or "Not Assigned"

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-like safe getter for seamless transition from legacy dicts."""
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        return default

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentModel":
        """Factory constructor ensuring strict type casting from API/JSON dictionaries."""
        raw_date = data.get("date") or data.get("received_date") or data.get("received")
        raw_deadline = data.get("deadline")
        raw_status = data.get("status", "Received")
        raw_priority = data.get("priority", "Medium")
        raw_stage = data.get("current_stage") or data.get("stage", "DS")

        return cls(
            id=data.get("id") or data.get("doc_id"),
            reference_no=data.get("reference_no") or data.get("reference"),
            title=data.get("title") or data.get("subject", ""),
            date=str(raw_date) if raw_date is not None else None,
            mode=data.get("mode") or data.get("ingestion_mode", "Government Mail"),
            source=data.get("source"),
            priority=PriorityEnum.normalize(str(raw_priority)),
            deadline=str(raw_deadline) if raw_deadline is not None else None,
            status=DocumentStatusEnum.normalize(str(raw_status)),
            current_stage=str(raw_stage).upper(),
            director_remark=data.get("director_remark") or data.get("director_remarks"),
            hod_remark=data.get("hod_remark") or data.get("hod_remarks"),
            current_owner_id=data.get("current_owner_id"),
            current_owner_name=data.get("current_owner_name"),
            target_department_id=data.get("target_department_id"),
            target_department_name=data.get("target_department_name") or data.get("department"),
            assigned_employee_id=data.get("assigned_employee_id"),
            assigned_employee_name=data.get("assigned_employee_name") or data.get("employee"),
            remarks=data.get("remarks"),
            action=data.get("action"),
            suggested_department_id=data.get("suggested_department_id"),
            suggested_department_name=data.get("suggested_department_name"),
            suggested_employee_id=data.get("suggested_employee_id"),
            suggested_employee_name=data.get("suggested_employee_name"),
            has_director_routing_instruction=bool(data.get("has_director_routing_instruction", False)),
            director_routing_raw_text=data.get("director_routing_raw_text"),
            routing_instruction_confidence=int(data.get("routing_instruction_confidence", 0)),
            file_path=data.get("file_path"),
            file_type=data.get("file_type") or data.get("format"),
            format=data.get("format") or data.get("file_type", "PDF"),
            ocr_text=data.get("ocr_text"),
            has_prior_director_remark=bool(data.get("has_prior_director_remark", False)),
            attachment_count=int(data.get("attachment_count", 0)),
            attachments_list=data.get("attachments_list") or [],
            created_by=data.get("created_by"),
            created_at=str(data.get("created_at")) if data.get("created_at") else None,
            updated_at=str(data.get("updated_at")) if data.get("updated_at") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes domain model back to Python dictionary."""
        return {
            "id": self.id,
            "reference_no": self.reference_no,
            "reference": self.reference,
            "title": self.title,
            "subject": self.subject,
            "date": self.date,
            "received": self.received,
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
            "department": self.department,
            "assigned_employee_id": self.assigned_employee_id,
            "assigned_employee_name": self.assigned_employee_name,
            "employee": self.employee,
            "remarks": self.remarks,
            "action": self.action,
            "suggested_department_id": self.suggested_department_id,
            "suggested_department_name": self.suggested_department_name,
            "suggested_employee_id": self.suggested_employee_id,
            "suggested_employee_name": self.suggested_employee_name,
            "has_director_routing_instruction": self.has_director_routing_instruction,
            "director_routing_raw_text": self.director_routing_raw_text,
            "routing_instruction_confidence": self.routing_instruction_confidence,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "format": self.format,
            "ocr_text": self.ocr_text,
            "has_prior_director_remark": self.has_prior_director_remark,
            "attachment_count": self.attachment_count,
            "attachments_list": self.attachments_list,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
