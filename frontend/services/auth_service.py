from typing import Any, Dict, Optional, List

from models.user import UserModel
from repositories.provider import get_repository


class AuthService:
    """Authentication and active WorkContextMembership session management."""

    def __init__(self):
        self._repository = get_repository()
        self._active_context_id: Optional[int] = None

    def login(self, username: str, password: str) -> Optional[UserModel]:
        repo = get_repository()
        user = repo.authenticate(username, password)
        if not user:
            return None

        self._active_context_id = user.active_context_id

        if self._active_context_id is None:
            contexts = repo.get_user_contexts()
            if contexts:
                user.set_contexts(contexts)
                self._active_context_id = user.active_context_id

        if self._active_context_id is not None:
            user.set_active_context(self._active_context_id)

        from config.settings import settings
        if settings.is_api_mode:
            try:
                from services.websocket_service import websocket_service
                websocket_service.connect_client()
            except Exception:
                pass

        return user

    def logout(self) -> None:
        self._active_context_id = None
        try:
            from services.websocket_service import websocket_service
            websocket_service.disconnect_client()
        except Exception:
            pass
        get_repository().logout()

    def get_current_user(self) -> Optional[UserModel]:
        return get_repository().get_current_user()

    def is_authenticated(self) -> bool:
        return self.get_current_user() is not None

    def get_contexts(self) -> List[Any]:
        user = self.get_current_user()
        if not user:
            return []
        contexts = user.get_contexts()
        if not contexts:
            raw = get_repository().get_user_contexts()
            if raw:
                user.set_contexts(raw)
        return user.get_contexts()

    def get_active_context(self):
        user = self.get_current_user()
        if not user:
            return None
        if self._active_context_id is not None:
            user.set_active_context(self._active_context_id)
        return user.active_context

    def get_active_context_id(self) -> Optional[int]:
        context = self.get_active_context()
        return context.id if context else self._active_context_id

    def switch_context(self, context_membership_id: int) -> bool:
        try:
            context_id = int(context_membership_id)
            result = get_repository().switch_context(context_id)
        except Exception:
            return False

        selected_id = int(result.get("id") or context_membership_id)
        self._active_context_id = selected_id

        user = self.get_current_user()
        if not user:
            return True

        try:
            raw_contexts = get_repository().get_user_contexts()
            if raw_contexts:
                user.set_contexts(raw_contexts)
        except Exception:
            pass

        return user.set_active_context(selected_id)

    # ---- Compatibility wrappers for existing UI ----

    def get_active_department(self) -> Optional[str]:
        context = self.get_active_context()
        if context and context.department_name:
            return context.department_name
        user = self.get_current_user()
        return user.department_name if user else None

    def set_active_department(self, dept_name: str) -> None:
        if not dept_name:
            return
        target = dept_name.strip().lower()
        for context in self.get_contexts():
            if context.department_name and context.department_name.strip().lower() == target:
                self.switch_context(context.id)
                return

    def get_active_role(self) -> str:
        context = self.get_active_context()
        if context:
            return context.context_type
        user = self.get_current_user()
        return user.role if user else "Employee"

    def set_active_role(self, role_name: str) -> None:
        if not role_name:
            return
        target = role_name.strip().lower()
        for context in self.get_contexts():
            if context.context_type.strip().lower() == target:
                self.switch_context(context.id)
                return

    def get_managed_departments(self) -> List[str]:
        departments: List[str] = []
        for context in self.get_contexts():
            if context.department_name and context.department_name not in departments:
                departments.append(context.department_name)

        user = self.get_current_user()
        if user:
            for department in user.managed_depts:
                if department and department != "*" and department not in departments:
                    departments.append(department)
            if user.department_name and user.department_name not in departments:
                departments.append(user.department_name)
        return departments

    def reset_password(self, username: str, old_password: str, new_password: str) -> bool:
        return get_repository().reset_password(username, old_password, new_password)


auth_service = AuthService()


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = auth_service.login(username, password)
    if not user:
        return None

    context = user.active_context
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": context.context_type if context else user.role,
        "department_id": context.department_id if context else user.department_id,
        "department": context.department_name if context else user.department_name,
        "contexts": [c.to_dict() for c in user.get_contexts()],
        "active_context_id": user.active_context_id,
        "active_context_membership_id": user.active_context_id,
    }
