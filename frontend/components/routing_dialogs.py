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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from repositories.provider import get_repository


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
        self.setMinimumWidth(400)
        self.setMaximumWidth(580)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Route Document to Department Head (HOD)")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A;")
        
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
        target_dept = self.document.target_department_name or self.document.suggested_department_name
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
            self.dept_combo.addItem("⚠ Could not load departments — check connection", None)

        if target_dept and departments:
            alias_map = {
                "human resources": "hr",
                "it": "technical",
                "information technology": "technical",
                "systems": "technical",
                "operations": "administration",
                "legal": "administration",
            }
            norm_target = alias_map.get(target_dept.lower(), target_dept).lower()
            for i in range(self.dept_combo.count()):
                item_text = self.dept_combo.itemText(i).lower()
                if norm_target == item_text or norm_target in item_text or item_text in norm_target:
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
        confirm_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
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
        dept_id = self.dept_combo.currentData()  # Real backend ID stored as item data
        if dept_id is None:
            dept_id = self._dept_map.get(dept_name)
        return {
            "department_name": dept_name,
            "department_id": dept_id,
            "remarks": None
        }


class RouteToEmployeeDialog(QDialog):
    """
    Modal dialog for DS routing a document directly to an explicitly identified Employee.
    Remarks are not requested as routing is a direct structural action.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Route to Employee - {document.reference}")
        self.setMinimumWidth(420)
        self.setMaximumWidth(600)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Direct Route to Employee")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A;")
        
        subtitle = QLabel(f"Document: {self.document.title}\n(Direct routing when staff is explicitly identified)")
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
        target_emp = self.document.assigned_employee_name or self.document.suggested_employee_name
        if not target_emp and self.document.id:
            try:
                s_data = repo.get_routing_suggestion(self.document.id) or {}
                target_emp = s_data.get("suggested_employee_name")
            except Exception:
                pass

        if employees:
            for emp in employees:
                label = f"{emp.full_name} ({emp.department_name or 'General'})"
                self.emp_combo.addItem(label, emp.id)
                self._emp_map[label] = emp.id

            if target_emp:
                for i in range(self.emp_combo.count()):
                    item_text = self.emp_combo.itemText(i).lower()
                    if target_emp.lower() in item_text:
                        self.emp_combo.setCurrentIndex(i)
                        break
        else:
            # Backend unreachable — show placeholder; do not insert hardcoded employees
            self.emp_combo.addItem("⚠ Could not load employees — check connection", None)

        form.addRow("Select Staff:", self.emp_combo)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm Route to Staff")
        confirm_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
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
        emp_id = self.emp_combo.currentData()  # None if no real employee loaded
        emp_text = self.emp_combo.currentText().split(" (")[0]
        return {
            "employee_id": emp_id,
            "employee_name": emp_text,
            "remarks": None
        }


class HODAssignEmployeeDialog(QDialog):
    """
    Modal dialog for Department Head (HOD) delegating execution of a document to a departmental Employee.
    Includes option to require HOD validation before progress reports reach DS.
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
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A;")
        
        dept_name = self.document.target_department_name or "Department"
        subtitle = QLabel(f"Document: {self.document.title}\nDepartment: {dept_name}")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.emp_combo = QComboBox()
        repo = get_repository()
        dept_name = self.document.target_department_name or auth_service.get_active_department()
        dept_id = self.document.target_department_id

        if not dept_id and dept_name:
            all_depts = repo.get_departments()
            for d in all_depts:
                if d.name.upper() == dept_name.upper():
                    dept_id = d.id
                    break

        employees = repo.get_users(role="Employee", department_id=dept_id)
        if not employees and dept_name:
            all_emps = repo.get_users(role="Employee")
            employees = [u for u in all_emps if u.department_name and u.department_name.upper() == dept_name.upper()]
        if not employees:
            employees = repo.get_users(role="Employee")

        if employees:
            for emp in employees:
                code_str = f" [{emp.employee_code}]" if getattr(emp, "employee_code", None) else ""
                label = f"{emp.full_name}{code_str} ({emp.department_name or 'General'})"
                self.emp_combo.addItem(label, emp.id)
        else:
            self.emp_combo.addItem("⚠ No employees found for this department", None)


        form.addRow("Assign To:", self.emp_combo)

        # Show existing HOD remark that will be forwarded
        if getattr(self.document, "hod_remark", None):
            rem_note = QLabel(f"<b>Forwarded HOD Remark:</b> <i>{self.document.hod_remark}</i>")
            rem_note.setStyleSheet("color: #0284C7; font-size: 11px; padding: 4px 0px;")
            rem_note.setWordWrap(True)
            form.addRow("", rem_note)

        self.val_checkbox = QCheckBox("Require HOD validation before progress updates reach DS")
        self.val_checkbox.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 12px; margin-top: 4px;")
        self.val_checkbox.setChecked(False)

        form.addRow("", self.val_checkbox)
        layout.addLayout(form)


        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        assign_btn = QPushButton("Confirm Work Assignment")
        assign_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
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
            "instructions": getattr(self.document, "hod_remark", "") or None,
            "requires_hod_validation": self.val_checkbox.isChecked()
        }



