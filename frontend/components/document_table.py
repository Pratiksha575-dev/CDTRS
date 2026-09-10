from typing import List, Optional, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from models.document import DocumentModel


class DocumentTable(QTableWidget):
    """
    Standardized, robust Document Table for CDTRS.
    Supports both DocumentModel instances and legacy dictionaries with priority badges and stage indicators.
    """

    document_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            "Reference",
            "Subject / Title",
            "Priority",
            "Department",
            "Assigned Staff / Team",
            "Deadline",
            "Status",
            "Stage"
        ])

        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.itemSelectionChanged.connect(self.on_selection_changed)

    def load_documents(self, documents: List[Union[DocumentModel, dict]]):
        self.documents = documents
        self.setRowCount(len(documents))

        for row, doc in enumerate(documents):
            if isinstance(doc, DocumentModel):
                ref = doc.reference or "-"
                title = doc.title or "Untitled"
                prio = doc.priority or "Medium"
                dept = doc.department or doc.target_department_name or "-"
                emp = self._assignment_display(doc)
                deadline = doc.deadline or "-"
                status = doc.status or "-"
                stage = doc.current_stage or "-"
            else:
                ref = doc.get("reference") or f"CDTRS-2026-{doc.get('id', 0):03d}"
                title = doc.get("title") or doc.get("subject") or "Untitled"
                prio = doc.get("priority") or "Medium"
                dept = doc.get("department") or "-"
                emp = self._assignment_display(doc)
                deadline = doc.get("deadline") or "-"
                status = doc.get("status") or "-"
                stage = doc.get("current_stage") or "-"

            self.setItem(row, 0, QTableWidgetItem(str(ref)))
            self.setItem(row, 1, QTableWidgetItem(str(title)))

            prio_item = QTableWidgetItem(str(prio))
            prio_str = str(prio).lower()
            if prio_str in ("high", "red"):
                prio_item.setForeground(Qt.darkRed)
            elif prio_str in ("medium", "orange", "yellow"):
                prio_item.setForeground(Qt.darkYellow)
            else:
                prio_item.setForeground(Qt.darkGreen)
            self.setItem(row, 2, prio_item)

            self.setItem(row, 3, QTableWidgetItem(str(dept)))
            self.setItem(row, 4, QTableWidgetItem(str(emp)))
            self.setItem(row, 5, QTableWidgetItem(str(deadline)))
            self.setItem(row, 6, QTableWidgetItem(str(status)))
            self.setItem(row, 7, QTableWidgetItem(str(stage)))


    @staticmethod
    def _assignment_display(doc) -> str:
        """Return a compact single/team assignment label for table display."""
        assignments = getattr(doc, "work_assignments", None)
        if assignments is None and isinstance(doc, dict):
            assignments = doc.get("work_assignments") or doc.get("assignments")

        labels = []
        for assignment in assignments or []:
            if isinstance(assignment, dict):
                if not assignment.get("is_active", True):
                    continue
                team_name = assignment.get("team_name")
                members = assignment.get("members") or []
                member_names = []
                for member in members:
                    if isinstance(member, dict):
                        name = member.get("user_name") or member.get("full_name") or member.get("name")
                    else:
                        name = getattr(member, "user_name", None) or getattr(member, "full_name", None) or getattr(member, "name", None)
                    if name:
                        member_names.append(str(name))
                if team_name:
                    labels.append(f"{team_name} ({len(member_names)} members)" if member_names else str(team_name))
                elif member_names:
                    labels.append(", ".join(member_names))
                elif assignment.get("assigned_to_user_name") or assignment.get("assigned_to_name"):
                    labels.append(str(assignment.get("assigned_to_user_name") or assignment.get("assigned_to_name")))
            else:
                if not getattr(assignment, "is_active", True):
                    continue
                display = getattr(assignment, "display_name", None)
                if display:
                    labels.append(str(display))
                    continue
                team_name = getattr(assignment, "team_name", None)
                member_names = getattr(assignment, "active_member_names", None) or getattr(assignment, "member_names", None) or []
                if team_name:
                    labels.append(f"{team_name} ({len(member_names)} members)" if member_names else str(team_name))
                elif member_names:
                    labels.append(", ".join(map(str, member_names)))
                else:
                    name = getattr(assignment, "assigned_to_user_name", None) or getattr(assignment, "assigned_to_name", None)
                    if name:
                        labels.append(str(name))

        if labels:
            return " | ".join(labels)

        return getattr(doc, "assigned_employee_name", None) or (doc.get("assigned_employee_name") if isinstance(doc, dict) else None) or "-"

    def on_selection_changed(self):
        row = self.currentRow()
        if 0 <= row < len(self.documents):
            self.document_selected.emit(self.documents[row])

    def get_selected_document(self) -> Optional[Union[DocumentModel, dict]]:
        row = self.currentRow()
        if 0 <= row < len(self.documents):
            return self.documents[row]
        return None
