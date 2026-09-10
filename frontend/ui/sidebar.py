from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from models.enums import RoleEnum
from core.context.context_manager import context_manager
from core.navigation.navigation_registry import NavigationRegistry


class Sidebar(QFrame):
    """
    Primary navigation driven by the user's active operational context.

    A user may have multiple WorkContextMembership records, for example:

        Employee • FCTD
        HOD      • C&IT

    The selected context controls:
        - navigation
        - dashboard
        - task/inbox scope
        - permissions
        - department data scope
    """

    page_requested = Signal(str)
    logout_requested = Signal()
    context_switch_requested = Signal(int)

    # Legacy compatibility signals. They are emitted after the
    # ContextManager confirms a context change.
    department_context_changed = Signal(str)
    role_context_changed = Signal(str)

    def __init__(self, role: str = "", username: str = ""):
        super().__init__()

        self.username = username
        self._context_switching = False

        self.role = RoleEnum.normalize(
            context_manager.active_context_type(
                fallback_role=role
            )
            or RoleEnum.EMPLOYEE.value
        )

        self.setObjectName("sidebar")
        self.setMinimumWidth(220)
        self.setMaximumWidth(290)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 20, 15, 20)
        self.layout.setSpacing(6)

        # ------------------------------------------------------------
        # BRAND
        # ------------------------------------------------------------

        title = QLabel("CDTRS")
        title.setObjectName("sidebarTitle")
        self.layout.addWidget(title)

        self.user_label = QLabel()
        self.user_label.setObjectName("sidebarUser")
        self.user_label.setWordWrap(True)
        self.layout.addWidget(self.user_label)

        self.layout.addSpacing(8)

        # ------------------------------------------------------------
        # CONTEXT SWITCHER
        # ------------------------------------------------------------

        self.context_label: Optional[QLabel] = None
        self.context_selector: Optional[QComboBox] = None

        self._build_context_selector()

        # ------------------------------------------------------------
        # NAVIGATION
        # ------------------------------------------------------------

        self.buttons = {}
        self._build_menu()

        self.layout.addStretch()

        # ------------------------------------------------------------
        # LOGOUT
        # ------------------------------------------------------------

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(
            self.logout_requested.emit
        )
        self.layout.addWidget(self.logout_button)

        self.setLayout(self.layout)

        # ------------------------------------------------------------
        # CONTEXT EVENTS
        # ------------------------------------------------------------

        try:
            context_manager.active_context_changed.connect(
                self._handle_active_context_changed
            )
        except Exception:
            pass

        self._refresh_context_display()

    # ================================================================
    # CONTEXT SELECTOR
    # ================================================================

    def _build_context_selector(self) -> None:
        """
        Build the context selector from ContextManager's current
        memberships.

        If contexts are not populated yet, the selector can be created
        later by _ensure_context_selector().
        """
        contexts = self._get_contexts()

        if len(contexts) <= 1:
            return

        self._create_context_selector(contexts)

    def _get_contexts(self):
        """Safely retrieve available work contexts."""
        try:
            contexts = context_manager.contexts()
            return list(contexts or [])
        except Exception:
            return []

    def _create_context_selector(self, contexts) -> None:
        """Create the context selector exactly once."""
        if self.context_selector is not None:
            return

        self.context_label = QLabel("🔐 Active Workspace")
        self.context_label.setObjectName("contextLabel")
        self.context_label.setStyleSheet(
            "font-size: 11px; "
            "font-weight: bold; "
            "color: #94A3B8; "
            "padding-top: 2px;"
        )

        self.context_selector = QComboBox()
        self.context_selector.setObjectName("contextSelector")
        self.context_selector.setMinimumHeight(34)

        self.context_selector.setStyleSheet(
            """
            QComboBox {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                padding: 6px 9px;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
            }

            QComboBox:hover {
                border: 1px solid #38BDF8;
            }

            QComboBox::drop-down {
                border: none;
                width: 24px;
            }

            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #FFFFFF;
                selection-background-color: #334155;
                selection-color: #38BDF8;
            }
            """
        )

        for context in contexts:
            context_id = getattr(context, "id", None)

            if context_id is None:
                continue

            context_type = (
                getattr(context, "context_type", None)
                or "Workspace"
            )

            department = (
                getattr(context, "department_name", None)
                or ""
            )

            # Prefer a human-readable label if the model provides one.
            display_label = getattr(
                context,
                "display_label",
                None
            )

            if display_label:
                text = str(display_label)
            else:
                text = str(context_type)

                if department:
                    text += f" • {department}"

            self.context_selector.addItem(
                text,
                int(context_id)
            )

        active_id = context_manager.active_membership_id()

        if active_id is not None:
            index = self.context_selector.findData(
                int(active_id)
            )

            if index >= 0:
                self.context_selector.setCurrentIndex(index)

        self.context_selector.currentIndexChanged.connect(
            self._handle_context_changed
        )

        # Insert before the navigation buttons.
        self.layout.addWidget(self.context_label)
        self.layout.addWidget(self.context_selector)
        self.layout.addSpacing(7)

    def _ensure_context_selector(self) -> None:
        """
        Contexts may be populated after Sidebar construction.

        This method guarantees that a multi-context user gets the
        dropdown even if the ContextManager was refreshed after the
        Sidebar was created.
        """
        if self.context_selector is not None:
            self._sync_context_selector()
            return

        contexts = self._get_contexts()

        if len(contexts) <= 1:
            return

        self._create_context_selector(contexts)

    def _sync_context_selector(self) -> None:
        """Synchronize selector contents and active selection."""
        if self.context_selector is None:
            return

        contexts = self._get_contexts()

        current_ids = [
            self.context_selector.itemData(i)
            for i in range(self.context_selector.count())
        ]

        new_ids = [
            getattr(ctx, "id", None)
            for ctx in contexts
            if getattr(ctx, "id", None) is not None
        ]

        if current_ids != new_ids:
            self.context_selector.blockSignals(True)

            try:
                self.context_selector.clear()

                for context in contexts:
                    context_id = getattr(context, "id", None)

                    if context_id is None:
                        continue

                    context_type = (
                        getattr(context, "context_type", None)
                        or "Workspace"
                    )

                    department = (
                        getattr(context, "department_name", None)
                        or ""
                    )

                    display_label = getattr(
                        context,
                        "display_label",
                        None
                    )

                    if display_label:
                        text = str(display_label)
                    else:
                        text = str(context_type)

                        if department:
                            text += f" • {department}"

                    self.context_selector.addItem(
                        text,
                        int(context_id)
                    )
            finally:
                self.context_selector.blockSignals(False)

        active_id = context_manager.active_membership_id()

        if active_id is not None:
            index = self.context_selector.findData(
                int(active_id)
            )

            if index >= 0:
                self.context_selector.blockSignals(True)
                self.context_selector.setCurrentIndex(index)
                self.context_selector.blockSignals(False)

    # ================================================================
    # NAVIGATION
    # ================================================================

    def _build_menu(self) -> None:
        """
        Build navigation using NavigationItem.page_key / label.

        This matches MainWindow's NavigationRegistry contract.
        """
        for button in self.buttons.values():
            self.layout.removeWidget(button)
            button.deleteLater()

        self.buttons.clear()

        try:
            items = NavigationRegistry.get_items(self.role)
        except Exception:
            items = []

        for item in items:
            page_key = getattr(item, "page_key", None)
            label = getattr(item, "label", None)

            # Defensive compatibility with older registry entries.
            if page_key is None:
                page_key = str(item)

            if label is None:
                label = str(page_key)

            button = QPushButton(str(label))
            button.setObjectName("sidebarButton")

            button.clicked.connect(
                lambda checked=False, key=page_key:
                    self.page_requested.emit(key)
            )

            self.buttons[page_key] = button

            # Put navigation buttons before the stretch/logout area.
            self.layout.insertWidget(
                self._navigation_insert_index(),
                button
            )

    def _navigation_insert_index(self) -> int:
        """
        Return the position where navigation buttons should be inserted.

        This keeps the context selector above navigation and logout at
        the bottom.
        """
        # Insert before the stretch item.
        return max(0, self.layout.count() - 2)

    # ================================================================
    # CONTEXT CHANGES
    # ================================================================

    def _handle_context_changed(self, index: int) -> None:
        """Request a context switch through MainWindow/ContextManager."""
        if self._context_switching:
            return

        if self.context_selector is None:
            return

        if index < 0:
            return

        context_id = self.context_selector.itemData(index)

        if context_id is None:
            return

        try:
            context_id = int(context_id)
        except (TypeError, ValueError):
            return

        current_id = context_manager.active_membership_id()

        if current_id is not None:
            try:
                if int(current_id) == context_id:
                    return
            except (TypeError, ValueError):
                pass

        self._context_switching = True

        try:
            # Do NOT directly call auth_service.switch_context here.
            #
            # MainWindow receives this request and delegates to
            # ContextManager, which then emits active_context_changed.
            self.context_switch_requested.emit(context_id)
        finally:
            self._context_switching = False

    def _handle_active_context_changed(self, *_args) -> None:
        """
        React to the context actually becoming active.

        This is deliberately separate from requesting a switch.
        """
        self._ensure_context_selector()
        self._sync_context_selector()

        context = None

        try:
            context = context_manager.active_context()
        except Exception:
            context = None

        if context is not None:
            self.apply_context(context)
        else:
            self._refresh_context_display()

    def apply_context(self, context) -> None:
        """
        Apply a context confirmed by ContextManager.

        This changes the Sidebar's role/navigation and visible
        department/workspace information.
        """
        old_role = self.role

        new_role = RoleEnum.normalize(
            getattr(context, "context_type", None)
            or RoleEnum.EMPLOYEE.value
        )

        self.role = new_role

        # Context memberships may be loaded after Sidebar construction.
        # Ensure the selector exists for multi-context users.
        self._ensure_context_selector()
        self._sync_context_selector()

        self._build_menu()
        self._refresh_context_display()

        department = (
            getattr(context, "department_name", None)
            or ""
        )

        if department:
            self.department_context_changed.emit(
                str(department)
            )

        if old_role != new_role:
            self.role_context_changed.emit(new_role)

    # ================================================================
    # DISPLAY
    # ================================================================

    def _refresh_context_display(self) -> None:
        """Update username + active workspace display."""
        try:
            context = context_manager.active_context()
        except Exception:
            context = None

        display_role = self.role

        if context:
            context_type = (
                getattr(context, "context_type", None)
                or display_role
            )

            department = (
                getattr(context, "department_name", None)
                or ""
            )

            display_role = str(context_type)

            if department:
                display_role += f" • {department}"

        if self.username:
            self.user_label.setText(
                f"{self.username}\n{display_role}"
            )
        else:
            self.user_label.setText(display_role)

    # ================================================================
    # ACTIVE NAVIGATION ITEM
    # ================================================================

    def set_active(self, active_item: str) -> None:
        """Highlight the currently displayed page."""
        for item, button in self.buttons.items():
            if item == active_item:
                button.setStyleSheet(
                    """
                    background-color: #1E293B;
                    color: #FFFFFF;
                    font-weight: 600;
                    border-radius: 5px;
                    padding: 7px 10px;
                    """
                )
            else:
                button.setStyleSheet("")

    # ================================================================
    # PUBLIC HELPERS
    # ================================================================

    def get_menu_items(self, role: str):
        return NavigationRegistry.get_items(role)