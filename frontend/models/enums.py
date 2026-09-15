from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    DS = "DS"
    DIRECTOR_SECRETARY = "DS"
    DIRECTOR = "DIRECTOR"
    HOD = "HOD"
    EMPLOYEE = "EMPLOYEE"
    TSO = "TSO"

    @classmethod
    def normalize(cls, value) -> str:
        """
        Normalize backend/frontend role values to the canonical
        operational context type.
        """
        if value is None:
            return ""

        text = str(value).strip().upper()

        aliases = {
            "ADMINISTRATOR": cls.ADMIN.value,
            "MASTER": cls.ADMIN.value,
            "DIRECTOR_SECRETARY": cls.DS.value,
            "DIRECTOR SECRETARY": cls.DS.value,
            "SECRETARY": cls.DS.value,
            "HEAD OF DEPARTMENT": cls.HOD.value,
            "HEAD_OF_DEPARTMENT": cls.HOD.value,
            "TECHNICAL SUPPORT OFFICER": cls.TSO.value,
            "TECHNICAL_SUPPORT_OFFICER": cls.TSO.value,
        }

        return aliases.get(text, text)


class DocumentStatusEnum(str, Enum):
    RECEIVED = "RECEIVED"
    UNDER_DIRECTOR_REVIEW = "UNDER_DIRECTOR_REVIEW"
    RETURNED_TO_DS = "RETURNED_TO_DS"
    UNDER_HOD_PROCESSING = "UNDER_HOD_PROCESSING"
    ASSIGNED_FOR_EXECUTION = "ASSIGNED_FOR_EXECUTION"
    PROGRESS_UPDATED = "PROGRESS_UPDATED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    DIRECTOR_REVIEW_COMPLETED = "RETURNED_TO_DS"

    @classmethod
    def normalize(cls, value) -> str:
        if value is None:
            return ""

        text = str(value).strip()

        aliases = {
            "Director Review": cls.UNDER_DIRECTOR_REVIEW.value,
            "Under Director Review": cls.UNDER_DIRECTOR_REVIEW.value,
            "Director Review Completed": cls.RETURNED_TO_DS.value,
            "DIRECTOR_REVIEW_COMPLETED": cls.RETURNED_TO_DS.value,
            "Returned to DS": cls.RETURNED_TO_DS.value,
            "Under HOD Processing": cls.UNDER_HOD_PROCESSING.value,
            "Assigned for Execution": cls.ASSIGNED_FOR_EXECUTION.value,
            "Progress Updated": cls.PROGRESS_UPDATED.value,
            "Completed": cls.COMPLETED.value,
            "Closed": cls.CLOSED.value,
            "Cancelled": cls.CANCELLED.value,
        }

        return aliases.get(text, text.upper().replace(" ", "_"))


class PriorityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def normalize(cls, value) -> str:
        if value is None:
            return cls.MEDIUM.value

        text = str(value).strip().upper()

        aliases = {
            "CRITICAL": cls.CRITICAL.value,
            "URGENT": cls.CRITICAL.value,
            "RED": cls.CRITICAL.value,
            "NORMAL": cls.MEDIUM.value,
            "ORANGE": cls.MEDIUM.value,
            "YELLOW": cls.MEDIUM.value,

            "GREEN": cls.LOW.value,
        }

        return aliases.get(text, text)


class IngestionModeEnum(str, Enum):
    GOVERNMENT_MAIL = "GOVERNMENT_MAIL"
    OUTLOOK = "OUTLOOK"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"

    @classmethod
    def normalize(cls, value) -> str:
        if value is None:
            return ""

        text = str(value).strip().upper()

        aliases = {
            "GOVERNMENT MAIL": cls.GOVERNMENT_MAIL.value,
            "GOVT MAIL": cls.GOVERNMENT_MAIL.value,
            "GOVT_MAIL": cls.GOVERNMENT_MAIL.value,

            "OUTLOOK MAIL": cls.OUTLOOK.value,
            "OUTLOOK_EMAIL": cls.OUTLOOK.value,

            "MANUAL UPLOAD": cls.MANUAL_UPLOAD.value,
            "MANUAL": cls.MANUAL_UPLOAD.value,
        }

        return aliases.get(text, text)


class WorkflowStageEnum(str, Enum):
    """Display/workflow stage derived from document lifecycle state."""
    DS = "DS"
    DIRECTOR = "DIRECTOR"
    HOD = "HOD"
    EMPLOYEE = "EMPLOYEE"
    TSO = "TSO"
    CLOSED = "CLOSED"


class RouteTypeEnum(str, Enum):
    """
    Canonical operational routing branch types.

    These represent actual routing branches, not workflow history
    transitions such as DS_TO_DIRECTOR.
    """

    DEPARTMENT_HOD = "DEPARTMENT_HOD"
    DIRECT_EMPLOYEE = "DIRECT_EMPLOYEE"
    TSO = "TSO"

    @classmethod
    def normalize(cls, value) -> str:
        if value is None:
            return ""

        text = str(value).strip().upper()

        aliases = {
            "DEPARTMENT HOD": cls.DEPARTMENT_HOD.value,
            "HOD": cls.DEPARTMENT_HOD.value,

            "DIRECT EMPLOYEE": cls.DIRECT_EMPLOYEE.value,
            "EMPLOYEE": cls.DIRECT_EMPLOYEE.value,

            "TECHNICAL SUPPORT OFFICER": cls.TSO.value,
            "TECHNICAL_SUPPORT_OFFICER": cls.TSO.value,
        }

        return aliases.get(text, text)