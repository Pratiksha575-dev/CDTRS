from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton
)

class Sidebar(QFrame):

    def __init__(self, role):
        super().__init__()

        self.role = role

        self.setObjectName("sidebar")
        self.setFixedWidth(230)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(6)

        # -------------------------
        # Application title
        # -------------------------

        title = QLabel("CDTRS")
        title.setObjectName("sidebarTitle")

        user_label = QLabel(role)
        user_label.setObjectName("sidebarUser")

        layout.addWidget(title)
        layout.addWidget(user_label)

        layout.addSpacing(15)

        # -------------------------
        # Role-based menu
        # -------------------------

        menu_items = self.get_menu_items(role)

        self.buttons = {}

        for item in menu_items:

            button = QPushButton(item)
            button.setObjectName("sidebarButton")

            self.buttons[item] = button

            layout.addWidget(button)

        # Push Logout to bottom
        layout.addStretch()

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")

        layout.addWidget(self.logout_button)

        self.setLayout(layout)

    # -------------------------
    # Menu configuration
    # -------------------------

    def get_menu_items(self, role):

        menus = {

            "Master": [
                "Dashboard",
                "Inbox",
                "Document Intake",
                "Documents",
                "Priority / Deadlines",
                "History"
            ],

            "Director": [
                "Dashboard",
                "Inbox",
                "Documents",
                "Priority / Deadlines",
                "History"
            ],

            "HOD": [
                "Dashboard",
                "Inbox",
                "Department Tasks",
                "Priority / Deadlines",
                "History"
            ],

            "HOD PA": [
                "Dashboard",
                "Inbox",
                "Department Tasks",
                "Priority / Deadlines",
                "History"
            ],

            "Employee": [
                "Dashboard",
                "My Tasks",
                "History"
            ],

            "Administrator": [
                "Dashboard",
                "Users & Roles",
                "Departments",
                "Configuration",
                "Audit / History"
            ],

            "Read-only User": [
                "Dashboard",
                "Documents",
                "Priority / Deadlines",
                "History"
            ]
        }

        return menus.get(role, ["Dashboard"])