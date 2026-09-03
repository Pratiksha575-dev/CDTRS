from typing import Any, Dict, Optional

from models.user import UserModel
from repositories.provider import get_repository


class AuthService:
    """
    Client authentication and active session management service.
    Coordinates authentication requests through the repository layer.
    """

    def __init__(self):
        self._repository = get_repository()
        self._active_department: Optional[str] = None
        self._active_role: Optional[str] = None

    def login(self, username: str, password: str) -> Optional[UserModel]:
        """Authenticates user credentials and establishes active session."""
        repo = get_repository()
        user = repo.authenticate(username, password)
        if user:
            # Set default active department and active role
            self._active_role = user.role
            if user.managed_depts and len(user.managed_depts) > 0 and user.managed_depts[0] != "*":
                self._active_department = user.managed_depts[0]
            else:
                self._active_department = user.department_name

            from config.settings import settings
            if settings.is_api_mode:
                from services.websocket_service import websocket_service
                websocket_service.connect_client()
        return user

    def logout(self) -> None:
        """Terminates active session."""
        self._active_department = None
        self._active_role = None
        try:
            from services.websocket_service import websocket_service
            websocket_service.disconnect_client()
        except Exception:
            pass
        repo = get_repository()
        repo.logout()

    def get_current_user(self) -> Optional[UserModel]:
        """Returns currently authenticated user profile."""
        repo = get_repository()
        return repo.get_current_user()

    def is_authenticated(self) -> bool:
        """Checks if a user session is actively authenticated."""
        return self.get_current_user() is not None

    def get_active_department(self) -> Optional[str]:
        """Returns the currently active department context."""
        if self._active_department:
            return self._active_department
        u = self.get_current_user()
        return u.department_name if u else None

    def set_active_department(self, dept_name: str) -> None:
        """Switches active department for multi-dept HODs."""
        self._active_department = dept_name

    def get_active_role(self) -> str:
        """Returns currently active persona role."""
        if self._active_role:
            return self._active_role
        u = self.get_current_user()
        return u.role if u else "Employee"

    def set_active_role(self, role_name: str) -> None:
        """Switches active role for dual-role users (Employee <-> HOD)."""
        self._active_role = role_name

    def get_managed_departments(self) -> list:
        """Returns list of departments managed by the current user."""
        u = self.get_current_user()
        if not u:
            return []
        depts = [d for d in u.managed_depts if d != "*"]
        if u.department_name and u.department_name not in depts:
            depts.append(u.department_name)
        return depts

    def reset_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Resets user password through repository layer verifying current password."""
        repo = get_repository()
        return repo.reset_password(username, old_password, new_password)



# Global singleton service instance
auth_service = AuthService()


# =========================================================
# BACKWARD COMPATIBILITY FUNCTION FOR EXISTING LOGIN UI
# =========================================================

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Backward compatibility adapter for existing ui/login.py.
    Routes authentication through AuthService and returns dict expected by legacy UI.
    """
    user = auth_service.login(username, password)
    if user:
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "department_id": user.department_id,
            "department": user.department_name
        }
    return None