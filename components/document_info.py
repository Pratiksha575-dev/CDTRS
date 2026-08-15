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
        
        dept_val = self._get_val("target_department_name", self._get_val("department", "Not Specified"))
        if not dept_val or dept_val == "-":
            dept_val = "Not Specified"
        self.add_field("Department", dept_val)

        emp_val = self._get_val("assigned_employee_name", self._get_val("employee", "Not Assigned"))
        if not emp_val or emp_val == "-":
            emp_val = "Not Assigned"
        self.add_field("Assigned Employee", emp_val)

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

    def add_field(self, label: str, value_text: str):
        val_lbl = QLabel(value_text)
        val_lbl.setWordWrap(True)
        val_lbl.setStyleSheet("color: #1E293B; font-weight: 500; font-size: 12px;")
        self.fields[label] = val_lbl
        self.form.addRow(f"{label}:", val_lbl)

    def set_document(self, document):
        self.document = document or DocumentModel()
        self.fields["Reference"].setText(self._get_val("reference"))
        self.fields["Title / Subject"].setText(self._get_val("subject"))
        self.fields["Source"].setText(self._get_val("source", "External"))
        self.fields["Received Date"].setText(self._get_val("received", "N/A"))
        self.fields["Ingestion Mode"].setText(self._get_val("mode", "Government Mail"))
        self.fields["Format"].setText(self._get_val("format", self._get_val("file_type", "PDF")))
        self.fields["Priority"].setText(self._get_val("priority", "Medium"))
        self.fields["Target Deadline"].setText(self._get_val("deadline", "None"))
        
        dept_val = self._get_val("target_department_name", self._get_val("department", "Not Specified"))
        self.fields["Department"].setText(dept_val if dept_val and dept_val != "-" else "Not Specified")

        emp_val = self._get_val("assigned_employee_name", self._get_val("employee", "Not Assigned"))
        self.fields["Assigned Employee"].setText(emp_val if emp_val and emp_val != "-" else "Not Assigned")

        self.fields["Current Stage"].setText(self._get_val("current_stage", "DS"))
        self.fields["Status"].setText(self._get_val("status", "Received"))