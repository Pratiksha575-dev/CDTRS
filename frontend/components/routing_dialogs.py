from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from repositories.provider import get_repository
try:
    from context_manager import context_manager
except Exception:
    context_manager = None


class RouteToHODDialog(QDialog):
    """
    Modal dialog for DS routing a document to a Department Head (HOD).
    Remarks are not requested as routing is a direct structural action.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Route to HOD - {document.reference}")
        self.setMinimumSize(360, 180)
        self.setMaximumSize(640, 420)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Route Document to Department Head (HOD)")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #0F172A;"
        )

        subtitle = QLabel(f"Document: {self.document.title}")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.dept_combo = QComboBox()
        repo = get_repository()
        departments = repo.get_departments()
        self._dept_map = {}

        target_dept = self.document.suggested_department_name

        if not target_dept and self.document.id:
            try:
                s_data = repo.get_routing_suggestion(self.document.id) or {}
                target_dept = s_data.get("suggested_department_name")
            except Exception:
                pass

        if departments:
            for d in departments:
                if d.name.lower() != "administration":
                    self.dept_combo.addItem(d.name, d.id)
                    self._dept_map[d.name] = d.id
        else:
            self.dept_combo.addItem(
                "⚠ Could not load departments — check connection",
                None,
            )

        if target_dept and departments:
            alias_map = {
                "human resources": "hr",
                "it": "technical",
                "information technology": "technical",
                "systems": "technical",
                "operations": "administration",
                "legal": "administration",
            }

            norm_target = alias_map.get(
                target_dept.lower(),
                target_dept,
            ).lower()

            for i in range(self.dept_combo.count()):
                item_text = self.dept_combo.itemText(i).lower()

                if (
                    norm_target == item_text
                    or norm_target in item_text
                    or item_text in norm_target
                ):
                    self.dept_combo.setCurrentIndex(i)
                    break

        form.addRow("Select Department:", self.dept_combo)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm Route to HOD")
        confirm_btn.setStyleSheet(
            "background-color: #0F172A; color: white; "
            "font-weight: 600; padding: 7px 16px; border-radius: 5px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_confirm(self):
        if self._is_confirmed:
            return

        self._is_confirmed = True
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        dept_name = self.dept_combo.currentText()
        dept_id = self.dept_combo.currentData()

        if dept_id is None:
            dept_id = self._dept_map.get(dept_name)

        return {
            "department_name": dept_name,
            "department_id": dept_id,
            "remarks": None,
        }


class RouteToEmployeeDialog(QDialog):
    """
    Modal dialog for DS routing a document directly to an explicitly
    identified Employee.

    DS may optionally require HOD validation before the employee's
    progress updates reach DS.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Route to Employee - {document.reference}")
        self.setMinimumSize(380, 200)
        self.setMaximumSize(680, 480)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Direct Route to Employee")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #0F172A;"
        )

        subtitle = QLabel(
            f"Document: {self.document.title}\n"
            "(Direct routing when staff is explicitly identified)"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.emp_combo = QComboBox()
        repo = get_repository()
        employees = repo.get_users(role="Employee")
        self._emp_map = {}

        target_emp = self.document.suggested_employee_name

        if not target_emp and self.document.id:
            try:
                s_data = repo.get_routing_suggestion(self.document.id) or {}
                target_emp = s_data.get("suggested_employee_name")
            except Exception:
                pass

        if employees:
            for emp in employees:
                label = (
                    f"{emp.full_name} "
                    f"({emp.department_name or 'General'})"
                )

                self.emp_combo.addItem(label, emp.id)
                self._emp_map[label] = emp.id

            if target_emp:
                for i in range(self.emp_combo.count()):
                    item_text = self.emp_combo.itemText(i).lower()

                    if target_emp.lower() in item_text:
                        self.emp_combo.setCurrentIndex(i)
                        break
        else:
            # Backend unreachable — show placeholder;
            # do not insert hardcoded employees.
            self.emp_combo.addItem(
                "⚠ Could not load employees — check connection",
                None,
            )

        form.addRow("Select Staff:", self.emp_combo)

        # ---------------------------------------------------------
        # HOD VALIDATION OPTION
        # ---------------------------------------------------------
        self.val_checkbox = QCheckBox(
            "Require HOD validation before progress reaches DS"
        )
        self.val_checkbox.setStyleSheet(
            "color: #0F172A; "
            "font-weight: 600; "
            "font-size: 12px; "
            "margin-top: 4px;"
        )

        # Direct Employee routing defaults to NO HOD validation.
        self.val_checkbox.setChecked(False)

        form.addRow("", self.val_checkbox)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm Route to Staff")
        confirm_btn.setStyleSheet(
            "background-color: #0284C7; color: white; "
            "font-weight: 600; padding: 7px 16px; border-radius: 5px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_confirm(self):
        if self._is_confirmed:
            return

        self._is_confirmed = True
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        emp_id = self.emp_combo.currentData()
        emp_text = self.emp_combo.currentText().split(" (")[0]

        return {
            "employee_id": emp_id,
            "employee_name": emp_text,
            "remarks": None,
            "requires_hod_validation": self.val_checkbox.isChecked(),
        }


def _document_routed_department(document: DocumentModel):
    """Resolve a confirmed department from canonical routing/assignment data."""
    assignments = getattr(document, "work_assignments", None) or []
    for assignment in assignments:
        if getattr(assignment, "is_active", True) is False:
            continue
        routing = getattr(assignment, "routing", None)
        dept = getattr(assignment, "department", None)
        if dept:
            return getattr(dept, "name", None) or str(dept)
        dept_name = getattr(assignment, "department_name", None)
        if dept_name:
            return dept_name
        if routing:
            dept = getattr(routing, "department", None)
            if dept:
                return getattr(dept, "name", None) or str(dept)
            dept_name = getattr(routing, "department_name", None)
            if dept_name:
                return dept_name
    return None

def _document_routed_department_id(document: DocumentModel):
    assignments = getattr(document, "work_assignments", None) or []
    for assignment in assignments:
        if getattr(assignment, "is_active", True) is False:
            continue
        value = getattr(assignment, "department_id", None)
        if value:
            return value
        routing = getattr(assignment, "routing", None)
        value = getattr(routing, "department_id", None) if routing else None
        if value:
            return value
    return None


class HODAssignEmployeeDialog(QDialog):
    """
    Modal dialog for Department Head (HOD) delegating execution
    of a document to a departmental Employee.

    Includes option to require HOD validation before progress
    reports reach DS.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Assign Document - {document.reference}")
        self.setMinimumWidth(440)
        self.setMaximumWidth(620)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Delegate Task to Departmental Staff")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #0F172A;"
        )

        dept_name = _document_routed_department(self.document) or self.document.suggested_department_name or "Department"

        subtitle = QLabel(
            f"Document: {self.document.title}\n"
            f"Department: {dept_name}"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.emp_combo = QComboBox()
        repo = get_repository()

        dept_name = _document_routed_department(self.document) or self.document.suggested_department_name or "Department"

        dept_id = _document_routed_department_id(self.document)

        if not dept_id and dept_name:
            all_depts = repo.get_departments()

            for d in all_depts:
                if d.name.upper() == dept_name.upper():
                    dept_id = d.id
                    break

        employees = repo.get_users(
            role="Employee",
            department_id=dept_id,
        )

        if not employees and dept_name:
            all_emps = repo.get_users(role="Employee")

            employees = [
                u
                for u in all_emps
                if u.department_name
                and u.department_name.upper() == dept_name.upper()
            ]

        if not employees:
            employees = repo.get_users(role="Employee")

        if employees:
            for emp in employees:
                code_str = (
                    f" [{emp.employee_code}]"
                    if getattr(emp, "employee_code", None)
                    else ""
                )

                label = (
                    f"{emp.full_name}{code_str} "
                    f"({emp.department_name or 'General'})"
                )

                self.emp_combo.addItem(label, emp.id)
        else:
            self.emp_combo.addItem(
                "⚠ No employees found for this department",
                None,
            )

        form.addRow("Assign To:", self.emp_combo)

        # Show existing HOD remark that will be forwarded
        if getattr(self.document, "hod_remark", None):
            rem_note = QLabel(
                f"<b>Forwarded HOD Remark:</b> "
                f"<i>{self.document.hod_remark}</i>"
            )
            rem_note.setStyleSheet(
                "color: #0284C7; "
                "font-size: 11px; "
                "padding: 4px 0px;"
            )
            rem_note.setWordWrap(True)
            form.addRow("", rem_note)

        self.val_checkbox = QCheckBox(
            "Require HOD validation before progress updates reach DS"
        )
        self.val_checkbox.setStyleSheet(
            "color: #0F172A; "
            "font-weight: 600; "
            "font-size: 12px; "
            "margin-top: 4px;"
        )
        self.val_checkbox.setChecked(False)

        form.addRow("", self.val_checkbox)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        assign_btn = QPushButton("Confirm Work Assignment")
        assign_btn.setStyleSheet(
            "background-color: #0F172A; color: white; "
            "font-weight: 600; padding: 7px 16px; border-radius: 5px;"
        )
        assign_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(assign_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_confirm(self):
        if self._is_confirmed:
            return

        self._is_confirmed = True
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        emp_id = self.emp_combo.currentData()
        emp_text = self.emp_combo.currentText().split(" (")[0]

        return {
            "assigned_to_id": emp_id,
            "employee_name": emp_text,
            "instructions": getattr(
                self.document,
                "hod_remark",
                "",
            ) or None,
            "requires_hod_validation": self.val_checkbox.isChecked(),
        }



class _TeamAssignmentDialog(QDialog):
    """
    Shared UI for assigning one work assignment to multiple employees.

    The backend stores this as one WorkAssignment with multiple
    WorkAssignmentMember rows. This dialog only collects assignment data;
    it does not perform routing or infer workflow actions.
    """

    def __init__(
        self,
        document: DocumentModel,
        *,
        mode: str,
        routing_id: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.document = document
        self.mode = mode
        self.routing_id = routing_id
        self._is_confirmed = False

        self.setModal(True)
        self.setWindowTitle(
            f"{'Assign Team' if mode == 'HOD' else 'Create Team Assignment'}"
            f" - {document.reference}"
        )
        self.setMinimumWidth(520)
        self.setMaximumWidth(760)
        self.setMinimumHeight(520)
        self.resize(620, 620)
        self.setSizeGripEnabled(True)

        self._employees = []
        self._load_employees()
        self.setup_ui()

    def _load_employees(self):
        repo = get_repository()

        target_department_id = _document_routed_department_id(self.document)
        target_department_name = _document_routed_department(self.document) or getattr(
            self.document, "suggested_department_name", None
        )

        try:
            if self.mode == "HOD":
                # HOD assignment is departmental. Keep the UI restricted to
                # the document's target department; the backend is still the
                # final authority.
                employees = (
                    repo.get_users(
                        role="Employee",
                        department_id=target_department_id,
                    )
                    if target_department_id
                    else []
                )

                if not employees and target_department_name:
                    all_employees = repo.get_users(role="Employee") or []
                    employees = [
                        user
                        for user in all_employees
                        if (
                            getattr(user, "department_name", None)
                            and user.department_name.upper()
                            == target_department_name.upper()
                        )
                    ]

                self._employees = employees or []
            else:
                # DS may form cross-department teams. The backend validates
                # whether the selected employees belong to routed branches.
                self._employees = repo.get_users(role="Employee") or []
        except Exception:
            self._employees = []

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        if self.mode == "HOD":
            title_text = "Assign Work to Multiple Departmental Employees"
            note_text = (
                "Select two or more employees from this department. "
                "They will share one work assignment."
            )
            button_text = "Confirm Team Assignment"
        else:
            title_text = "Create Cross-Department Team Assignment"
            note_text = (
                "Select two or more employees. Cross-department teams are "
                "allowed when they belong to the document's routed branches."
            )
            button_text = "Create Team Assignment"

        title = QLabel(title_text)
        title.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #0F172A;"
        )

        subtitle = QLabel(
            f"Document: {self.document.title}\n{note_text}"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(9)

        self.team_name_input = QComboBox()
        self.team_name_input.setEditable(True)
        self.team_name_input.setPlaceholderText("Optional team name")
        self.team_name_input.setCurrentText("")
        form.addRow("Team Name:", self.team_name_input)

        self.member_list = QListWidget()
        self.member_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        self.member_list.setMinimumHeight(230)

        if self._employees:
            for employee in self._employees:
                code = getattr(employee, "employee_code", None)
                code_text = f" [{code}]" if code else ""
                department = (
                    getattr(employee, "department_name", None)
                    or "General"
                )
                item = QListWidgetItem(
                    f"{employee.full_name}{code_text} ({department})"
                )
                item.setData(Qt.ItemDataRole.UserRole, employee.id)
                self.member_list.addItem(item)
        else:
            item = QListWidgetItem(
                "⚠ No eligible employees could be loaded — check connection"
            )
            item.setData(Qt.ItemDataRole.UserRole, None)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.member_list.addItem(item)

        form.addRow("Team Members:", self.member_list)

        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText(
            "Optional instructions for the team..."
        )
        self.instructions_input.setMaximumHeight(75)
        form.addRow("Instructions:", self.instructions_input)

        self.validation_checkbox = QCheckBox(
            "Require HOD validation before progress reaches DS"
        )
        self.validation_checkbox.setChecked(False)
        self.validation_checkbox.setStyleSheet(
            "color: #0F172A; font-weight: 600; font-size: 11px;"
        )
        form.addRow("", self.validation_checkbox)

        layout.addLayout(form)

        selection_note = QLabel(
            "Select at least two employees. The first selected employee is "
            "kept as the compatibility primary assignee by the backend."
        )
        selection_note.setWordWrap(True)
        selection_note.setStyleSheet(
            "color: #64748B; font-size: 10px; padding: 2px 0px;"
        )
        layout.addWidget(selection_note)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton(button_text)
        confirm_btn.setStyleSheet(
            "background-color: #0F172A; color: white; "
            "font-weight: 600; padding: 7px 16px; border-radius: 5px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(confirm_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _selected_member_ids(self) -> List[Any]:
        ids = []
        for item in self.member_list.selectedItems():
            user_id = item.data(Qt.ItemDataRole.UserRole)
            if user_id is not None:
                ids.append(user_id)
        return ids

    def _on_confirm(self):
        if self._is_confirmed:
            return

        member_ids = self._selected_member_ids()
        if len(member_ids) < 2:
            QMessageBox.warning(
                self,
                "Team Members Required",
                "Please select at least two employees for a team assignment.",
            )
            return

        if len(member_ids) != len(set(member_ids)):
            QMessageBox.warning(
                self,
                "Duplicate Team Member",
                "Each employee can appear only once in the team.",
            )
            return

        self._is_confirmed = True
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        return {
            "member_user_ids": self._selected_member_ids(),
            "routing_id": self.routing_id,
            "team_name": (
                self.team_name_input.currentText().strip() or None
            ),
            "instructions": (
                self.instructions_input.toPlainText().strip() or None
            ),
            "requires_hod_validation": (
                self.validation_checkbox.isChecked()
            ),
        }


class HODAssignTeamDialog(_TeamAssignmentDialog):
    """HOD-facing multi-employee work-assignment dialog."""

    def __init__(
        self,
        document: DocumentModel,
        routing_id: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            document,
            mode="HOD",
            routing_id=routing_id,
            parent=parent,
        )


class DSTeamAssignmentDialog(_TeamAssignmentDialog):
    """
    DS-facing team-assignment dialog.

    DS may select employees across departments; the backend remains
    authoritative for branch membership and permissions.
    """

    def __init__(
        self,
        document: DocumentModel,
        routing_id: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            document,
            mode="DS",
            routing_id=routing_id,
            parent=parent,
        )


class UniversalRoutingDialog(QDialog):
    """
    Unified DS routing dialog.

    One routing workspace supports all operational routing combinations:
      - Department / HOD branch
      - Direct Employee branch (with optional HOD validation)
      - TSO branch

    Multiple routing rows may be added, allowing mixed and cross-department
    routing without creating separate routing dialogs/buttons.
    """

    ROUTE_DEPARTMENT = "DEPARTMENT_HOD"
    ROUTE_EMPLOYEE = "DIRECT_EMPLOYEE"
    ROUTE_TSO = "TSO"

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.row_items: List[Dict[str, Any]] = []
        self._departments = []
        self._all_employees = []

        self.setWindowTitle(f"Route Document - {document.reference}")
        self.setMinimumSize(520, 420)
        self.setMaximumSize(980, 760)
        self.resize(700, 560)
        self.setSizeGripEnabled(True)

        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(22, 20, 22, 20)
        root_layout.setSpacing(12)

        title = QLabel("Route Document")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #0F172A;"
        )

        subtitle = QLabel(
            f"Document: {self.document.title}\n"
            "Choose one or more routing targets. Each route can progress independently."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        repo = get_repository()
        self._departments = [
            d for d in (repo.get_departments() or [])
            if (d.name or "").lower() != "administration"
        ]
        self._all_employees = repo.get_users(role="Employee") or []

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: 1px solid #E2E8F0; "
            "border-radius: 6px; background: #FFFFFF; }"
        )

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(10, 10, 10, 10)
        self.rows_layout.setSpacing(10)
        self.rows_layout.addStretch()
        self.scroll_area.setWidget(self.rows_container)
        root_layout.addWidget(self.scroll_area, 1)

        self._add_row(prefill=True)

        add_btn_row = QHBoxLayout()
        self.add_row_btn = QPushButton("➕ Add Another Route")
        self.add_row_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #0F172A; "
            "border: 1px solid #CBD5E1; font-weight: 600; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        self.add_row_btn.clicked.connect(self._add_row)
        add_btn_row.addWidget(self.add_row_btn)
        add_btn_row.addStretch()
        root_layout.addLayout(add_btn_row)

        note = QLabel(
            "Department = route to that department's HOD. "
            "Employee = direct staff route. TSO uses the system's active TSO."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #64748B; font-size: 11px; padding: 2px 0px;"
        )
        root_layout.addWidget(note)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm Routing")
        confirm_btn.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: 600; "
            "padding: 8px 18px; border-radius: 5px;"
        )
        confirm_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        root_layout.addLayout(btn_layout)

        self.setLayout(root_layout)

    def _suggested_employee_id(self):
        value = getattr(self.document, "suggested_employee_id", None)
        if value:
            return value

        name = getattr(self.document, "suggested_employee_name", None)
        if not name or name in ("Not specified", "Not Assigned", "None"):
            return None

        for emp in self._all_employees:
            if emp.full_name and name.lower() in emp.full_name.lower():
                return emp.id
        return None

    def _suggested_department_id(self):
        value = getattr(self.document, "suggested_department_id", None)
        if value:
            return value

        name = (
            getattr(self.document, "suggested_department_name", None)
            or getattr(self.document, "suggested_department_name", None)
        )
        if not name:
            return None

        name_lower = name.lower()
        for dept in self._departments:
            dept_name = (dept.name or "").lower()
            if (
                dept_name == name_lower
                or dept_name in name_lower
                or name_lower in dept_name
            ):
                return dept.id
        return None

    def _populate_employee_combo(self, combo: QComboBox, selected_id=None):
        combo.clear()
        combo.addItem("-- Select Employee --", None)

        for emp in self._all_employees:
            label = f"{emp.full_name} ({emp.department_name or 'General'})"
            combo.addItem(label, emp.id)

        if selected_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == selected_id:
                    combo.setCurrentIndex(i)
                    break

    def _add_row(self, prefill: bool = False):
        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; "
            "border-radius: 6px; }"
        )

        row_vbox = QVBoxLayout(row_frame)
        row_vbox.setContentsMargins(10, 10, 10, 10)
        row_vbox.setSpacing(7)

        header = QHBoxLayout()
        row_index = len(self.row_items) + 1
        header_label = QLabel(f"Routing #{row_index}")
        header_label.setStyleSheet(
            "font-weight: 700; color: #0F172A; font-size: 12px;"
        )
        header.addWidget(header_label)
        header.addStretch()

        remove_btn = QPushButton("✕ Remove")
        remove_btn.setStyleSheet(
            "background: transparent; color: #DC2626; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        header.addWidget(remove_btn)
        row_vbox.addLayout(header)

        form = QFormLayout()
        form.setSpacing(7)

        route_type_combo = QComboBox()
        route_type_combo.addItem("Department / HOD", self.ROUTE_DEPARTMENT)
        route_type_combo.addItem("Direct Employee", self.ROUTE_EMPLOYEE)
        route_type_combo.addItem("TSO", self.ROUTE_TSO)

        dept_combo = QComboBox()
        dept_combo.addItem("-- Select Department --", None)
        for dept in self._departments:
            dept_combo.addItem(dept.name, dept.id)

        employee_combo = QComboBox()
        self._populate_employee_combo(employee_combo)

        employee_hint = QLabel(
            "Select an eligible employee. The backend validates the final assignment."
        )
        employee_hint.setStyleSheet("color: #64748B; font-size: 10px;")
        employee_hint.setWordWrap(True)

        tso_label = QLabel(
            "TSO route — the backend resolves the authorized TSO for the active DS context."
        )
        tso_label.setStyleSheet(
            "color: #0F172A; background-color: #F1F5F9; "
            "border: 1px solid #CBD5E1; border-radius: 4px; padding: 6px;"
        )
        tso_label.setWordWrap(True)

        dept_widget = QWidget()
        dept_layout = QVBoxLayout(dept_widget)
        dept_layout.setContentsMargins(0, 0, 0, 0)
        dept_layout.setSpacing(3)
        dept_layout.addWidget(dept_combo)

        employee_widget = QWidget()
        employee_layout = QVBoxLayout(employee_widget)
        employee_layout.setContentsMargins(0, 0, 0, 0)
        employee_layout.setSpacing(3)
        employee_layout.addWidget(employee_combo)
        employee_layout.addWidget(employee_hint)

        tso_widget = QWidget()
        tso_layout = QVBoxLayout(tso_widget)
        tso_layout.setContentsMargins(0, 0, 0, 0)
        tso_layout.addWidget(tso_label)

        instructions_edit = QTextEdit()
        instructions_edit.setPlaceholderText(
            "Optional instructions for this route..."
        )
        instructions_edit.setMaximumHeight(58)

        validation_checkbox = QCheckBox(
            "Require HOD validation before progress reaches DS"
        )
        validation_checkbox.setChecked(False)
        validation_checkbox.setStyleSheet(
            "color: #0F172A; font-weight: 600; font-size: 11px;"
        )

        form.addRow("Routing Type:", route_type_combo)
        form.addRow("Department:", dept_widget)
        form.addRow("Employee:", employee_widget)
        form.addRow("TSO:", tso_widget)
        form.addRow("Instructions:", instructions_edit)
        form.addRow("", validation_checkbox)
        row_vbox.addLayout(form)

        row_item = {
            "frame": row_frame,
            "header_label": header_label,
            "route_type": route_type_combo,
            "dept_combo": dept_combo,
            "employee_combo": employee_combo,
            "dept_widget": dept_widget,
            "employee_widget": employee_widget,
            "tso_widget": tso_widget,
            "instructions": instructions_edit,
            "validation": validation_checkbox,
        }

        def refresh_target_widgets():
            route_type = route_type_combo.currentData()
            dept_widget.setVisible(route_type == self.ROUTE_DEPARTMENT)
            employee_widget.setVisible(route_type == self.ROUTE_EMPLOYEE)
            tso_widget.setVisible(route_type == self.ROUTE_TSO)
            validation_checkbox.setVisible(route_type == self.ROUTE_EMPLOYEE)
            if route_type != self.ROUTE_EMPLOYEE:
                validation_checkbox.setChecked(False)

        route_type_combo.currentIndexChanged.connect(refresh_target_widgets)

        if prefill:
            suggested_emp_id = self._suggested_employee_id()
            suggested_dept_id = self._suggested_department_id()
            if suggested_emp_id:
                route_type_combo.setCurrentIndex(1)
                self._populate_employee_combo(employee_combo, suggested_emp_id)
            elif suggested_dept_id:
                route_type_combo.setCurrentIndex(0)
                for i in range(dept_combo.count()):
                    if dept_combo.itemData(i) == suggested_dept_id:
                        dept_combo.setCurrentIndex(i)
                        break

        refresh_target_widgets()

        def remove_row():
            if len(self.row_items) <= 1:
                QMessageBox.information(
                    self,
                    "Notice",
                    "At least one routing row is required."
                )
                return
            self.rows_layout.removeWidget(row_frame)
            row_frame.deleteLater()
            self.row_items.remove(row_item)
            self._renumber_rows()

        remove_btn.clicked.connect(remove_row)

        self.rows_layout.insertWidget(
            self.rows_layout.count() - 1,
            row_frame,
        )
        self.row_items.append(row_item)

    def _renumber_rows(self):
        for index, row in enumerate(self.row_items, start=1):
            row["header_label"].setText(f"Routing #{index}")

    def _on_confirm(self):
        routes = self.get_routes()
        if not routes:
            QMessageBox.warning(
                self,
                "Routing Required",
                "Please configure at least one valid routing target."
            )
            return

        tso_count = sum(
            1 for row in routes if row["branch_type"] == self.ROUTE_TSO
        )
        if tso_count > 1:
            QMessageBox.warning(
                self,
                "Invalid TSO Routing",
                "Only one TSO route can be added for a document."
            )
            return

        employee_ids = [
            row["target_user_id"]
            for row in routes
            if row["branch_type"] == self.ROUTE_EMPLOYEE
        ]
        if len(employee_ids) != len(set(employee_ids)):
            QMessageBox.warning(
                self,
                "Duplicate Employee Route",
                "The same employee cannot be added more than once in a single routing submission.",
            )
            return

        self._is_confirmed = True
        self.accept()

    def get_routes(self) -> List[Dict[str, Any]]:
        routes = []

        for row in self.row_items:
            branch_type = row["route_type"].currentData()
            instructions = row["instructions"].toPlainText().strip() or None

            if branch_type == self.ROUTE_DEPARTMENT:
                department_id = row["dept_combo"].currentData()
                if department_id is None:
                    continue
                routes.append({
                    "branch_type": self.ROUTE_DEPARTMENT,
                    "department_id": department_id,
                    "target_user_id": None,
                    "requires_hod_validation": False,
                    "instructions": instructions,
                })

            elif branch_type == self.ROUTE_EMPLOYEE:
                employee_id = row["employee_combo"].currentData()
                if employee_id is None:
                    continue

                employee = next(
                    (e for e in self._all_employees if e.id == employee_id),
                    None,
                )
                if employee is None:
                    continue

                routes.append({
                    "branch_type": self.ROUTE_EMPLOYEE,
                    "department_id": getattr(employee, "department_id", None),
                    "target_user_id": employee_id,
                    "requires_hod_validation": row["validation"].isChecked(),
                    "instructions": instructions,
                })

            elif branch_type == self.ROUTE_TSO:
                routes.append({
                    "branch_type": self.ROUTE_TSO,
                    "department_id": None,
                    "target_user_id": None,
                    "requires_hod_validation": False,
                    "instructions": instructions,
                })

        return routes

    # Backward-compatible accessor for any remaining legacy callers.
    def get_assignments(self) -> List[Dict[str, Any]]:
        return self.get_routes()


# Backward-compatible name. New DS UI uses UniversalRoutingDialog directly.
MultiDeptAssignDialog = UniversalRoutingDialog
HODAssignMultipleEmployeesDialog = HODAssignTeamDialog
DSAssignTeamDialog = DSTeamAssignmentDialog


class CloseDocumentDialog(QDialog):
    """
    Modal confirmation dialog for DS to close a completed document.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False

        self.setWindowTitle(
            f"Close Document - {document.reference}"
        )
        self.setMinimumSize(380, 220)
        self.setMaximumSize(680, 520)
        self.setSizeGripEnabled(True)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Confirm Document Closure")
        title.setStyleSheet(
            "font-size: 15px; "
            "font-weight: 600; "
            "color: #E11D48;"
        )

        desc = QLabel(
            f"Are you sure you want to close document "
            f"{self.document.reference}?\n\n"
            "Once closed, the document lifecycle will be finalized. "
            "The document, its remarks, and progress records will remain "
            "permanently viewable in audit history."
        )
        desc.setStyleSheet("color: #334155; font-size: 12px;")
        desc.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(desc)

        form = QFormLayout()

        self.remarks_input = QTextEdit()
        self.remarks_input.setPlaceholderText(
            "Enter final closure notes or summary..."
        )
        self.remarks_input.setMaximumHeight(80)

        form.addRow(
            "Closure Remarks:",
            self.remarks_input,
        )

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        close_btn = QPushButton("Finalize & Close Document")
        close_btn.setStyleSheet(
            "background-color: #E11D48; "
            "color: white; "
            "font-weight: 600; "
            "padding: 6px 14px; "
            "border-radius: 5px;"
        )
        close_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_confirm(self):
        if self._is_confirmed:
            return

        self._is_confirmed = True
        self.accept()

    def get_remarks(self) -> str:
        return self.remarks_input.toPlainText().strip()

    def get_data(self) -> Dict[str, Any]:
        return {
            "remarks": self.get_remarks()
        }


class SendReminderDialog(QDialog):
    """
    Modal dialog for DS sending an official workflow action reminder
    to the resolved recipient.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False

        self.setWindowTitle(
            f"Send Reminder - {document.reference}"
        )
        self.setMinimumSize(380, 200)
        self.setMaximumSize(680, 480)
        self.setSizeGripEnabled(True)

        self.setup_ui()

    def setup_ui(self):
        from services.notification_service import notification_service

        self.recipient = notification_service.resolve_reminder_recipient(
            self.document
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Send Document Action Reminder")
        title.setStyleSheet(
            "font-size: 15px; "
            "font-weight: 600; "
            "color: #0F172A;"
        )

        subtitle = QLabel(
            f"Document: {self.document.title}\n"
            f"Deadline: {self.document.deadline or 'Not specified'}"
        )
        subtitle.setStyleSheet(
            "color: #64748B; "
            "font-size: 12px;"
        )
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        if self.recipient:
            rec_text = (
                f"{self.recipient['user_name']} "
                f"({self.recipient['role']} • "
                f"{self.recipient.get('department_name') or 'General'})"
            )

            self.recipient_lbl = QLabel(rec_text)
            self.recipient_lbl.setStyleSheet(
                "font-weight: 600; "
                "color: #0F172A; "
                "font-size: 13px;"
            )

            form.addRow(
                "Reminder Recipient:",
                self.recipient_lbl,
            )
        else:
            self.recipient_lbl = QLabel(
                "⚠️ No downstream recipient available "
                "(Unassigned / Closed)"
            )
            self.recipient_lbl.setStyleSheet(
                "font-weight: 600; "
                "color: #DC2626; "
                "font-size: 12px;"
            )

            form.addRow(
                "Reminder Recipient:",
                self.recipient_lbl,
            )

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText(
            "Enter reminder message..."
        )
        self.message_input.setText(
            f"Gentle reminder regarding pending execution "
            f"for document {self.document.reference} "
            f"({self.document.title})."
        )
        self.message_input.setMaximumHeight(80)

        form.addRow(
            "Message:",
            self.message_input,
        )

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        send_btn = QPushButton("Send Reminder")
        send_btn.setStyleSheet(
            "background-color: #0F172A; "
            "color: white; "
            "font-weight: 600; "
            "padding: 6px 16px; "
            "border-radius: 5px;"
        )

        if not self.recipient:
            send_btn.setEnabled(False)

        send_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(send_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_confirm(self):
        if self._is_confirmed:
            return

        self._is_confirmed = True
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        return {
            "recipient": self.recipient,
            "message": self.message_input.toPlainText().strip(),
        }