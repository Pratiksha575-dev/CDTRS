from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from models.document import DocumentModel


class DocumentTable(QTableWidget):
    """Reusable document table backed by the canonical document model.

    Operational department/staff information comes from WorkAssignment and
    routing branches. DocumentModel suggestion fields are used only when no
    confirmed assignment exists.
    """

    document_selected = Signal(object)

    HEADERS = [
        "Reference",
        "Subject / Title",
        "Priority",
        "Department",
        "Assigned Staff",
        "Deadline",
        "Status",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.documents: List[DocumentModel] = []
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setWordWrap(True)
        self.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustIgnored)
        self.setMinimumHeight(180)
        self.itemSelectionChanged.connect(self._selection_changed)

    @staticmethod
    def _value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @classmethod
    def _active_assignments(cls, document: Any) -> list:
        assignments = cls._value(document, "work_assignments", None) or []
        return [
            a for a in assignments
            if cls._value(a, "is_active", True) is not False
        ]

    @classmethod
    def _department_text(cls, document: Any) -> str:
        names = []
        for assignment in cls._active_assignments(document):
            routing = cls._value(assignment, "routing", None)
            department = cls._value(assignment, "department", None)
            name = cls._value(assignment, "department_name", None)
            if not name and department:
                name = cls._value(department, "name", None) or str(department)
            if not name and routing:
                name = cls._value(routing, "department_name", None)
                if not name:
                    routed_department = cls._value(routing, "department", None)
                    if routed_department:
                        name = cls._value(routed_department, "name", None) or str(routed_department)
            if name and str(name) not in names:
                names.append(str(name))
        if names:
            return " | ".join(names)

        # A routing suggestion is advisory intelligence, not confirmed routing.
        # Never display it as the document's assigned department.
        branches = cls._value(document, "department_routings", None) or cls._value(document, "branches", None) or []
        for branch in branches:
            if cls._value(branch, "is_active", True) is False:
                continue
            if cls._value(branch, "branch_type", None) != "DEPARTMENT_HOD":
                continue
            name = cls._value(branch, "department_name", None)
            department = cls._value(branch, "department", None)
            if not name and department:
                name = cls._value(department, "name", None) or str(department)
            if name and str(name) not in names:
                names.append(str(name))
        return " | ".join(names) if names else "Not Specified"

    @classmethod
    def _staff_text(cls, document: Any) -> str:
        displays = []
        for assignment in cls._active_assignments(document):
            display = cls._value(assignment, "display_assignee", None)
            if callable(display):
                try:
                    display = display()
                except Exception:
                    display = None
            if display:
                displays.append(str(display))
                continue

            team = cls._value(assignment, "team_name", None)
            members = cls._value(assignment, "members", None) or []
            names = []
            for member in members:
                name = (
                    cls._value(member, "user_name", None)
                    or cls._value(member, "employee_name", None)
                    or cls._value(member, "name", None)
                )
                if name:
                    names.append(str(name))
            if not names:
                name = (
                    cls._value(assignment, "assigned_to_user_name", None)
                    or cls._value(assignment, "assigned_to_name", None)
                )
                if name:
                    names.append(str(name))
            if team and names:
                displays.append(f"{team} ({', '.join(names)})")
            elif team:
                displays.append(str(team))
            elif names:
                displays.append(", ".join(names))

        if displays:
            return " | ".join(dict.fromkeys(displays))

        # Suggestions are never operational assignments.
        return "Not Assigned"

    def load_documents(self, documents: Optional[List[DocumentModel]] = None):
        self.documents = list(documents or [])
        self.setRowCount(len(self.documents))

        for row, document in enumerate(self.documents):
            values = [
                self._value(document, "reference", "-"),
                self._value(document, "subject", None) or self._value(document, "title", "-"),
                self._value(document, "priority", "Medium"),
                self._department_text(document),
                self._staff_text(document),
                self._value(document, "deadline", None) or "—",
                self._value(document, "status", "Received"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, document)
                self.setItem(row, column, item)

        self.resizeRowsToContents()
        self.verticalHeader().setDefaultSectionSize(34)

    def _selection_changed(self):
        document = self.get_selected_document()
        if document is not None:
            self.document_selected.emit(document)

    def get_selected_document(self) -> Optional[DocumentModel]:
        row = self.currentRow()
        if row < 0 or row >= len(self.documents):
            return None
        return self.documents[row]

    def clear_documents(self):
        self.documents = []
        self.setRowCount(0)

    def selectedItems(self):
        return super().selectedItems()
