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

    def login(self, username: str, password: str) -> Optional[UserModel]:
        """Authenticates user credentials and establishes active session."""
        repo = get_repository()
        user = repo.authenticate(username, password)
        if user:
            from config.settings import settings
            if settings.is_api_mode:
                from services.websocket_service import websocket_service
                websocket_service.connect_client()
        return user

    def logout(self) -> None:
        """Terminates active session."""
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