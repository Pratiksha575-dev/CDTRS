from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QFormLayout
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
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Document Information")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setSpacing(8)

        # Metadata fields
        self.add_field("Reference", self._get_val("reference"))
        self.add_field("Title / Subject", self._get_val("subject"))
        self.add_field("Source", self._get_val("source", "External"))
        self.add_field("Received Date", self._get_val("received", "N/A"))
        self.add_field("Ingestion Mode", self._get_val("mode", "Government Mail"))
        self.add_field("Format", self._get_val("format", self._get_val("file_type", "PDF")))
        self.add_field("Priority", self._get_val("priority", "Medium"))
        self.add_field("Target Deadline", self._get_val("deadline", "None"))

        dept_val = self._get_val(
            "target_department_name",
            self._get_val("department", "Not Specified")
        )
        self.add_field("Department", self._display_value(dept_val, "Not Specified"))

        self.add_field("Assigned Staff / Team", self._assignment_display())
        self.add_field("Current Stage", self._get_val("current_stage", "DS"))
        self.add_field("Status", self._get_val("status", "Received"))

        layout.addLayout(self.form)
        layout.addStretch()
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

        # Legacy / compatibility fallback.
        emp_val = self._get_val(
            "assigned_employee_name",
            self._get_val("employee", "Not Assigned")
        )
        return self._display_value(emp_val, "Not Assigned")

    def add_field(self, label: str, value_text: str):
        val_lbl = QLabel(value_text)
        val_lbl.setWordWrap(True)
        val_lbl.setStyleSheet(
            "color: #1E293B; font-weight: 500; font-size: 12px;"
        )
        self.fields[label] = val_lbl
        self.form.addRow(f"{label}:", val_lbl)

    def set_document(self, document):
        self.document = document or DocumentModel()

        self.fields["Reference"].setText(self._get_val("reference"))
        self.fields["Title / Subject"].setText(self._get_val("subject"))
        self.fields["Source"].setText(self._get_val("source", "External"))
        self.fields["Received Date"].setText(self._get_val("received", "N/A"))
        self.fields["Ingestion Mode"].setText(
            self._get_val("mode", "Government Mail")
        )
        self.fields["Format"].setText(
            self._get_val("format", self._get_val("file_type", "PDF"))
        )
        self.fields["Priority"].setText(self._get_val("priority", "Medium"))
        self.fields["Target Deadline"].setText(
            self._get_val("deadline", "None")
        )

        dept_val = self._get_val(
            "target_department_name",
            self._get_val("department", "Not Specified")
        )
        self.fields["Department"].setText(
            self._display_value(dept_val, "Not Specified")
        )

        self.fields["Assigned Staff / Team"].setText(self._assignment_display())
        self.fields["Current Stage"].setText(
            self._get_val("current_stage", "DS")
        )
        self.fields["Status"].setText(
            self._get_val("status", "Received")
        )
