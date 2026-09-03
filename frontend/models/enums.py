from enum import Enum


class RoleEnum(str, Enum):
    """Core user roles in CDTRS V2."""
    DIRECTOR_SECRETARY = "Director Secretary"  # DS (Replaces legacy "Master")
    DIRECTOR = "Director"
    HOD = "HOD"
    EMPLOYEE = "Employee"
    TSO = "TSO"
    ADMINISTRATOR = "Administrator"
    READ_ONLY = "Read-only User"

    @classmethod
    def normalize(cls, role_str: str) -> str:
        """Maps legacy role names to V2 standardized names."""
        if not role_str:
            return cls.DIRECTOR_SECRETARY.value
        s = role_str.strip().lower()
        if s in ("master", "ds", "director secretary"):
            return cls.DIRECTOR_SECRETARY.value
        if s in ("director",):
            return cls.DIRECTOR.value
        if s in ("hod",):
            return cls.HOD.value
        if s in ("employee",):
            return cls.EMPLOYEE.value
        if s in ("tso", "technical staff officer"):
            return cls.TSO.value
        if s in ("admin", "administrator"):
            return cls.ADMINISTRATOR.value
        return role_str



class DocumentStatusEnum(str, Enum):
    """User-facing lifecycle statuses for CDTRS V2 documents."""
    RECEIVED = "Received"
    UNDER_DIRECTOR_REVIEW = "Under Director Review"
    DIRECTOR_REVIEW_COMPLETED = "Director Review Completed"
    UNDER_HOD_PROCESSING = "Under HOD Processing"
    ASSIGNED_FOR_EXECUTION = "Assigned for Execution"
    IN_PROGRESS = "In Progress"
    PROGRESS_UPDATED = "Progress Updated"
    PROGRESS_FOLLOWUP_UNDER_REVIEW = "Progress Follow-up Under Review"
    REVIEW_COMPLETED = "Review Completed"
    CLOSED = "Closed"

    @classmethod
    def normalize(cls, val: str) -> str:
        if not val:
            return cls.RECEIVED.value
        s = val.strip()
        # Direct match by value
        for member in cls:
            if member.value.lower() == s.lower():
                return member.value
            if member.name.lower() == s.lower():
                return member.value
        # Uppercase backend enum mapping
        mapping = {
            "RECEIVED": cls.RECEIVED.value,
            "UNDER_DIRECTOR_REVIEW": cls.UNDER_DIRECTOR_REVIEW.value,
            "DIRECTOR_REVIEW_COMPLETED": cls.DIRECTOR_REVIEW_COMPLETED.value,
            "UNDER_HOD_PROCESSING": cls.UNDER_HOD_PROCESSING.value,
            "ASSIGNED_FOR_EXECUTION": cls.ASSIGNED_FOR_EXECUTION.value,
            "IN_PROGRESS": cls.IN_PROGRESS.value,
            "PROGRESS_UPDATED": cls.PROGRESS_UPDATED.value,
            "PROGRESS_FOLLOWUP_UNDER_REVIEW": cls.PROGRESS_FOLLOWUP_UNDER_REVIEW.value,
            "REVIEW_COMPLETED": cls.REVIEW_COMPLETED.value,
            "CLOSED": cls.CLOSED.value,
        }
        return mapping.get(s.upper(), val)


class WorkflowStageEnum(str, Enum):
    """Internal workflow routing stages controlling operational ownership and permissions."""
    DS = "DS"
    DIRECTOR = "DIRECTOR"
    HOD = "HOD"
    EMPLOYEE = "EMPLOYEE"
    CLOSED = "CLOSED"


class PriorityEnum(str, Enum):
    """Business priority levels for CDTRS documents."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    # Color aliases for compatibility
    RED = "High"
    ORANGE = "Medium"
    YELLOW = "Medium"
    GREEN = "Low"

    @classmethod
    def normalize(cls, val: str) -> str:
        if not val:
            return cls.MEDIUM.value
        v = val.strip().lower()
        if v in ("high", "red", "critical", "urgent"):
            return cls.HIGH.value
        if v in ("medium", "orange", "yellow", "normal"):
            return cls.MEDIUM.value
        if v in ("low", "green", "routine"):
            return cls.LOW.value
        return cls.MEDIUM.value


# PZ_26/08: Streamlined IngestionModeEnum to 3 canonical modes (Government Mail, Outlook, Manual Upload)
# with aliases mapping Fax, Physical, Scanned, Direct Submission into Manual Upload.
class IngestionModeEnum(str, Enum):
    """Channels / modes through which documents enter CDTRS."""
    GOVERNMENT_MAIL = "Government Mail"
    OUTLOOK = "Outlook"
    MANUAL_UPLOAD = "Manual Upload"

    # Backward compatibility aliases
    INTERNAL_OUTLOOK = "Outlook"
    EMAIL = "Outlook"
    INTRANET = "Government Mail"
    FAX = "Manual Upload"
    SCANNED = "Manual Upload"
    PHYSICAL = "Manual Upload"
    DIRECT_SUBMISSION = "Manual Upload"
    OTHER = "Manual Upload"

    @classmethod
    def normalize(cls, val: str) -> str:
        if not val:
            return cls.MANUAL_UPLOAD.value
        s = str(val).strip().lower()
        if any(k in s for k in ("gov", "nic", "government")):
            return cls.GOVERNMENT_MAIL.value
        if any(k in s for k in ("outlook", "email", "intranet")):
            return cls.OUTLOOK.value
        if any(k in s for k in ("manual", "scan", "fax", "physical", "direct", "upload")):
            return cls.MANUAL_UPLOAD.value
        for m in cls:
            if m.value.lower() == s:
                return m.value
        return cls.MANUAL_UPLOAD.value


class RouteTypeEnum(str, Enum):
    """Document routing transition categories (DS routing decisions)."""
    DS_TO_DIRECTOR = "DS_TO_DIRECTOR"
    DIRECTOR_TO_DS = "DIRECTOR_TO_DS"
    DS_TO_HOD = "DS_TO_HOD"
    DS_TO_EMPLOYEE = "DS_TO_EMPLOYEE"
    DS_TO_DIRECTOR_FOLLOWUP = "DS_TO_DIRECTOR_FOLLOWUP"
