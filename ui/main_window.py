from PySide6.QtWidgets import(
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget
)

from pages.dashboard import DashboardPage
from ui.sidebar import Sidebar

class MainWindow(QMainWindow):

    def __init__(self, username, role):
        super().__init__()

        self.username = username
        self.role = role

        self.setWindowTitle(f"CDTRS - {role}")
        self.resize(1100, 700)

        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(role)

        self.sidebar.logout_button.clicked.connect(self.logout)

        # Page container
        self.stack = QStackedWidget()

        # Dashboard
        self.dashboard_page = DashboardPage(role)
        self.stack.addWidget(self.dashboard_page)

        # Add sidebar + content
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        central_widget.setLayout(main_layout)

    def logout(self):
        from ui.login import LoginWindow
        self.login_window=LoginWindow()
        self.login_window.show()
        self.close()     
