from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QComboBox,
    QHBoxLayout,
)

from models.enums import RoleEnum
from services.auth_service import auth_service


class Sidebar(QFrame):
    """
    Role-based primary sidebar navigation for CDTRS.
    Supports dynamic department switching for multi-dept HODs and role switching.
    """
    department_context_changed = Signal(str)
    role_context_changed = Signal(str)

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
        layout.addSpacing(6)

        # -------------------------
        # Multi-Dept HOD Context Switcher
        # -------------------------
        managed_depts = auth_service.get_managed_departments()
        if len(managed_depts) > 1:
            dept_lbl = QLabel("🏢 Active Department:")
            dept_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #94A3B8;")
            layout.addWidget(dept_lbl)

            self.dept_selector = QComboBox()
            self.dept_selector.setStyleSheet("""
                QComboBox { background: #1E293B; color: #38BDF8; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
                QComboBox::drop-down { border: none; }
            """)
            self.dept_selector.addItems(managed_depts)
            cur_active = auth_service.get_active_department()
            if cur_active:
                idx = self.dept_selector.findText(cur_active)
                if idx >= 0:
                    self.dept_selector.setCurrentIndex(idx)
            self.dept_selector.currentTextChanged.connect(self._handle_dept_changed)
            layout.addWidget(self.dept_selector)
            layout.addSpacing(6)

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

    def _handle_dept_changed(self, dept_name: str):
        if dept_name:
            auth_service.set_active_department(dept_name)
            self.department_context_changed.emit(dept_name)

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
            RoleEnum.TSO.value: [
                "Dashboard",
                "My Tasks",
                "History / Audit"
            ],
            "TSO": [
                "Dashboard",
                "My Tasks",
                "History / Audit"
            ],
            "Employee": [
                "Dashboard",
                "My Tasks",
                "History / Audit"
            ],
            RoleEnum.ADMINISTRATOR.value: [
                "Dashboard",
                "Admin Suite",
                "Documents",
                "History / Audit"
            ],
            "Administrator": [
                "Dashboard",
                "Admin Suite",
                "Documents",
                "History / Audit"
            ],
            "Read-only User": [
                "Dashboard",
                "Documents",
                "History / Audit"
            ]
        }
        return menus.get(role, ["Dashboard", "My Tasks", "History / Audit"])