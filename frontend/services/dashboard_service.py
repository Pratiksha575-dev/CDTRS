from typing import Any, Dict, Optional

from repositories.provider import get_repository


class DashboardService:
    """Client service for dashboard metrics in the active work context."""

    def __init__(self):
        pass

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        # Do not synthesize or filter dashboard data locally. The backend
        # derives the permitted scope from X-Work-Context-Id.
        return get_repository().get_dashboard_summary(role=role)


dashboard_service = DashboardService()
