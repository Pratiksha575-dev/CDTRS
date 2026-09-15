from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from api.client import api_client


def _list(data: Any, *keys: str) -> List[Dict[str, Any]]:
    """Normalize common API list response shapes."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


class DepartmentDialog(QDialog):
    """Dialog used to create or edit a department."""

    def __init__(
        self,
        department: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        super().__init__(parent)

        self.department = department or {}
        self.editing = bool(department)

        self.setWindowTitle(
            "Edit Department" if self.editing else "Add Department"
        )
        self.setMinimumWidth(450)

        # ------------------------------------------------------------------
        # Fields
        # ------------------------------------------------------------------

        self.name = QLineEdit(
            str(self.department.get("name") or "")
        )

        self.code = QLineEdit(
            str(self.department.get("code") or "")
        )

        self.active = QCheckBox("Department is active")
        self.active.setChecked(
            bool(self.department.get("is_active", True))
        )

        # A new department is active by default.
        # Status can be changed after creation through the main page.
        self.active.setEnabled(self.editing)

        # ------------------------------------------------------------------
        # Form
        # ------------------------------------------------------------------

        form = QFormLayout()
        form.setSpacing(12)

        form.addRow(
            "Department Name *",
            self.name,
        )

        form.addRow(
            "Department Code *",
            self.code,
        )

        form.addRow(
            "Status",
            self.active,
        )

        # ------------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )

        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate(self):
        name = self.name.text().strip()
        code = self.code.text().strip()

        if not name or not code:
            QMessageBox.warning(
                self,
                "Required",
                "Department name and code are required.",
            )
            return

        self.accept()

    def values(self) -> Dict[str, Any]:
        return {
            "name": self.name.text().strip(),
            "code": self.code.text().strip().upper(),
            "is_active": self.active.isChecked(),
        }


class DepartmentCard(QFrame):
    """Visual department row/card."""

    def __init__(
        self,
        department: Dict[str, Any],
        callback,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("departmentCard")

        active = bool(
            department.get("is_active", True)
        )

        name = QLabel(
            str(
                department.get("name")
                or "Unnamed Department"
            )
        )

        name.setStyleSheet(
            "font-size: 14px; "
            "font-weight: 700; "
            "color: #172033;"
        )

        code = QLabel(
            str(department.get("code") or "—")
        )
        code.setObjectName("muted")

        if active:
            status = QLabel("ACTIVE")
            status.setStyleSheet(
                "font-weight:700; "
                "padding:4px 8px; "
                "border-radius:6px; "
                "background:#ecfdf3; "
                "color:#067647;"
            )
        else:
            status = QLabel("INACTIVE")
            status.setStyleSheet(
                "font-weight:700; "
                "padding:4px 8px; "
                "border-radius:6px; "
                "background:#fef3f2; "
                "color:#b42318;"
            )

        edit = QPushButton("Edit")
        edit.clicked.connect(
            lambda: callback(
                "edit",
                department,
            )
        )

        toggle = QPushButton(
            "Deactivate" if active else "Activate"
        )

        toggle.clicked.connect(
            lambda: callback(
                "toggle",
                department,
            )
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(15, 12, 15, 12)
        row.setSpacing(12)

        row.addWidget(name, 1)
        row.addWidget(code)
        row.addWidget(status)
        row.addWidget(edit)
        row.addWidget(toggle)


class DepartmentConfigurationPage(QWidget):
    """
    Create, edit, activate and deactivate organisational departments.

    Department deletion is intentionally not exposed because the backend
    currently supports activation/deactivation rather than hard deletion.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName(
            "departmentConfigurationPage"
        )

        self.departments: List[
            Dict[str, Any]
        ] = []

        # ------------------------------------------------------------------
        # Header
        # ------------------------------------------------------------------

        title = QLabel(
            "Department Configuration"
        )
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Maintain the departments used by work contexts, "
            "routing branches, and organisational configuration."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)

        # ------------------------------------------------------------------
        # Search
        # ------------------------------------------------------------------

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search department name or code…"
        )
        self.search.textChanged.connect(
            self._render
        )

        # ------------------------------------------------------------------
        # Status filter
        # ------------------------------------------------------------------

        self.status_filter = QComboBox()
        self.status_filter.addItems(
            [
                "All Departments",
                "Active",
                "Inactive",
            ]
        )
        self.status_filter.currentIndexChanged.connect(
            self._render
        )

        # ------------------------------------------------------------------
        # Toolbar buttons
        # ------------------------------------------------------------------

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(
            self.load_departments
        )

        add = QPushButton(
            "+ Add Department"
        )
        add.setObjectName("primaryButton")
        add.clicked.connect(self._add)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(
            self.search,
            1,
        )

        toolbar.addWidget(
            self.status_filter
        )

        toolbar.addWidget(
            refresh
        )

        toolbar.addWidget(
            add
        )

        # ------------------------------------------------------------------
        # Department list
        # ------------------------------------------------------------------

        self.box = QWidget()

        self.list_layout = QVBoxLayout(
            self.box
        )
        self.list_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.list_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )
        scroll.setWidget(self.box)

        # ------------------------------------------------------------------
        # Main layout
        # ------------------------------------------------------------------

        root = QVBoxLayout(self)

        root.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        root.setSpacing(11)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addLayout(toolbar)
        root.addWidget(
            scroll,
            1,
        )

        # ------------------------------------------------------------------
        # Styling
        # ------------------------------------------------------------------

        self.setStyleSheet(
            """
            QWidget#departmentConfigurationPage {
                background: #f6f8fb;
            }

            QLabel#pageTitle {
                font-size: 23px;
                font-weight: 750;
                color: #172033;
            }

            QLabel#muted {
                color: #667085;
            }

            QLineEdit,
            QComboBox {
                min-height: 35px;
                background: white;
                border: 1px solid #d0d5dd;
                border-radius: 8px;
                padding: 0 9px;
            }

            QPushButton {
                min-height: 34px;
                background: white;
                border: 1px solid #d0d5dd;
                border-radius: 8px;
                padding: 0 12px;
            }

            QPushButton:hover {
                background: #f2f4f7;
            }

            QPushButton#primaryButton {
                background: #2563eb;
                color: white;
                border-color: #2563eb;
                font-weight: 650;
            }

            QFrame#departmentCard {
                background: white;
                border: 1px solid #e4e7ec;
                border-radius: 10px;
            }
            """
        )

        # ------------------------------------------------------------------
        # Initial load
        # ------------------------------------------------------------------

        self.load_departments()

    # ======================================================================
    # DATA
    # ======================================================================

    def load_departments(self):
        try:
            response = api_client.get(
                "/admin/departments"
            )

            self.departments = _list(
                response,
                "departments",
                "items",
            )

            self._render()

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Departments",
                f"Unable to load departments.\n\n{exc}",
            )

    # ======================================================================
    # RENDER
    # ======================================================================

    def _render(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        query = (
            self.search.text()
            .strip()
            .lower()
        )

        filter_value = (
            self.status_filter.currentText()
        )

        rows: List[
            Dict[str, Any]
        ] = []

        for dept in self.departments:
            active = bool(
                dept.get(
                    "is_active",
                    True,
                )
            )

            text = (
                f"{dept.get('name', '')} "
                f"{dept.get('code', '')}"
            ).lower()

            # Search filter
            if query and query not in text:
                continue

            # Status filter
            if (
                filter_value == "Active"
                and not active
            ):
                continue

            if (
                filter_value == "Inactive"
                and active
            ):
                continue

            rows.append(dept)

        if not rows:
            label = QLabel(
                "No departments match the current filters."
            )

            label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            label.setObjectName("muted")

            self.list_layout.addWidget(
                label
            )

            self.list_layout.addStretch(1)

            return

        for dept in rows:
            self.list_layout.addWidget(
                DepartmentCard(
                    dept,
                    self._action,
                )
            )

        self.list_layout.addStretch(1)

    # ======================================================================
    # ADD DEPARTMENT
    # ======================================================================

    def _add(self):
        dialog = DepartmentDialog(
            parent=self
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        try:
            api_client.post(
                "/admin/departments",
                json=dialog.values(),
            )

            self.load_departments()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Add Department Failed",
                str(exc),
            )

    # ======================================================================
    # EDIT / ACTIVATE / DEACTIVATE
    # ======================================================================

    def _action(
        self,
        action: str,
        dept: Dict[str, Any],
    ):
        dept_id = dept.get("id")

        if dept_id is None:
            QMessageBox.warning(
                self,
                "Department",
                "The selected department has no valid ID.",
            )
            return

        # --------------------------------------------------------------
        # EDIT
        # --------------------------------------------------------------

        if action == "edit":
            dialog = DepartmentDialog(
                dept,
                self,
            )

            if (
                dialog.exec()
                != QDialog.DialogCode.Accepted
            ):
                return

            payload = dialog.values()

        # --------------------------------------------------------------
        # TOGGLE STATUS
        # --------------------------------------------------------------

        else:
            active = bool(
                dept.get(
                    "is_active",
                    True,
                )
            )

            target = (
                "deactivate"
                if active
                else "activate"
            )

            department_name = (
                dept.get("name")
                or "this department"
            )

            result = QMessageBox.question(
                self,
                "Confirm Department Status",
                (
                    f"Are you sure you want to "
                    f"{target} {department_name}?"
                ),
            )

            if (
                result
                != QMessageBox.StandardButton.Yes
            ):
                return

            payload = {
                "is_active": not active
            }

        # --------------------------------------------------------------
        # API UPDATE
        # --------------------------------------------------------------

        try:
            api_client.put(
                f"/admin/departments/{dept_id}",
                json=payload,
            )

            self.load_departments()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Department Update Failed",
                str(exc),
            )


# Compatibility alias used by MainWindow/importers.
AdminDepartmentConfigurationPage = (
    DepartmentConfigurationPage
)