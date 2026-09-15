from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QFormLayout,
    QSizePolicy,
)
from models.document import DocumentModel


class DocumentInfo(QFrame):
    """
    Compact Document Information component for DocumentViewer.
    Renders structured metadata cleanly without redundancy.
    """

    def __init__(self, document=None):
        super().__init__()
        self.document = document or DocumentModel()
        self.setObjectName("contentCard")
        self.fields = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Document Information")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setSpacing(6)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Metadata fields
        self.add_field("Reference", self._get_val("reference"))
        self.add_field("Title / Subject", self._get_val("subject", self._get_val("title", "—")))
        self.add_field("Source", self._get_val("source", "External"))
        self.add_field("Received Date", self._get_val("received", self._get_val("date", "N/A")))
        self.add_field("Ingestion Mode", self._get_val("mode", "—"))
        self.add_field("Format", self._get_val("format", self._get_val("file_type", "—")))
        self.add_field("Priority", self._get_val("priority", "Medium"))
        self.add_field("Target Deadline", self._get_val("deadline", "—"))

        dept_val = self._department_display()
        self.add_field("Department", dept_val)

        self.add_field("Assigned Staff / Team", self._assignment_display())
        self.add_field("Status", self._get_val("status", "Received"))

        layout.addLayout(self.form)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setLayout(layout)

    def _get_val(self, key, default="-"):
        if isinstance(self.document, DocumentModel):
            val = getattr(self.document, key, None)
            if val is not None and str(val).strip():
                return str(val)
            return default
        elif isinstance(self.document, dict):
            val = self.document.get(key)
            if val is not None and str(val).strip():
                return str(val)
            return default
        return default

    def _display_value(self, value, default):
        if value is None:
            return default
        text = str(value).strip()
        return text if text and text != "-" else default

    def _assignment_display(self):
        """
        Display active team/multi-member assignments when available,
        while preserving the legacy single-assignee fallback.
        """
        assignments = None

        if isinstance(self.document, DocumentModel):
            assignments = getattr(self.document, "work_assignments", None)
            if assignments is None:
                assignments = getattr(self.document, "assignments", None)
        elif isinstance(self.document, dict):
            assignments = self.document.get("work_assignments")
            if assignments is None:
                assignments = self.document.get("assignments")

        if assignments:
            active = []
            for assignment in assignments:
                if isinstance(assignment, dict):
                    is_active = assignment.get("is_active", True)
                    if is_active is False:
                        continue
                    team_name = assignment.get("team_name")
                    members = assignment.get("members") or []
                    if members:
                        names = []
                        for member in members:
                            if isinstance(member, dict):
                                name = (
                                    member.get("user_name")
                                    or member.get("employee_name")
                                    or member.get("name")
                                )
                            else:
                                name = getattr(member, "user_name", None) or getattr(
                                    member, "employee_name", None
                                ) or getattr(member, "name", None)
                            if name:
                                names.append(str(name))
                        member_text = ", ".join(names)
                    else:
                        member_text = (
                            assignment.get("assigned_to_user_name")
                            or assignment.get("assigned_employee_name")
                            or ""
                        )
                else:
                    if getattr(assignment, "is_active", True) is False:
                        continue
                    team_name = getattr(assignment, "team_name", None)
                    members = getattr(assignment, "members", None) or []
                    names = []
                    for member in members:
                        name = (
                            getattr(member, "user_name", None)
                            or getattr(member, "employee_name", None)
                            or getattr(member, "name", None)
                        )
                        if name:
                            names.append(str(name))
                    member_text = ", ".join(names)
                    if not member_text:
                        member_text = (
                            getattr(assignment, "assigned_to_user_name", None)
                            or getattr(assignment, "assigned_employee_name", None)
                            or ""
                        )

                if team_name and member_text:
                    active.append(f"{team_name} ({member_text})")
                elif team_name:
                    active.append(str(team_name))
                elif member_text:
                    active.append(member_text)

            if active:
                return " | ".join(active)

        # Suggestions are advisory only and must never appear as an assignment.
        return "Not Assigned"

    def _department_display(self):
        """Return the confirmed department from canonical work/routing data.

        Department ownership belongs to DocumentDepartmentRouting / WorkAssignment;
        DocumentModel suggestions are advisory only.
        """
        assignments = self._get_val("work_assignments", None)
        if isinstance(assignments, list):
            names = []
            for assignment in assignments:
                if isinstance(assignment, dict):
                    if assignment.get("is_active", True) is False:
                        continue
                    routing = assignment.get("routing") or {}
                    name = (
                        assignment.get("department_name")
                        or assignment.get("department")
                        or (routing.get("department_name") if isinstance(routing, dict) else None)
                    )
                else:
                    if getattr(assignment, "is_active", True) is False:
                        continue
                    routing = getattr(assignment, "routing", None)
                    name = (getattr(assignment, "department_name", None)
                            or getattr(assignment, "department", None)
                            or getattr(routing, "department_name", None)
                            or getattr(getattr(routing, "department", None), "name", None))
                if name and str(name) not in names:
                    names.append(str(name))
            if names:
                return " | ".join(names)

        # Also inspect canonical routing branches for department/HOD routes.
        branches = self._get_val("department_routings", None)
        if branches is None:
            branches = self._get_val("branches", None)
        names = []
        for branch in branches or []:
            if isinstance(branch, dict):
                if branch.get("is_active", True) is False:
                    continue
                if branch.get("branch_type") != "DEPARTMENT_HOD":
                    continue
                dept = branch.get("department")
                name = branch.get("department_name")
                if not name and isinstance(dept, dict):
                    name = dept.get("name")
            else:
                if getattr(branch, "is_active", True) is False or getattr(branch, "branch_type", None) != "DEPARTMENT_HOD":
                    continue
                dept = getattr(branch, "department", None)
                name = getattr(branch, "department_name", None) or getattr(dept, "name", None)
            if name and str(name) not in names:
                names.append(str(name))
        return " | ".join(names) if names else "Not Specified"

    def add_field(self, label: str, value_text: str):
        val_lbl = QLabel(value_text)
        val_lbl.setWordWrap(True)
        val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        val_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        val_lbl.setStyleSheet(
            "color: #1E293B; font-weight: 500; font-size: 12px;"
        )
        self.fields[label] = val_lbl
        self.form.addRow(f"{label}:", val_lbl)

    def set_document(self, document):
        self.document = document or DocumentModel()

        self.fields["Reference"].setText(self._get_val("reference"))
        self.fields["Title / Subject"].setText(self._get_val("subject", self._get_val("title", "—")))
        self.fields["Source"].setText(self._get_val("source", "External"))
        self.fields["Received Date"].setText(self._get_val("received", self._get_val("date", "N/A")))
        self.fields["Ingestion Mode"].setText(
            self._get_val("mode", "—")
        )
        self.fields["Format"].setText(
            self._get_val("format", self._get_val("file_type", "—"))
        )
        self.fields["Priority"].setText(self._get_val("priority", "Medium"))
        self.fields["Target Deadline"].setText(
            self._get_val("deadline", "—")
        )

        self.fields["Department"].setText(self._department_display())
        self.fields["Assigned Staff / Team"].setText(self._assignment_display())
        self.fields["Status"].setText(
            self._get_val("status", "Received")
        )
