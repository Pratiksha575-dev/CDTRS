from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from models.enums import RoleEnum


class Sidebar(QFrame):
    """
    Role-based primary sidebar navigation for CDTRS.
    """

    def __init__(self, role: str):
        super().__init__()
        self.role = RoleEnum.normalize(role)

        self.setObjectName("sidebar")
        self.setFixedWidth(230)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(6)

        # -------------------------
        # Application title & User
        # -------------------------
        title = QLabel("CDTRS")
        title.setObjectName("sidebarTitle")

        user_label = QLabel(self.role)
        user_label.setObjectName("sidebarUser")
        user_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(user_label)
        layout.addSpacing(15)

        # -------------------------
        # Role-based menu
        # -------------------------
        menu_items = self.get_menu_items(self.role)
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

    def set_active(self, active_item: str):
        """Visually indicates the currently active navigation item."""
        for item, btn in self.buttons.items():
            if item == active_item:
                btn.setStyleSheet("background-color: #1E293B; color: #FFFFFF; font-weight: 600;")
            else:
                btn.setStyleSheet("")

    def get_menu_items(self, role: str):
        menus = {
            RoleEnum.DIRECTOR_SECRETARY.value: [
                "Dashboard",
                "Inbox",
                "Document Processing",
                "Documents",
                "History / Audit"
            ],
            RoleEnum.DIRECTOR.value: [
                "Dashboard",
                "Inbox",
                "Reviewed Documents",
                "History / Audit"
            ],
            RoleEnum.HOD.value: [
                "Dashboard",
                "Department Tasks",
                "History / Audit"
            ],
            "HOD PA": [
                "Dashboard",
                "Department Tasks",
                "History / Audit"
            ],
            "Employee": [
                "Dashboard",
                "My Tasks",
                "History / Audit"
            ],
            "Administrator": [
                "Dashboard",
                "Users & Roles",
                "Departments",
                "Configuration",
                "History / Audit"
            ],
            "Read-only User": [
                "Dashboard",
                "Documents",
                "History / Audit"
            ]
        }
        return menus.get(role, ["Dashboard"])