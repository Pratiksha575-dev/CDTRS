from typing import Any, Dict, Optional

from repositories.provider import get_repository


class DashboardService:
    """
    Client service providing role-specific dashboard metrics and priority document summaries.
    """

    def __init__(self):
        pass

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves dashboard summary statistics and queue metrics."""
        repo = get_repository()
        return repo.get_dashboard_summary(role=role)


# Global singleton service instance
dashboard_service = DashboardService()
