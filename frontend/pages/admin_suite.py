"""
CDTRS - Administrator Suite Page
Provides complete administrative control: User & Role provisioning, Department mapping,
Priority & Email configuration thresholds, and System Audit logs.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QTabWidget, QDialog, QFormLayout, QMessageBox,
    QTextEdit, QSpinBox, QGroupBox, QFrame
)

from config.settings import settings
from services.auth_service import auth_service
from repositories.provider import get_repository



class AddEditUserDialog(QDialog):
    """Dialog for creating or editing user accounts and role assignments."""
    def __init__(self, user_data: Optional[Dict[str, Any]] = None, departments: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.user_data = user_data or {}
        self.departments = departments or []
        self.setWindowTitle("Edit User Profile" if user_data else "Add New User")
        self.setMinimumWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.username_input = QLineEdit(self.user_data.get("username", ""))
        if self.user_data:
            self.username_input.setReadOnly(True)
            self.username_input.setStyleSheet("background: #F1F5F9; color: #64748B;")
        form.addRow("Username *:", self.username_input)

        self.fullname_input = QLineEdit(self.user_data.get("full_name", ""))
        form.addRow("Full Name *:", self.fullname_input)

        self.empcode_input = QLineEdit(self.user_data.get("employee_code", ""))
        form.addRow("Employee Code:", self.empcode_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["EMPLOYEE", "HOD", "TSO", "DS", "DIRECTOR", "ADMIN"])
        cur_role = (self.user_data.get("role") or "EMPLOYEE").upper()
        idx = self.role_combo.findText(cur_role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        form.addRow("System Role *:", self.role_combo)

        self.dept_combo = QComboBox()
        self.dept_combo.addItem("None", None)
        for d in self.departments:
            self.dept_combo.addItem(d, d)
        cur_dept = self.user_data.get("department")
        if cur_dept:
            d_idx = self.dept_combo.findText(cur_dept)
            if d_idx >= 0:
                self.dept_combo.setCurrentIndex(d_idx)
        form.addRow("Primary Department:", self.dept_combo)

        self.managed_input = QLineEdit()
        m_depts = self.user_data.get("managed_depts") or []
        if isinstance(m_depts, list):
            self.managed_input.setText(", ".join(m_depts))
        else:
            self.managed_input.setText(str(m_depts))
        self.managed_input.setPlaceholderText("e.g. PSTD, ESFS (for Multi-Dept HOD / TSO)")
        form.addRow("Managed Depts:", self.managed_input)

        self.designation_input = QLineEdit(self.user_data.get("designation", ""))
        self.designation_input.setPlaceholderText("e.g. Scientist 'E' / Head of Division")
        form.addRow("Designation:", self.designation_input)

        self.email_input = QLineEdit(self.user_data.get("email", ""))
        form.addRow("Primary Email:", self.email_input)

        self.outlook_input = QLineEdit(self.user_data.get("outlook_email", ""))
        form.addRow("Outlook Email:", self.outlook_input)

        self.gov_input = QLineEdit(self.user_data.get("gov_email", ""))
        form.addRow("NIC / Gov Email:", self.gov_input)

        if not self.user_data:
            self.pwd_input = QLineEdit("cdtrs@123")
            form.addRow("Initial Password:", self.pwd_input)

        layout.addLayout(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save User Profile")
        save_btn.setStyleSheet("background: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        save_btn.clicked.connect(self._handle_save)

        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def _handle_save(self):
        uname = self.username_input.text().strip()
        fname = self.fullname_input.text().strip()
        if not uname or not fname:
            QMessageBox.warning(self, "Validation Error", "Username and Full Name are required.")
            return

        managed_raw = self.managed_input.text().strip()
        managed_list = [d.strip().upper() for d in managed_raw.split(",") if d.strip()] if managed_raw else []

        self.result_data = {
            "username": uname,
            "full_name": fname,
            "employee_code": self.empcode_input.text().strip(),
            "role": self.role_combo.currentText(),
            "department": self.dept_combo.currentText() if self.dept_combo.currentText() != "None" else None,
            "department_name": self.dept_combo.currentText() if self.dept_combo.currentText() != "None" else None,
            "managed_depts": managed_list,
            "designation": self.designation_input.text().strip(),
            "email": self.email_input.text().strip() or None,
            "outlook_email": self.outlook_input.text().strip() or None,
            "gov_email": self.gov_input.text().strip() or None,
        }
        if not self.user_data:
            self.result_data["password"] = self.pwd_input.text().strip() or "cdtrs@123"

        self.accept()


class AdminSuitePage(QWidget):
    """Administrator Suite for CDTRS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._departments: List[Dict[str, Any]] = []
        self._users: List[Dict[str, Any]] = []
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🛡️ CDTRS System Administration Suite")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Manage organizational hierarchy, multi-department HODs, priority thresholds, and security audits.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        hdr.addLayout(title_box)
        hdr.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.setStyleSheet("padding: 6px 14px; font-weight: bold;")
        refresh_btn.clicked.connect(self.load_data)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: bold; padding: 8px 16px; font-size: 12px; }
            QTabBar::tab:selected { color: #2563EB; border-bottom: 2px solid #2563EB; }
        """)

        # Tab 1: Users & Roles
        self.tab_users = self._build_users_tab()
        self.tabs.addTab(self.tab_users, "👥 Users & Roles")

        # Tab 2: Departments & Mapping
        self.tab_depts = self._build_depts_tab()
        self.tabs.addTab(self.tab_depts, "🏢 Departments")

        # Tab 3: Priority & Settings
        self.tab_settings = self._build_settings_tab()
        self.tabs.addTab(self.tab_settings, "⚙️ Priority & Email Config")

        # Tab 4: Audit Logs
        self.tab_audit = self._build_audit_tab()
        self.tabs.addTab(self.tab_audit, "📜 Security & Audit Trail")

        layout.addWidget(self.tabs)

    def _build_users_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # Controls
        ctrls = QHBoxLayout()
        self.user_search = QLineEdit()
        self.user_search.setPlaceholderText("🔍 Search by name, username, or code...")
        self.user_search.textChanged.connect(self._filter_users_table)
        ctrls.addWidget(self.user_search)

        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "ADMIN", "DIRECTOR", "DS", "TSO", "HOD", "EMPLOYEE"])
        self.role_filter.currentIndexChanged.connect(self._filter_users_table)
        ctrls.addWidget(self.role_filter)

        ctrls.addStretch()

        add_user_btn = QPushButton("+ Add New User")
        add_user_btn.setStyleSheet("background: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_user_btn.clicked.connect(self._handle_add_user)
        ctrls.addWidget(add_user_btn)
        layout.addLayout(ctrls)

        # Users Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels([
            "Username", "Emp Code", "Full Name", "Role", "Primary Dept", "Managed Depts", "Status", "Actions"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setAlternatingRowColors(True)
        layout.addWidget(self.users_table)

        return widget

    def _build_depts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        top_box = QHBoxLayout()
        lbl = QLabel("15 Canonical NMRL Divisions & Specialized Cells")
        lbl.setStyleSheet("font-weight: bold; color: #334155;")
        top_box.addWidget(lbl)
        top_box.addStretch()

        add_dept_btn = QPushButton("+ Add Department")
        add_dept_btn.setStyleSheet("background: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_dept_btn.clicked.connect(self._handle_add_dept)
        top_box.addWidget(add_dept_btn)
        layout.addLayout(top_box)

        self.depts_table = QTableWidget()
        self.depts_table.setColumnCount(4)
        self.depts_table.setHorizontalHeaderLabels(["Department Name", "Code", "Status", "Actions"])
        self.depts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.depts_table.verticalHeader().setVisible(False)
        self.depts_table.setAlternatingRowColors(True)
        layout.addWidget(self.depts_table)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        # Priority Thresholds Group
        p_grp = QGroupBox("Dynamic Priority Countdown Thresholds (SRS BR-6 / FR-5.5)")
        p_layout = QFormLayout(p_grp)
        p_layout.setSpacing(10)

        self.red_spin = QSpinBox()
        self.red_spin.setRange(-30, 10)
        self.red_spin.setValue(0)
        p_layout.addRow("🔴 Red / Urgent (Days Left <=):", self.red_spin)

        self.orange_spin = QSpinBox()
        self.orange_spin.setRange(1, 30)
        self.orange_spin.setValue(3)
        p_layout.addRow("🟠 Orange / High (Days Left <=):", self.orange_spin)

        self.yellow_spin = QSpinBox()
        self.yellow_spin.setRange(1, 60)
        self.yellow_spin.setValue(7)
        p_layout.addRow("🟡 Yellow / Medium (Days Left <=):", self.yellow_spin)

        layout.addWidget(p_grp)

        # Email Template Group
        e_grp = QGroupBox("Action Reminder Email Template (SRS FR-6.7)")
        e_layout = QFormLayout(e_grp)
        e_layout.setSpacing(10)

        self.email_subj = QLineEdit("ACTION REQUIRED: CDTRS Document Reminder - {reference}")
        e_layout.addRow("Email Subject:", self.email_subj)

        self.email_tmpl = QTextEdit()
        self.email_tmpl.setPlainText("Dear {assignee_name},\n\nThis is an automated reminder regarding document '{title}' (Ref: {reference}).\nDeadline: {deadline} ({days_left} remaining).\n\nPlease review and take necessary action.\n\nCDTRS Automated Dispatch System")
        self.email_tmpl.setMaximumHeight(120)
        e_layout.addRow("Email Body Template:", self.email_tmpl)

        layout.addWidget(e_grp)

        save_cfg_btn = QPushButton("💾 Save Configuration Changes")
        save_cfg_btn.setStyleSheet("background: #2563EB; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        save_cfg_btn.clicked.connect(self._handle_save_settings)
        layout.addWidget(save_cfg_btn, alignment=Qt.AlignRight)

        layout.addStretch()
        return widget

    def _build_audit_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Timestamp", "Admin User", "Action", "Target Entity", "Details"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.audit_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.audit_table.verticalHeader().setVisible(False)
        self.audit_table.setAlternatingRowColors(True)
        layout.addWidget(self.audit_table)

        return widget

    def load_data(self):
        """Loads live data from API / database."""
        from api.client import api_client

        try:
            # 1. Departments
            d_data = api_client.get(f"{settings.api_url}/admin/departments")
            if isinstance(d_data, list):
                self._departments = d_data
                self._populate_depts_table()

            # 2. Users
            u_data = api_client.get(f"{settings.api_url}/admin/users")
            if isinstance(u_data, list):
                self._users = u_data
                self._populate_users_table(self._users)

            # 3. Settings
            s_data = api_client.get(f"{settings.api_url}/admin/settings")
            if isinstance(s_data, dict):
                self.red_spin.setValue(int(s_data.get("priority_red_days", 0)))
                self.orange_spin.setValue(int(s_data.get("priority_orange_days", 3)))
                self.yellow_spin.setValue(int(s_data.get("priority_yellow_days", 7)))
                self.email_subj.setText(s_data.get("reminder_email_subject", ""))
                self.email_tmpl.setPlainText(s_data.get("reminder_email_template", ""))

            # 4. Audit logs
            a_data = api_client.get(f"{settings.api_url}/admin/audit-logs")
            if isinstance(a_data, list):
                self._populate_audit_table(a_data)

        except Exception as e:
            print(f"[AdminSuite] Notice loading data: {e}")


    def _populate_users_table(self, users: List[Dict[str, Any]]):
        self.users_table.setRowCount(len(users))
        for r, u in enumerate(users):
            self.users_table.setItem(r, 0, QTableWidgetItem(u.get("username", "")))
            self.users_table.setItem(r, 1, QTableWidgetItem(u.get("employee_code") or "-"))
            self.users_table.setItem(r, 2, QTableWidgetItem(u.get("full_name", "")))
            self.users_table.setItem(r, 3, QTableWidgetItem(u.get("role", "")))
            self.users_table.setItem(r, 4, QTableWidgetItem(u.get("department") or "-"))

            m = u.get("managed_depts") or []
            m_str = ", ".join(m) if isinstance(m, list) else str(m)
            self.users_table.setItem(r, 5, QTableWidgetItem(m_str or "-"))

            st = "Active" if u.get("is_active", True) else "Suspended"
            st_item = QTableWidgetItem(st)
            st_item.setForeground(Qt.darkGreen if st == "Active" else Qt.red)
            self.users_table.setItem(r, 6, st_item)

            # Actions cell
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(4)

            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            edit_btn.clicked.connect(lambda _, user=u: self._handle_edit_user(user))

            pwd_btn = QPushButton("🔑 Pwd")
            pwd_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            pwd_btn.clicked.connect(lambda _, user=u: self._handle_reset_password(user))

            act_layout.addWidget(edit_btn)
            act_layout.addWidget(pwd_btn)
            self.users_table.setCellWidget(r, 7, act_widget)

    def _filter_users_table(self):
        query = self.user_search.text().strip().lower()
        role_filt = self.role_filter.currentText().upper()

        filtered = []
        for u in self._users:
            uname = u.get("username", "").lower()
            fname = u.get("full_name", "").lower()
            code = (u.get("employee_code") or "").lower()
            dept = (u.get("department") or "").lower()
            u_role = (u.get("role") or "").upper()

            matches_query = not query or (query in uname or query in fname or query in code or query in dept)
            matches_role = role_filt == "ALL ROLES" or u_role == role_filt

            if matches_query and matches_role:
                filtered.append(u)

        self._populate_users_table(filtered)

    def _populate_depts_table(self):
        self.depts_table.setRowCount(len(self._departments))
        for r, d in enumerate(self._departments):
            self.depts_table.setItem(r, 0, QTableWidgetItem(d.get("name", "")))
            self.depts_table.setItem(r, 1, QTableWidgetItem(d.get("code", "")))
            st = "Active" if d.get("is_active", True) else "Inactive"
            self.depts_table.setItem(r, 2, QTableWidgetItem(st))

            act_btn = QPushButton("✏️ Edit")
            act_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            act_btn.clicked.connect(lambda _, dept=d: self._handle_edit_dept(dept))
            self.depts_table.setCellWidget(r, 3, act_btn)

    def _populate_audit_table(self, logs: List[Dict[str, Any]]):
        self.audit_table.setRowCount(len(logs))
        for r, l in enumerate(logs):
            self.audit_table.setItem(r, 0, QTableWidgetItem(l.get("created_at") or "-"))
            self.audit_table.setItem(r, 1, QTableWidgetItem(l.get("username") or f"id:{l.get('user_id', '?')}"))
            self.audit_table.setItem(r, 2, QTableWidgetItem(l.get("action") or "-"))
            self.audit_table.setItem(r, 3, QTableWidgetItem(f"{l.get('entity_type') or ''} #{l.get('entity_id') or ''}"))
            self.audit_table.setItem(r, 4, QTableWidgetItem(l.get("description") or "-"))

    def _handle_add_user(self):
        from api.client import api_client
        dept_names = [d["name"] for d in self._departments]
        dialog = AddEditUserDialog(departments=dept_names, parent=self)
        if dialog.exec():
            try:
                res = api_client.post(f"{settings.api_url}/admin/users", json=dialog.result_data)
                QMessageBox.information(self, "Success", "User created successfully.")
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create user: {e}")

    def _handle_edit_user(self, user: Dict[str, Any]):
        from api.client import api_client
        dept_names = [d["name"] for d in self._departments]
        dialog = AddEditUserDialog(user_data=user, departments=dept_names, parent=self)
        if dialog.exec():
            try:
                res = api_client.put(f"{settings.api_url}/admin/users/{user['id']}", json=dialog.result_data)
                QMessageBox.information(self, "Success", "User updated successfully.")
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update user: {e}")

    def _handle_reset_password(self, user: Dict[str, Any]):
        from api.client import api_client
        from PySide6.QtWidgets import QInputDialog
        pwd, ok = QInputDialog.getText(self, "Reset Password", f"Enter new password for '{user['username']}':")
        if ok and pwd.strip():
            try:
                res = api_client.post(f"{settings.api_url}/admin/users/{user['id']}/reset-password", json={"new_password": pwd.strip()})
                QMessageBox.information(self, "Success", f"Password reset for {user['username']}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed: {e}")

    def _handle_add_dept(self):
        from api.client import api_client
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Department", "Enter Department Name / Code:")
        if ok and name.strip():
            try:
                res = api_client.post(f"{settings.api_url}/admin/departments", json={"name": name.strip(), "code": name.strip().upper()})
                QMessageBox.information(self, "Success", "Department added.")
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed: {e}")

    def _handle_edit_dept(self, dept: Dict[str, Any]):
        from api.client import api_client
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Edit Department", "Enter new name:", text=dept.get("name", ""))
        if ok and name.strip():
            try:
                res = api_client.put(f"{settings.api_url}/admin/departments/{dept['id']}", json={"name": name.strip()})
                QMessageBox.information(self, "Success", "Department updated.")
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed: {e}")

    def _handle_save_settings(self):
        from api.client import api_client
        payload = {
            "priority_red_days": str(self.red_spin.value()),
            "priority_orange_days": str(self.orange_spin.value()),
            "priority_yellow_days": str(self.yellow_spin.value()),
            "reminder_email_subject": self.email_subj.text().strip(),
            "reminder_email_template": self.email_tmpl.toPlainText().strip()
        }
        try:
            res = api_client.post(f"{settings.api_url}/admin/settings", json=payload)
            QMessageBox.information(self, "Success", "System configuration saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed: {e}")

