from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget
)

from pages.dashboard import DashboardPage
from pages.inbox import InboxPage
from pages.document_intake import DocumentIntakePage
from ui.sidebar import Sidebar
from components.document_viewer import DocumentViewer
from pages.documents import DocumentsPage
from pages.priority import PriorityPage
from pages.history import HistoryPage
from pages.director_inbox import DirectorInboxPage
class MainWindow(QMainWindow):

    def __init__(self, username, role):
        super().__init__()

        self.username = username
        self.role = role

        self.setWindowTitle(f"CDTRS - {role}")
        self.resize(1100, 700)

        # --------------------------------
        # Main central widget
        # --------------------------------

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --------------------------------
        # Main horizontal layout
        # --------------------------------

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --------------------------------
        # Sidebar
        # --------------------------------

        self.sidebar = Sidebar(role)

        self.sidebar.logout_button.clicked.connect(
            self.logout
        )

        # --------------------------------
        # Page container
        # --------------------------------

        self.stack = QStackedWidget()

        # --------------------------------
        # Dashboard
        # --------------------------------

        self.dashboard_page = DashboardPage(role)
        self.stack.addWidget(self.dashboard_page)

        # --------------------------------
        # Inbox
        # --------------------------------

        self.inbox_page = InboxPage()
        self.stack.addWidget(self.inbox_page)

        # --------------------------------
        # Document Intake
        # --------------------------------

        self.document_intake_page = DocumentIntakePage()
        self.stack.addWidget(self.document_intake_page)

        # --------------------------------
        # Documents
        # --------------------------------

        self.documents_page = DocumentsPage()

        self.stack.addWidget(
            self.documents_page
        )

        self.documents_page.view_requested.connect(
            self.open_document_viewer
        )


        # --------------------------------
        # Priority / Deadlines
        # --------------------------------

        self.priority_page = PriorityPage()

        self.stack.addWidget(
            self.priority_page
        )

        self.priority_page.view_requested.connect(
            self.open_document_viewer
        )


        # --------------------------------
        # History / Audit
        # --------------------------------

        self.history_page = HistoryPage()

        self.stack.addWidget(
            self.history_page
        )

        # --------------------------------
        # DIRECTOR INBOX
        # --------------------------------

        self.director_inbox_page = DirectorInboxPage()

        self.stack.addWidget(
            self.director_inbox_page
        )

        self.director_inbox_page.view_requested.connect(
            self.open_document_viewer
        )

        # --------------------------------
        # Setup navigation
        # --------------------------------

        self.setup_navigation()

        # --------------------------------
        # Add sidebar + content
        # --------------------------------

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        central_widget.setLayout(main_layout)

    # ====================================
    # NAVIGATION
    # ====================================

    def setup_navigation(self):

        # Dashboard
        if "Dashboard" in self.sidebar.buttons:

            self.sidebar.buttons["Dashboard"].clicked.connect(
                lambda: self.stack.setCurrentWidget(
                    self.dashboard_page
                )
            )

        # Inbox
        if self.role == "Master":

            if "Inbox" in self.sidebar.buttons:
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self.stack.setCurrentWidget(
                        self.inbox_page
                    )
                )

        elif self.role == "Director":

            if "Inbox" in self.sidebar.buttons:
                self.sidebar.buttons["Inbox"].clicked.connect(
                    lambda: self.stack.setCurrentWidget(
                        self.director_inbox_page
                    )
                )

        # Document Intake
        if "Document Intake" in self.sidebar.buttons:

            self.sidebar.buttons["Document Intake"].clicked.connect(
                lambda: self.stack.setCurrentWidget(
                    self.document_intake_page
                )
            )

        # Inbox → Document Intake
        self.inbox_page.process_requested.connect(
            self.open_document_from_inbox
        )

        if "Documents" in self.sidebar.buttons:

            self.sidebar.buttons["Documents"].clicked.connect(
                lambda: self.stack.setCurrentWidget(
                    self.documents_page
                )
            )

        if "Priority / Deadlines" in self.sidebar.buttons:

            self.sidebar.buttons[
                "Priority / Deadlines"
            ].clicked.connect(
                lambda: self.stack.setCurrentWidget(
                    self.priority_page
                )
            )

        if "History" in self.sidebar.buttons:

            self.sidebar.buttons["History"].clicked.connect(
                lambda: self.stack.setCurrentWidget(
                    self.history_page
                )
            )    
    # ====================================
    # OPEN DOCUMENT FROM INBOX
    # ====================================

    def open_document_from_inbox(self, document):

        self.document_intake_page.load_document(
            document
        )

        self.stack.setCurrentWidget(
            self.document_intake_page
        )

    def open_document_viewer(self, document, role):

        self.previous_page = self.stack.currentWidget()

        self.document_viewer = DocumentViewer(
            document,
            role
        )

        self.document_viewer.close_requested.connect(
            self.close_document_viewer
        )

        self.stack.addWidget(
            self.document_viewer
        )

        self.stack.setCurrentWidget(
            self.document_viewer
        )

    def close_document_viewer(self):

        if hasattr(self, "document_viewer"):

            self.stack.removeWidget(
                self.document_viewer
            )

            self.document_viewer.deleteLater()

            self.document_viewer = None

        if hasattr(self, "previous_page"):

            self.stack.setCurrentWidget(
                self.previous_page
            )
    # ====================================
    # LOGOUT
    # ====================================

    def logout(self):

        from ui.login import LoginWindow

        self.login_window = LoginWindow()
        self.login_window.show()

        self.close()