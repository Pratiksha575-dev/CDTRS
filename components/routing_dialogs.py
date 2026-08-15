from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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
        self.setFixedWidth(440)
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
        self.dept_combo.addItems([
            "Finance",
            "Procurement",
            "HR",
            "Maintenance",
            "IT"
        ])
        
        target_dept = self.document.target_department_name or self.document.suggested_department_name
        if target_dept:
            idx = self.dept_combo.findText(target_dept)
            if idx >= 0:
                self.dept_combo.setCurrentIndex(idx)

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
        dept_id_map = {"Finance": 1, "Procurement": 2, "HR": 3, "Maintenance": 4, "IT": 5}
        return {
            "department_name": dept_name,
            "department_id": dept_id_map.get(dept_name, 1),
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
        self.setFixedWidth(450)
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

        for emp in employees:
            label = f"{emp.full_name} ({emp.department_name or 'General'})"
            self.emp_combo.addItem(label, emp.id)
            self._emp_map[label] = emp.id
            if target_emp and emp.full_name.lower() in target_emp.lower():
                self.emp_combo.setCurrentText(label)

        if not employees:
            self.emp_combo.addItem("Rahul Sharma (Finance)", 5)
            self.emp_combo.addItem("Priya Verma (Procurement)", 8)

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
        emp_id = self.emp_combo.currentData() or 5
        emp_text = self.emp_combo.currentText().split(" (")[0]
        return {
            "employee_id": emp_id,
            "employee_name": emp_text,
            "remarks": None
        }


class HODAssignEmployeeDialog(QDialog):
    """
    Modal dialog for Department Head (HOD) delegating execution of a document to a departmental Employee.
    """

    def __init__(self, document: DocumentModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setModal(True)
        self._is_confirmed = False
        self.setWindowTitle(f"Assign Document - {document.reference}")
        self.setFixedWidth(460)
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
        dept_id = self.document.target_department_id
        employees = repo.get_users(role="Employee", department_id=dept_id)
        if not employees:
            employees = repo.get_users(role="Employee")

        for emp in employees:
            label = f"{emp.full_name} ({emp.department_name or 'General'})"
            self.emp_combo.addItem(label, emp.id)

        if not employees:
            self.emp_combo.addItem("Rahul Sharma (Finance)", 5)

        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText("Enter specific task instructions, deliverables, or target timeline...")
        self.instructions_input.setMaximumHeight(85)

        form.addRow("Assign To:", self.emp_combo)
        form.addRow("Task Instructions:", self.instructions_input)
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
        emp_id = self.emp_combo.currentData() or 5
        emp_text = self.emp_combo.currentText().split(" (")[0]
        return {
            "assigned_to_id": emp_id,
            "employee_name": emp_text,
            "instructions": self.instructions_input.toPlainText().strip()
        }


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
        self.setFixedWidth(450)
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
        self.setFixedWidth(460)
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
