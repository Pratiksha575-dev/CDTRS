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

    def __init__(self, role: str, username: str = ""):
        super().__init__()
        self.role = RoleEnum.normalize(role)
        self.username = username

        self.setObjectName("sidebar")
        self.setMinimumWidth(200)
        self.setMaximumWidth(260)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(6)

        # -------------------------
        # Application title & User
        # -------------------------
        title = QLabel("CDTRS")
        title.setObjectName("sidebarTitle")

        # Format user display text cleanly
        if self.username and self.username.strip().lower() != self.role.strip().lower():
            user_text = f"{self.username}\n{self.role}"
        else:
            user_text = self.role

        user_label = QLabel(user_text)
        user_label.setObjectName("sidebarUser")
        user_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(user_label)
        layout.addSpacing(14)

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
                "Review Queue",
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