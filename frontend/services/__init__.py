from services.auth_service import AuthService, auth_service, authenticate
from services.document_service import DocumentService, document_service
from services.routing_service import RoutingService, routing_service
from services.assignment_service import AssignmentService, assignment_service
from services.progress_service import ProgressService, progress_service
from services.workflow_service import WorkflowService, workflow_service
from services.notification_service import NotificationService, notification_service
from services.dashboard_service import DashboardService, dashboard_service
from services.inbox_service import InboxService, inbox_service
from services.ocr_service import OCRService, ocr_service

__all__ = [
    "AuthService",
    "auth_service",
    "authenticate",
    "DocumentService",
    "document_service",
    "RoutingService",
    "routing_service",
    "AssignmentService",
    "assignment_service",
    "ProgressService",
    "progress_service",
    "WorkflowService",
    "workflow_service",
    "NotificationService",
    "notification_service",
    "DashboardService",
    "dashboard_service",
    "InboxService",
    "inbox_service",
    "OCRService",
    "ocr_service",
]
