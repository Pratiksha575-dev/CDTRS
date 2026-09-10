"""CDTRS frontend active-context manager."""

from typing import Any, List, Optional

from PySide6.QtCore import QObject, Signal

from models.enums import RoleEnum
from services.auth_service import auth_service


class ContextManager(QObject):
    """Single frontend authority for the active operational context."""

    active_context_changed = Signal(object)
    context_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_context = None

    def refresh(self, fallback_role: Optional[str] = None):
        """Load the active context, preserving the authenticated role as fallback."""
        try:
            context = auth_service.get_active_context()
        except Exception:
            context = None

        self._active_context = context

        if context is None:
            if fallback_role:
                return None
            self.context_cleared.emit()
            return None

        self.active_context_changed.emit(context)
        return context

    def contexts(self) -> List[Any]:
        """Return all contexts available to the authenticated user."""
        try:
            return list(auth_service.get_contexts() or [])
        except Exception:
            return []

    def active_context(self):
        """Return the confirmed active backend context, if one exists."""
        if self._active_context is None:
            try:
                self._active_context = auth_service.get_active_context()
            except Exception:
                self._active_context = None
        return self._active_context

    def active_membership_id(self) -> Optional[int]:
        context = self.active_context()
        return getattr(context, "id", None) if context else None

    def active_context_type(self, fallback_role: Optional[str] = None) -> str:
        """Return active context type; otherwise use the authenticated role."""
        context = self.active_context()
        if context is not None:
            value = getattr(context, "context_type", None)
            if value:
                return RoleEnum.normalize(value)

        if fallback_role:
            return RoleEnum.normalize(fallback_role)

        return RoleEnum.EMPLOYEE.value

    def active_department_id(self):
        context = self.active_context()
        return getattr(context, "department_id", None) if context else None

    def active_department_name(self) -> str:
        context = self.active_context()
        return (
            getattr(context, "department_name", "") or ""
            if context else ""
        )

    def switch_context(self, membership_id: int) -> bool:
        """Switch context through auth_service and publish the new context."""
        try:
            success = auth_service.switch_context(int(membership_id))
        except Exception:
            return False

        if not success:
            return False

        try:
            self._active_context = auth_service.get_active_context()
        except Exception:
            self._active_context = None

        if not self._active_context:
            self.context_cleared.emit()
            return False

        self.active_context_changed.emit(self._active_context)
        return True

    def clear(self):
        """Clear local state during logout."""
        self._active_context = None
        self.context_cleared.emit()


context_manager = ContextManager()
