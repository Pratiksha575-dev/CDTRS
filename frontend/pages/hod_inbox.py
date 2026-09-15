from typing import Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from models.enums import DocumentStatusEnum
from services.document_service import document_service


class HODInboxPage(QWidget):
    """HOD inbox using canonical routing branches and WorkAssignments.

    A document remains one table row, while multiple routing branches and
    multiple/team assignments are summarized inside the row. No legacy
    document-level owner/stage fields are used.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self.setup_ui()
        self.load_inbox()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.load_inbox)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_inbox()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(14)

        title = QLabel("Department Documents & Tasks")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Manage departmental documents routed by Director Secretary, "
            "delegate work to staff, and track each routing workstream."
        )
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "🔍 Search by title, reference, department, staff, priority, status..."
        )
        self.search_input.setStyleSheet(
            "padding: 7px 12px; border: 1px solid #CBD5E1; "
            "border-radius: 5px; font-size: 12px;"
        )
        self.search_input.textChanged.connect(self.apply_filter)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Active Documents",
            "Awaiting Assignment",
            "Assigned / In Progress",
            "Progress Updates Received",
            "Closed Documents",
        ])
        self.filter_combo.setStyleSheet(
            "padding: 6px 10px; border: 1px solid #CBD5E1; "
            "border-radius: 5px; font-size: 12px;"
        )
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            "background-color: #F1F5F9; border: 1px solid #CBD5E1; "
            "padding: 6px 14px; border-radius: 4px; font-weight: 600;"
        )
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.filter_combo, 1)
        filter_layout.addWidget(clear_btn)
        main_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference No",
            "Document",
            "Priority",
            "Routing Branch",
            "Work Assignment",
            "Deadline",
            "Status",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(48)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.open_btn = QPushButton("Open / Manage Work")
        self.open_btn.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: 600; "
            "padding: 8px 22px; border-radius: 5px;"
        )
        self.open_btn.clicked.connect(self.open_document)
        action_layout.addWidget(self.open_btn)
        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_inbox(self):
        """Load documents for the active HOD context."""
        try:
            self.documents = list(document_service.get_documents() or [])
        except Exception as exc:
            print(f"[HOD INBOX] Failed to load active HOD context: {exc}")
            self.documents = []
        self.apply_filter()

    def _clear_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)

    # =========================================================
    # CANONICAL ROUTING DISPLAY HELPERS
    # =========================================================

    @staticmethod
    def _value(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
            if value is not None and value != "":
                return value
        return default

    @staticmethod
    def _call(value: Any) -> Any:
        if callable(value):
            try:
                return value()
            except Exception:
                return None
        return value

    def _active_branches(self, doc: DocumentModel) -> List[Any]:
        if isinstance(doc, dict):
            branches = (
                doc.get("department_routings")
                or doc.get("routing_branches")
                or doc.get("branches")
                or []
            )
        else:
            branches = (
                getattr(doc, "department_routings", None)
                or getattr(doc, "routing_branches", None)
                or getattr(doc, "branches", None)
                or []
            )
        if isinstance(branches, dict):
            branches = [branches]
        return [b for b in branches if self._value(b, "is_active", default=True) is not False]

    def _document_assignments(self, doc: DocumentModel) -> List[Any]:
        assignments = doc.get("work_assignments") if isinstance(doc, dict) else getattr(doc, "work_assignments", None)
        if isinstance(assignments, dict):
            assignments = [assignments]
        return [a for a in (assignments or []) if self._value(a, "is_active", default=True) is not False]

    def _branch_assignments(self, doc: DocumentModel, branch: Any) -> List[Any]:
        branch_id = self._value(branch, "id", "routing_id")
        assignments = self._value(branch, "assignments", default=None)
        if assignments is None:
            assignments = self._document_assignments(doc)
        if isinstance(assignments, dict):
            assignments = [assignments]
        result = []
        for assignment in assignments or []:
            if self._value(assignment, "is_active", default=True) is False:
                continue
            assignment_branch = self._value(assignment, "routing_id", "branch_id")
            if branch_id is not None and assignment_branch is not None and str(branch_id) != str(assignment_branch):
                continue
            result.append(assignment)
        return result

    def _branch_label(self, branch: Any) -> str:
        raw_type = str(self._value(branch, "branch_type", "route_type", default="ROUTING"))
        route_type = {
            "DEPARTMENT_HOD": "Department / HOD",
            "DIRECT_EMPLOYEE": "Direct Employee",
            "TSO": "TSO",
        }.get(raw_type, raw_type.replace("_", " ").title())

        dept = self._value(branch, "department_name", "department", default=None)
        if isinstance(dept, dict):
            dept = dept.get("name") or dept.get("department_name")
        if dept:
            return f"{dept} → {route_type}"

        target = self._value(branch, "target_user_name", "employee_name", default=None)
        if target and route_type == "Direct Employee":
            return f"{route_type} → {target}"
        return route_type

    def _assignment_label(self, assignment: Any) -> str:
        display = self._call(self._value(
            assignment,
            "display_assignee",
            "team_members_display",
            "assigned_team_names",
            "workstream_label",
            default=None,
        ))
        if display:
            return str(display)

        members = self._value(assignment, "members", default=None)
        if isinstance(members, dict):
            members = [members]
        names = []
        for member in members or []:
            name = self._value(member, "user_name", "member_name", "name", "full_name", default=None)
            if name:
                names.append(str(name))
        names = list(dict.fromkeys(names))
        if names:
            return f"👥 Team ({len(names)}): " + ", ".join(names) if len(names) > 1 else names[0]

        name = self._value(assignment, "assigned_to_name", "employee_name", default=None)
        return str(name) if name else "— Unassigned —"

    def _branch_status(self, doc: DocumentModel, branch: Any) -> str:
        assignments = self._branch_assignments(doc, branch)
        if not assignments:
            return "Awaiting Assignment"
        statuses = []
        for assignment in assignments:
            status = self._value(assignment, "status", "assignment_status", default=None)
            if status:
                statuses.append(str(status))
            else:
                statuses.append("Completed" if self._value(assignment, "completed_at") else "In Progress")
        statuses = list(dict.fromkeys(statuses))
        return statuses[0] if len(statuses) == 1 else "Mixed Progress"

    def _routing_summary(self, doc: DocumentModel) -> str:
        branches = self._active_branches(doc)
        if not branches:
            return "No active routing branch"
        labels = list(dict.fromkeys(self._branch_label(b) for b in branches))
        if len(labels) <= 3:
            return "\n".join(labels)
        return "\n".join(labels[:3]) + f"\n+ {len(labels) - 3} more branch(es)"

    def _assignment_summary(self, doc: DocumentModel) -> str:
        branches = self._active_branches(doc)
        lines = []
        if branches:
            for branch in branches:
                branch_label = self._branch_label(branch)
                assignments = self._branch_assignments(doc, branch)
                if not assignments:
                    lines.append(f"{branch_label}: — Unassigned —")
                else:
                    for assignment in assignments:
                        lines.append(f"{branch_label}: {self._assignment_label(assignment)}")
        else:
            for assignment in self._document_assignments(doc):
                lines.append(self._assignment_label(assignment))

        if not lines:
            return "— No assignment —"
        if len(lines) <= 4:
            return "\n".join(lines)
        return "\n".join(lines[:4]) + f"\n+ {len(lines) - 4} more assignment(s)"

    def _status_summary(self, doc: DocumentModel) -> str:
        branches = self._active_branches(doc)
        if not branches:
            return str(doc.status or "—")
        statuses = [self._branch_status(doc, b) for b in branches]
        if all(s == "Completed" for s in statuses):
            return "Completed"
        if any(s == "In Progress" for s in statuses):
            return "In Progress"
        if any(s == "Mixed Progress" for s in statuses):
            return "Mixed Progress"
        if any(s == "Awaiting Assignment" for s in statuses):
            return "Awaiting Assignment"
        return str(doc.status or "Active")

    def _has_unassigned_branch(self, doc: DocumentModel) -> bool:
        return any(not self._branch_assignments(doc, b) for b in self._active_branches(doc))

    def _has_assignment(self, doc: DocumentModel) -> bool:
        return bool(self._document_assignments(doc)) or any(
            self._branch_assignments(doc, b) for b in self._active_branches(doc)
        )

    def _has_progress(self, doc: DocumentModel) -> bool:
        if doc.status == DocumentStatusEnum.PROGRESS_UPDATED.value:
            return True
        for assignment in self._document_assignments(doc):
            status = str(self._value(assignment, "status", "assignment_status", default="")).lower()
            if "progress" in status or "updated" in status:
                return True
        return False

    # =========================================================
    # FILTER + TABLE
    # =========================================================

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        query = self.search_input.text().strip().lower()
        filtered = []

        for doc in self.documents:
            is_closed = str(doc.status or "").lower() == "closed"
            is_unassigned = self._has_unassigned_branch(doc)
            is_assigned = self._has_assignment(doc)
            is_progress = self._has_progress(doc)

            if filter_text == "All Active Documents" and is_closed:
                continue
            if filter_text == "Awaiting Assignment" and not is_unassigned:
                continue
            if filter_text == "Assigned / In Progress" and not (is_assigned and not is_progress and not is_closed):
                continue
            if filter_text == "Progress Updates Received" and not is_progress:
                continue
            if filter_text == "Closed Documents" and not is_closed:
                continue

            if query:
                values = (
                    str(doc.reference or ""),
                    str(doc.title or ""),
                    str(doc.priority or ""),
                    self._routing_summary(doc),
                    self._assignment_summary(doc),
                    self._status_summary(doc),
                )
                if not any(query in value.lower() for value in values):
                    continue
            filtered.append(doc)

        self.table.setRowCount(len(filtered))
        self._displayed_docs = filtered

        for row, doc in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.priority or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(self._routing_summary(doc)))

            assignment_text = self._assignment_summary(doc)
            assignment_item = QTableWidgetItem(assignment_text)
            if "Unassigned" in assignment_text:
                assignment_item.setForeground(Qt.red)
            self.table.setItem(row, 4, assignment_item)

            self.table.setItem(row, 5, QTableWidgetItem(str(doc.deadline or "-")))
            self.table.setItem(row, 6, QTableWidgetItem(self._status_summary(doc)))

        self.table.resizeRowsToContents()

    def open_document(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(
                self,
                "Selection Required",
                "Please select a document from the queue to open.",
            )
            return
        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "HOD")
