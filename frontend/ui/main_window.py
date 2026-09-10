from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from components.document_viewer import DocumentViewer
from models.enums import RoleEnum
from pages.admin_suite import AdminSuitePage
from pages.dashboard import DashboardPage
from pages.director_inbox import DirectorInboxPage
from pages.director_reviewed import DirectorReviewedPage
from pages.document_intake import DocumentIntakePage
from pages.documents import DocumentsPage
from pages.employee_tasks import EmployeeTasksPage
from pages.history import HistoryPage
from pages.hod_inbox import HODInboxPage
from pages.tso_tasks import TSOTasksPage
from pages.inbox import InboxPage
from ui.sidebar import Sidebar

from core.context.context_manager import context_manager
from core.navigation.navigation_registry import NavigationRegistry


class MainWindow(QMainWindow):
    """Main CDTRS application shell with context-aware navigation."""

    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = RoleEnum.normalize(role)
        self.previous_page = None
        self.document_viewer = None

        self.setWindowTitle(f"CDTRS - {self.role} ({self.username})")
        self.resize(1150, 720)
        self.setMinimumSize(960, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar(self.role, username=self.username)
        self.sidebar.page_requested.connect(self._handle_page_requested)
        self.sidebar.logout_requested.connect(self.logout)
        self.sidebar.context_switch_requested.connect(self._handle_context_switch)

        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage(self.role)
        self.dashboard_page.view_requested.connect(self.open_document_viewer)
        self.dashboard_page.navigate_requested.connect(self._handle_dashboard_navigate)
        self.stack.addWidget(self.dashboard_page)

        self.inbox_page = InboxPage()
        self.inbox_page.process_requested.connect(self.open_document_from_inbox)
        self.stack.addWidget(self.inbox_page)

        self.document_intake_page = DocumentIntakePage()
        self.document_intake_page.document_processed.connect(self.on_document_processed)
        self.stack.addWidget(self.document_intake_page)

        self.documents_page = DocumentsPage(user_role=self.role)
        self.documents_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.documents_page)

        self.history_page = HistoryPage()
        self.stack.addWidget(self.history_page)

        self.director_inbox_page = DirectorInboxPage()
        self.director_inbox_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.director_inbox_page)

        self.director_reviewed_page = DirectorReviewedPage()
        self.director_reviewed_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.director_reviewed_page)

        self.hod_inbox_page = HODInboxPage()
        self.hod_inbox_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.hod_inbox_page)

        self.employee_tasks_page = EmployeeTasksPage()
        self.employee_tasks_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.employee_tasks_page)

        self.tso_tasks_page = TSOTasksPage()
        self.tso_tasks_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.tso_tasks_page)

        if self.role == RoleEnum.ADMINISTRATOR.value:
            self.admin_suite_page = AdminSuitePage()
            self.stack.addWidget(self.admin_suite_page)
        else:
            self.admin_suite_page = None

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack, 1)
        central_widget.setLayout(main_layout)

        context_manager.active_context_changed.connect(
            self._handle_active_context_changed
        )
        context_manager.context_cleared.connect(self._handle_context_cleared)

        # If backend has an active context, use it. Otherwise preserve the
        # authenticated role supplied by Login.
        context = context_manager.active_context()
        if context is not None:
            self._apply_context(context)
        else:
            self._navigate_to_first_allowed_page()

    def _handle_context_switch(self, membership_id: int):
        current_id = context_manager.active_membership_id()
        if current_id == membership_id:
            return

        if not context_manager.switch_context(membership_id):
            self._sync_sidebar_selector()

    def _handle_active_context_changed(self, context):
        self._apply_context(context)
        self._sync_sidebar_selector()

    def _handle_context_cleared(self):
        # Context clearing is expected during logout; do not recursively clear.
        self.document_viewer = None

    def _apply_context(self, context):
        self.role = RoleEnum.normalize(
            getattr(context, "context_type", None) or
            self.role
        )
        self.setWindowTitle(f"CDTRS - {self.role} ({self.username})")
        self.sidebar.apply_context(context)

        if self.document_viewer is not None:
            self._cleanup_existing_viewer()

        self._navigate_to_first_allowed_page()

    def _sync_sidebar_selector(self):
        selector = self.sidebar.context_selector
        if selector is None:
            return

        active_id = context_manager.active_membership_id()
        if active_id is None:
            return

        self.sidebar._context_switching = True
        try:
            index = selector.findData(active_id)
            if index >= 0:
                selector.setCurrentIndex(index)
        finally:
            self.sidebar._context_switching = False

    def _handle_page_requested(self, page_key: str):
        context_type = context_manager.active_context_type(
            fallback_role=self.role
        )

        if not self._page_allowed_for_current_context(page_key):
            return

        if page_key == "Dashboard":
            self._navigate_to(self.dashboard_page, page_key)
        elif page_key == "Inbox":
            self._open_inbox_for_role(page_key)
        elif page_key == "Review Queue":
            self._navigate_to(self.director_inbox_page, page_key)
        elif page_key == "My Tasks":
            if self.role == RoleEnum.TSO.value:
                self._navigate_to(self.tso_tasks_page, page_key)
            else:
                self._navigate_to(self.employee_tasks_page, page_key)
        elif page_key == "Department Tasks":
            self._navigate_to(self.hod_inbox_page, page_key)
        elif page_key in ("Document Processing", "Document Intake"):
            self._navigate_to(self.document_intake_page, page_key)
        elif page_key in ("Documents", "All Documents"):
            self._navigate_to(self.documents_page, page_key)
        elif page_key in ("History / Audit", "History"):
            self._navigate_to(self.history_page, page_key)
        elif page_key == "Admin Suite" and self.admin_suite_page is not None:
            self._navigate_to(self.admin_suite_page, page_key)

    def _open_inbox_for_role(self, menu_key: str):
        if self.role == RoleEnum.DIRECTOR.value:
            self._navigate_to(self.director_inbox_page, menu_key)
        elif self.role == RoleEnum.HOD.value:
            self._navigate_to(self.hod_inbox_page, menu_key)
        elif self.role == RoleEnum.TSO.value:
            self._navigate_to(self.tso_tasks_page, menu_key)
        elif self.role == RoleEnum.EMPLOYEE.value:
            self._navigate_to(self.employee_tasks_page, menu_key)
        else:
            self._navigate_to(self.inbox_page, menu_key)

    def _navigate_to_first_allowed_page(self):
        items = NavigationRegistry.get_items(self.role)
        if not items:
            return
        # NavigationRegistry may return NavigationItem objects rather than strings.
        # This MainWindow uses the existing page architecture, so resolve only the
        # labels we actually support here.
        first_key = "Dashboard"
        if not self._page_allowed_for_current_context(first_key):
            first_key = "Inbox"
        self._handle_page_requested(first_key)

    def _page_allowed_for_current_context(self, page_key: str) -> bool:
        """Check the requested label against the active context without
        depending on a separate contexts/<role> page tree."""
        context_type = context_manager.active_context_type(
            fallback_role=self.role
        )
        try:
            return bool(NavigationRegistry.is_valid_page(context_type, page_key))
        except Exception:
            # Keep compatibility with the existing label-based navigation if
            # the registry does not know the legacy page names.
            allowed = {
                RoleEnum.ADMINISTRATOR.value: {"Dashboard", "Inbox", "Documents", "History / Audit", "Admin Suite"},
                RoleEnum.DS.value: {"Dashboard", "Inbox", "Document Processing", "Documents", "History / Audit"},
                RoleEnum.DIRECTOR.value: {"Dashboard", "Inbox", "Review Queue", "Documents", "History / Audit"},
                RoleEnum.HOD.value: {"Dashboard", "Inbox", "Department Tasks", "Documents", "History / Audit"},
                RoleEnum.EMPLOYEE.value: {"Dashboard", "Inbox", "My Tasks", "Documents", "History / Audit"},
                RoleEnum.TSO.value: {"Dashboard", "Inbox", "My Tasks", "Documents", "History / Audit"},
            }
            return page_key in allowed.get(self.role, set())

    def setup_navigation(self):
        """Compatibility method retained for older callers."""
        return None

    def _handle_dashboard_navigate(self, target_page_name: str, filters: Optional[dict] = None):
        if target_page_name == "Inbox":
            if self.role == RoleEnum.DIRECTOR.value:
                nav_key = "Review Queue" if "Review Queue" in self.sidebar.buttons else "Inbox"
                self._navigate_to(self.director_inbox_page, nav_key, skip_reload=bool(filters))
                if filters and hasattr(self.director_inbox_page, "set_filters"):
                    self.director_inbox_page.set_filters(**filters)
            elif self.role == RoleEnum.HOD.value:
                self._navigate_to(
                    self.hod_inbox_page,
                    "Department Tasks" if "Department Tasks" in self.sidebar.buttons else "Inbox",
                )
            elif self.role == RoleEnum.TSO.value:
                self._navigate_to(
                    self.tso_tasks_page,
                    "My Tasks" if "My Tasks" in self.sidebar.buttons else "Inbox",
                )
            elif self.role == RoleEnum.EMPLOYEE.value:
                self._navigate_to(
                    self.employee_tasks_page,
                    "My Tasks" if "My Tasks" in self.sidebar.buttons else "Inbox",
                )
            else:
                self._navigate_to(self.inbox_page, "Inbox")
        elif target_page_name in ("Reviewed Documents", "Reviewed"):
            if self.role == RoleEnum.DIRECTOR.value:
                nav_key = "Review Queue" if "Review Queue" in self.sidebar.buttons else "Inbox"
                self._navigate_to(self.director_inbox_page, nav_key, skip_reload=True)
                if hasattr(self.director_inbox_page, "set_filters"):
                    self.director_inbox_page.set_filters(
                        category="Reviewed & Returned to DS"
                    )
            else:
                self._navigate_to(self.director_reviewed_page, "Reviewed Documents")
        elif target_page_name in ("Documents", "All Documents"):
            self._navigate_to(
                self.documents_page,
                "Documents" if "Documents" in self.sidebar.buttons else "All Documents",
                skip_reload=bool(filters),
            )
            if filters and hasattr(self.documents_page, "set_filters"):
                self.documents_page.set_filters(**filters)

    def _navigate_to(self, target_widget: QWidget, menu_key: str, skip_reload: bool = False):
        if self.document_viewer is not None:
            self._cleanup_existing_viewer()

        if not skip_reload:
            if hasattr(target_widget, "refresh"):
                target_widget.refresh()
            elif hasattr(target_widget, "load_inbox"):
                target_widget.load_inbox()
            elif hasattr(target_widget, "load_tasks"):
                target_widget.load_tasks()
            elif hasattr(target_widget, "load_documents"):
                target_widget.load_documents()
            elif hasattr(target_widget, "load_history"):
                target_widget.load_history()

        self.sidebar.set_active(menu_key)
        self.stack.setCurrentWidget(target_widget)

    def open_document_from_inbox(self, document):
        if self.document_viewer is not None:
            self._cleanup_existing_viewer()
        self.document_intake_page.load_document(document)
        active_key = (
            "Document Processing"
            if "Document Processing" in self.sidebar.buttons
            else "Document Intake"
        )
        self.sidebar.set_active(active_key)
        self.stack.setCurrentWidget(self.document_intake_page)

    def on_document_processed(self, routed_document):
        self.dashboard_page.refresh()
        self.inbox_page.load_documents()
        self.documents_page.load_documents()
        self._navigate_to_first_allowed_page()

    def _cleanup_existing_viewer(self):
        if self.document_viewer is not None:
            viewer = self.document_viewer
            self.document_viewer = None
            try:
                viewer.close_requested.disconnect()
            except Exception:
                pass
            try:
                viewer.document_updated.disconnect()
            except Exception:
                pass
            if hasattr(viewer, "cleanup"):
                viewer.cleanup()
            self.stack.removeWidget(viewer)
            viewer.deleteLater()

    def open_document_viewer(self, document, role: Optional[str] = None):
        self._cleanup_existing_viewer()
        self.previous_page = self.stack.currentWidget()
        self.document_viewer = DocumentViewer(
            document,
            role=role or self.role,
        )
        self.document_viewer.close_requested.connect(self.close_document_viewer)
        self.document_viewer.document_updated.connect(self.on_document_updated)
        self.stack.addWidget(self.document_viewer)
        self.stack.setCurrentWidget(self.document_viewer)

    def on_document_updated(self, updated_document):
        self.dashboard_page.refresh()
        self.director_inbox_page.load_inbox()
        self.director_reviewed_page.load_documents()
        self.hod_inbox_page.load_inbox()
        self.employee_tasks_page.load_tasks()
        self.tso_tasks_page.load_tasks()
        if hasattr(self.documents_page, "status_filter"):
            self.documents_page.status_filter.setCurrentIndex(0)
        self.documents_page.load_documents()
        self.history_page.load_history()

    def close_document_viewer(self):
        self._cleanup_existing_viewer()
        if self.previous_page is not None:
            self.stack.setCurrentWidget(self.previous_page)
            if hasattr(self.previous_page, "refresh"):
                self.previous_page.refresh()
            elif hasattr(self.previous_page, "load_inbox"):
                self.previous_page.load_inbox()
            elif hasattr(self.previous_page, "load_tasks"):
                self.previous_page.load_tasks()
            elif hasattr(self.previous_page, "load_documents"):
                self.previous_page.load_documents()

    def logout(self):
        self._cleanup_existing_viewer()
        try:
            from services.auth_service import auth_service
            auth_service.logout()
        except Exception:
            pass
        context_manager.clear()
        from ui.login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

    def closeEvent(self, event):
        try:
            from services.websocket_service import websocket_service
            websocket_service.disconnect_client()
        except Exception:
            pass
        self._cleanup_existing_viewer()
        super().closeEvent(event)