class MultiDeptAssignDialog(QDialog):
    """
    Modal dialog for DS configuring Multi-Department and Multi-Employee routing for a document.
    Allows dynamically adding multiple departmental assignments.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Multi-Department Routing - {document.reference}")
        self.setMinimumWidth(560)
        self.setMaximumWidth(780)
        self.setMinimumHeight(420)
        self.setSizeGripEnabled(True)
        self.row_items: List[Dict[str, Any]] = []
        self._departments = []
        self._all_employees = []
        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(22, 20, 22, 20)
        root_layout.setSpacing(12)

        title = QLabel("Multi-Department / Multi-Employee Routing")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")

        subtitle = QLabel(f"Document: {self.document.title}\nAssign this document to multiple departments and staff simultaneously.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        # Load departments and employees once
        repo = get_repository()
        self._departments = [d for d in repo.get_departments() if d.name.lower() != "administration"]
        self._all_employees = repo.get_users(role="Employee")

        # Scroll area for assignment rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #E2E8F0; border-radius: 6px; background: #FFFFFF; }")

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(10, 10, 10, 10)
        self.rows_layout.setSpacing(10)
        self.rows_layout.addStretch()

        self.scroll_area.setWidget(self.rows_container)
        root_layout.addWidget(self.scroll_area, 1)

        # Add initial row
        self._add_row()

        # Add row button
        add_btn_row = QHBoxLayout()
        self.add_row_btn = QPushButton("➕ Add Another Department / Assignment")
        self.add_row_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 6px 14px; border-radius: 4px;")
        self.add_row_btn.clicked.connect(self._add_row)
        add_btn_row.addWidget(self.add_row_btn)
        add_btn_row.addStretch()
        root_layout.addLayout(add_btn_row)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirm Multi-Routing")
        confirm_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        confirm_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        root_layout.addLayout(btn_layout)

        self.setLayout(root_layout)

    def _add_row(self):
        row_frame = QFrame()
        row_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px;")
        row_vbox = QVBoxLayout(row_frame)
        row_vbox.setContentsMargins(8, 8, 8, 8)
        row_vbox.setSpacing(6)

        hdr_row = QHBoxLayout()
        row_idx = len(self.row_items) + 1
        hdr_lbl = QLabel(f"Assignment #{row_idx}")
        hdr_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 12px;")
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()

        remove_btn = QPushButton("✕ Remove")
        remove_btn.setStyleSheet("background: transparent; color: #DC2626; font-size: 11px; font-weight: 600; border: none;")
        hdr_row.addWidget(remove_btn)
        row_vbox.addLayout(hdr_row)

        form = QFormLayout()
        form.setSpacing(6)

        dept_combo = QComboBox()
        dept_combo.addItem("-- Select Department --", None)
        for d in self._departments:
            dept_combo.addItem(d.name, d.id)

        emp_combo = QComboBox()
        emp_combo.addItem("-- Assign Directly to Staff (Optional) --", None)

        def _on_dept_change():
            sel_dept_id = dept_combo.currentData()
            emp_combo.clear()
            emp_combo.addItem("-- Assign Directly to Staff (Optional) --", None)
            for emp in self._all_employees:
                if sel_dept_id is None or emp.department_id == sel_dept_id:
                    emp_combo.addItem(f"{emp.full_name} ({emp.department_name or 'General'})", emp.id)

        dept_combo.currentIndexChanged.connect(_on_dept_change)
        _on_dept_change()

        instr_edit = QTextEdit()
        instr_edit.setPlaceholderText("Instructions for this department / employee...")
        instr_edit.setMaximumHeight(50)

        val_cb = QCheckBox("Require HOD validation before progress reaches DS")
        val_cb.setChecked(False)

        form.addRow("Department:", dept_combo)
        form.addRow("Specific Staff:", emp_combo)
        form.addRow("Instructions:", instr_edit)
        form.addRow("", val_cb)
        row_vbox.addLayout(form)

        row_item = {
            "frame": row_frame,
            "dept_combo": dept_combo,
            "emp_combo": emp_combo,
            "instr_edit": instr_edit,
            "val_cb": val_cb
        }

        def _remove():
            if len(self.row_items) <= 1:
                QMessageBox.information(self, "Notice", "At least one assignment row is required.")
                return
            self.rows_layout.removeWidget(row_frame)
            row_frame.deleteLater()
            self.row_items.remove(row_item)

        remove_btn.clicked.connect(_remove)

        # Insert before stretch
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row_frame)
        self.row_items.append(row_item)

    def _on_confirm(self):
        valid_items = self.get_assignments()
        if not valid_items:
            QMessageBox.warning(self, "Validation", "Please select at least one department or staff member.")
            return
        self._is_confirmed = True
        self.accept()

    def get_assignments(self) -> List[Dict[str, Any]]:
        results = []
        for r in self.row_items:
            dept_id = r["dept_combo"].currentData()
            emp_id = r["emp_combo"].currentData()
            instructions = r["instr_edit"].toPlainText().strip()
            requires_val = r["val_cb"].isChecked()

            if dept_id is not None or emp_id is not None:
                results.append({
                    "department_id": dept_id,
                    "assigned_employee_id": emp_id,
                    "instructions": instructions or None,
                    "requires_hod_validation": requires_val
                })
        return results


class CloseDocumentDialog(QDialog):
    """
    Modal confirmation dialog for DS to close a completed document.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Close Document - {document.reference}")
        self.setMinimumWidth(420)
        self.setMaximumWidth(580)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Confirm Document Closure")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #E11D48;")
        desc = QLabel(
            f"Are you sure you want to close document {self.document.reference}?\n\n"
            "Once closed, the document lifecycle will be finalized. The document, its remarks, "
            "and progress records will remain permanently viewable in audit history."
        )
        desc.setStyleSheet("color: #334155; font-size: 12px;")
        desc.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(desc)

        form = QFormLayout()
        self.remarks_input = QTextEdit()
        self.remarks_input.setPlaceholderText("Enter final closure notes or summary...")
        self.remarks_input.setMaximumHeight(80)
        form.addRow("Closure Remarks:", self.remarks_input)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        close_btn = QPushButton("Finalize & Close Document")
        close_btn.setStyleSheet("background-color: #E11D48; color: white; font-weight: 600; padding: 6px 14px; border-radius: 5px;")
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
    Modal dialog for DS sending an official workflow action reminder to the resolved recipient.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Send Reminder - {document.reference}")
        self.setMinimumWidth(420)
        self.setMaximumWidth(600)
        self.setSizeGripEnabled(True)
        self.setup_ui()

    def setup_ui(self):
        from services.notification_service import notification_service
        self.recipient = notification_service.resolve_reminder_recipient(self.document)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Send Document Action Reminder")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A;")
        
        subtitle = QLabel(f"Document: {self.document.title}\nDeadline: {self.document.deadline or 'Not specified'}")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        if self.recipient:
            rec_text = f"{self.recipient['user_name']} ({self.recipient['role']} • {self.recipient.get('department_name') or 'General'})"
            self.recipient_lbl = QLabel(rec_text)
            self.recipient_lbl.setStyleSheet("font-weight: 600; color: #0F172A; font-size: 13px;")
            form.addRow("Reminder Recipient:", self.recipient_lbl)
        else:
            self.recipient_lbl = QLabel("⚠️ No downstream recipient available (Unassigned / Closed)")
            self.recipient_lbl.setStyleSheet("font-weight: 600; color: #DC2626; font-size: 12px;")
            form.addRow("Reminder Recipient:", self.recipient_lbl)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Enter reminder message...")
        self.message_input.setText(f"Gentle reminder regarding pending execution for document {self.document.reference} ({self.document.title}).")
        self.message_input.setMaximumHeight(80)

        form.addRow("Message:", self.message_input)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        send_btn = QPushButton("Send Reminder")
        send_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 6px 16px; border-radius: 5px;")
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
            "message": self.message_input.toPlainText().strip()
        }
