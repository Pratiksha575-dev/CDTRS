from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from components.document_viewer import DocumentViewer
from models.enums import RoleEnum
from pages.dashboard import DashboardPage
from pages.director_inbox import DirectorInboxPage
from pages.director_reviewed import DirectorReviewedPage
from pages.document_intake import DocumentIntakePage
from pages.documents import DocumentsPage
from pages.employee_tasks import EmployeeTasksPage
from pages.history import HistoryPage
from pages.hod_inbox import HODInboxPage
from pages.inbox import InboxPage
from ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """
    Main application window for CDTRS desktop client.
    Houses role-based sidebar and dynamic QStackedWidget page container.
    """

    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = RoleEnum.normalize(role)

        self.setWindowTitle(f"CDTRS - {self.role} ({self.username})")
        self.resize(1150, 720)
        self.setMinimumSize(960, 600)

        # Main Central Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(self.role)
        self.sidebar.logout_button.clicked.connect(self.logout)

        # Page Container Stack
        self.stack = QStackedWidget()

        # 1. Dashboard (Specialized for DS, Director, HOD, or Employee)
        self.dashboard_page = DashboardPage(self.role)
        self.dashboard_page.view_requested.connect(self.open_document_viewer)
        self.dashboard_page.navigate_requested.connect(self._handle_dashboard_navigate)
        self.stack.addWidget(self.dashboard_page)

        # 2. DS Intake Inbox
        self.inbox_page = InboxPage()
        self.inbox_page.process_requested.connect(self.open_document_from_inbox)
        self.stack.addWidget(self.inbox_page)

        # 3. Document Processing / Intake Form
        self.document_intake_page = DocumentIntakePage()
        self.document_intake_page.document_processed.connect(self.on_document_processed)
        self.stack.addWidget(self.document_intake_page)

        # 4. Central Documents Repository (with Priority & Deadline tracking)
        self.documents_page = DocumentsPage(user_role=self.role)
        self.documents_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.documents_page)

        # 5. History / Audit Timeline
        self.history_page = HistoryPage()
        self.stack.addWidget(self.history_page)

        # 6. Director Review Inbox
        self.director_inbox_page = DirectorInboxPage()
        self.director_inbox_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.director_inbox_page)

        # 7. Director Reviewed Archive
        self.director_reviewed_page = DirectorReviewedPage()
        self.director_reviewed_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.director_reviewed_page)

        # 8. HOD Department Inbox & Tasks
        self.hod_inbox_page = HODInboxPage()
        self.hod_inbox_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.hod_inbox_page)

        # 9. Employee My Tasks
        self.employee_tasks_page = EmployeeTasksPage()
        self.employee_tasks_page.view_requested.connect(self.open_document_viewer)
        self.stack.addWidget(self.employee_tasks_page)

        # Wire Navigation
        self.setup_navigation()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack, 1)
        central_widget.setLayout(main_layout)

    # ====================================
    # NAVIGATION WIRING
    # ====================================

    def setup_navigation(self):
        # Dashboard
        if "Dashboard" in self.sidebar.buttons:
            self.sidebar.buttons["Dashboard"].clicked.connect(
                lambda: self._navigate_to(self.dashboard_page, "Dashboard")
            )

        # Inbox / Department Tasks / My Tasks
        if "Inbox" in self.sidebar.buttons:
            if self.role == RoleEnum.DIRECTOR.value:
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self._navigate_to(self.director_inbox_page, "Inbox")
                )
            elif self.role in (RoleEnum.HOD.value, "HOD", "HOD PA"):
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self._navigate_to(self.hod_inbox_page, "Inbox")
                )
            elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self._navigate_to(self.employee_tasks_page, "Inbox")
                )
            else:
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self._navigate_to(self.inbox_page, "Inbox")
                )

        if "My Tasks" in self.sidebar.buttons:
            self.sidebar.buttons["My Tasks"].clicked.connect(
                lambda: self._navigate_to(self.employee_tasks_page, "My Tasks")
            )

        if "Department Tasks" in self.sidebar.buttons:
            self.sidebar.buttons["Department Tasks"].clicked.connect(
                lambda: self._navigate_to(self.hod_inbox_page, "Department Tasks")
            )

        # Director Reviewed Documents
        if "Reviewed Documents" in self.sidebar.buttons:
            self.sidebar.buttons["Reviewed Documents"].clicked.connect(
                lambda: self._navigate_to(self.director_reviewed_page, "Reviewed Documents")
            )

        # Document Processing / Intake
        for intake_key in ("Document Processing", "Document Intake"):
            if intake_key in self.sidebar.buttons:
                self.sidebar.buttons[intake_key].clicked.connect(
                    lambda k=intake_key: self._navigate_to(self.document_intake_page, k)
                )

        # Documents
        for docs_key in ("Documents", "All Documents"):
            if docs_key in self.sidebar.buttons:
                self.sidebar.buttons[docs_key].clicked.connect(
                    lambda k=docs_key: self._navigate_to(self.documents_page, k)
                )

        # History / Audit
        for hist_key in ("History / Audit", "History"):
            if hist_key in self.sidebar.buttons:
                self.sidebar.buttons[hist_key].clicked.connect(
                    lambda k=hist_key: self._navigate_to(self.history_page, k)
                )

    def _handle_dashboard_navigate(self, target_page_name: str, filters: Optional[dict] = None):
        if target_page_name == "Inbox":
            if self.role == RoleEnum.DIRECTOR.value:
                self._navigate_to(self.director_inbox_page, "Inbox")
            elif self.role in (RoleEnum.HOD.value, "HOD"):
                self._navigate_to(self.hod_inbox_page, "Department Tasks" if "Department Tasks" in self.sidebar.buttons else "Inbox")
            elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
                self._navigate_to(self.employee_tasks_page, "My Tasks" if "My Tasks" in self.sidebar.buttons else "Inbox")
            else:
                self._navigate_to(self.inbox_page, "Inbox")
        elif target_page_name in ("Reviewed Documents", "Reviewed"):
            self._navigate_to(self.director_reviewed_page, "Reviewed Documents")
        elif target_page_name in ("Documents", "All Documents"):
            self._navigate_to(self.documents_page, "Documents" if "Documents" in self.sidebar.buttons else "All Documents", skip_reload=bool(filters))
            if filters and hasattr(self.documents_page, "set_filters"):
                self.documents_page.set_filters(**filters)

    def _navigate_to(self, target_widget: QWidget, menu_key: str, skip_reload: bool = False):
        # Clean up any active DocumentViewer if navigating away to top-level tabs
        if hasattr(self, "document_viewer") and self.document_viewer is not None:
            self._cleanup_existing_viewer()

        # Refresh target page data if it supports refresh and not explicitly skipped
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

    # ====================================
    # WORKFLOW TRANSITIONS
    # ====================================

    def open_document_from_inbox(self, document):
        """Transitions selected raw inbox item to Document Processing form with OCR."""
        if hasattr(self, "document_viewer") and self.document_viewer is not None:
            self._cleanup_existing_viewer()
        self.document_intake_page.load_document(document)
        active_key = "Document Processing" if "Document Processing" in self.sidebar.buttons else "Document Intake"
        self.sidebar.set_active(active_key)
        self.stack.setCurrentWidget(self.document_intake_page)

    def on_document_processed(self, routed_document):
        """Called when a document is created and sent to Director."""
        self.dashboard_page.refresh()
        if hasattr(self, "inbox_page"):
            self.inbox_page.load_documents()
        self.documents_page.load_documents()
        self._navigate_to(self.dashboard_page, "Dashboard")

    def _cleanup_existing_viewer(self):
        """Cleanly unmounts and disconnects existing DocumentViewer instance."""
        if hasattr(self, "document_viewer") and self.document_viewer is not None:
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
        """Mounts canonical DocumentViewer for the active role with duplicate prevention."""
        self._cleanup_existing_viewer()
        self.previous_page = self.stack.currentWidget()
        active_role = role or self.role

        self.document_viewer = DocumentViewer(document, role=active_role)
        self.document_viewer.close_requested.connect(self.close_document_viewer)
        self.document_viewer.document_updated.connect(self.on_document_updated)

        self.stack.addWidget(self.document_viewer)
        self.stack.setCurrentWidget(self.document_viewer)

    def on_document_updated(self, updated_document):
        """Refreshes background table queues upon workflow action completion."""
        self.dashboard_page.refresh()
        self.director_inbox_page.load_inbox()
        self.director_reviewed_page.load_documents()
        self.hod_inbox_page.load_inbox()
        self.employee_tasks_page.load_tasks()
        if hasattr(self.documents_page, "status_filter"):
            self.documents_page.status_filter.setCurrentIndex(0)
        self.documents_page.load_documents()
        self.history_page.load_history()

    def close_document_viewer(self):
        """Closes viewer and restores previous queue page."""
        self._cleanup_existing_viewer()

        if hasattr(self, "previous_page") and self.previous_page:
            self.stack.setCurrentWidget(self.previous_page)
            if hasattr(self.previous_page, "refresh"):
                self.previous_page.refresh()
            elif hasattr(self.previous_page, "load_inbox"):
                self.previous_page.load_inbox()
            elif hasattr(self.previous_page, "load_tasks"):
                self.previous_page.load_tasks()
            elif hasattr(self.previous_page, "load_documents"):
                self.previous_page.load_documents()

    # ====================================
    # LOGOUT & CLEANUP
    # ====================================

    def logout(self):
        try:
            from services.auth_service import auth_service
            auth_service.logout()
        except Exception:
            pass
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