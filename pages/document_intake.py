from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QFileDialog
)

from PySide6.QtCore import Qt

from services.ocr_service import ocr_service
from services.routing_service import routing_service
from services.document_service import document_service
from services.workflow_service import WorkflowService

class DocumentIntakePage(QWidget):

    def __init__(self):
        super().__init__()

        self.selected_file = None

        self.setup_ui()

    def setup_ui(self):

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # PAGE HEADER
        # --------------------------------

        title = QLabel("Document Intake")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Capture and review incoming documents before routing."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # MAIN CONTENT
        # --------------------------------

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # --------------------------------
        # LEFT - DOCUMENT PREVIEW
        # --------------------------------

        preview_card = QFrame()
        preview_card.setObjectName("contentCard")

        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        preview_title = QLabel("Document")
        preview_title.setObjectName("sectionTitle")

        self.preview_label = QLabel(
            "No document selected"
        )

        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 350)
        self.preview_label.setObjectName("documentPreview")

        select_button = QPushButton("Select Document")
        select_button.clicked.connect(self.select_document)

        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.preview_label)
        preview_layout.addWidget(select_button)

        preview_card.setLayout(preview_layout)

        # --------------------------------
        # RIGHT - DOCUMENT INFORMATION
        # --------------------------------

        info_card = QFrame()
        info_card.setObjectName("contentCard")

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(12)

        info_title = QLabel("Document Information")
        info_title.setObjectName("sectionTitle")

        form = QFormLayout()
        form.setSpacing(10)

        self.title_input = QLineEdit()
        self.date_input = QLineEdit()

        self.mode_input = QComboBox()
        self.mode_input.addItems([
            "Email",
            "Intranet",
            "Fax",
            "Scanned",
            "Other"
            ])

        self.source_input = QLineEdit()
        self.deadline_input = QLineEdit()

        self.remarks_input = QTextEdit()
        self.remarks_input.setMaximumHeight(80)

        form.addRow("Title:", self.title_input)
        form.addRow("Date:", self.date_input)
        form.addRow("Mode:", self.mode_input)
        form.addRow("Source:", self.source_input)
        form.addRow("Deadline:", self.deadline_input)

        info_layout.addWidget(info_title)
        info_layout.addLayout(form)

        # --------------------------------
        # OCR SECTION
        # --------------------------------

        ocr_title = QLabel("Extracted Text")
        ocr_title.setObjectName("sectionTitle")

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText(
            "OCR extracted text will appear here..."
        )

        info_layout.addWidget(ocr_title)
        info_layout.addWidget(self.ocr_text)

        info_card.setLayout(info_layout)

        content_layout.addWidget(preview_card, 1)
        content_layout.addWidget(info_card, 2)

        main_layout.addLayout(content_layout)

        # --------------------------------
        # ROUTING SECTION
        # --------------------------------

        routing_card = QFrame()
        routing_card.setObjectName("contentCard")

        routing_layout = QHBoxLayout()
        routing_layout.setContentsMargins(20, 15, 20, 15)
        routing_layout.setSpacing(15)

        routing_title = QLabel("Routing Suggestion")
        routing_title.setObjectName("sectionTitle")

        self.department_label = QLabel("Department: Not available")
        self.employee_label = QLabel("Employee: Not available")
        self.confidence_label = QLabel("Confidence: --")

        suggest_button = QPushButton("Suggest Routing")
        suggest_button.clicked.connect(self.suggest_routing)

        accept_button = QPushButton("Accept Routing")
        accept_button.clicked.connect(self.accept_routing)

        routing_layout.addWidget(routing_title)
        routing_layout.addWidget(self.department_label)
        routing_layout.addWidget(self.employee_label)
        routing_layout.addWidget(self.confidence_label)

        routing_layout.addStretch()

        routing_layout.addWidget(suggest_button)
        routing_layout.addWidget(accept_button)

        routing_card.setLayout(routing_layout)

        main_layout.addWidget(routing_card)

        # --------------------------------
        # SAVE / FORWARD
        # --------------------------------

        self.forward_button = QPushButton(
            "Save & Forward to Director"
        )

        self.forward_button.clicked.connect(
            self.save_and_forward
        )

        main_layout.addWidget(
            self.forward_button,
            alignment=Qt.AlignRight
        )

        self.setLayout(main_layout)

    # ====================================
    # ACTIONS
    # ====================================

    def select_document(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "Documents (*.pdf *.png *.jpg *.jpeg);;All Files (*)"
        )

        if not file_path:
            return

        self.selected_file = file_path

        self.preview_label.setText(
            f"Selected:\n{file_path}"
        )

        # OCR will eventually happen here
        result = ocr_service.extract_text(file_path)

        self.ocr_text.setPlainText(
            result.get("text", "")
        )

    def suggest_routing(self):

        text = self.ocr_text.toPlainText()

        result = routing_service.suggest_routing(text)

        department = result.get("department")
        employee = result.get("employee")
        confidence = result.get("confidence", 0)

        self.department_label.setText(
            f"Department: {department or 'Not found'}"
        )

        self.employee_label.setText(
            f"Employee: {employee or 'Not found'}"
        )

        self.confidence_label.setText(
            f"Confidence: {confidence:.0%}"
        )

    def accept_routing(self):

        print("Routing accepted")

    def save_and_forward(self):

        if not hasattr(self, "current_document"):

            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "No Document",
                "No document is currently loaded."
            )

            return

        document = self.current_document

        # Update information entered on screen
        document["title"] = self.title_input.text()
        document["date"] = self.date_input.text()
        document["mode"] = self.mode_input.currentText()
        document["source"] = self.source_input.text()
        document["deadline"] = self.deadline_input.text()
        document["file_path"] = self.selected_file or ""

        print(
            "Forwarding document:",
            document
        )

        success = WorkflowService.forward_to_director(
            document
        )

        if success:

            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Document Forwarded",
                f"Document {document.get('reference', '')} "
                "has been forwarded to the Director."
            )

        else:

            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Forwarding Failed",
                "The document could not be forwarded."
            )

    def load_document(self, document):

        self.current_document = document.copy()

        self.title_input.setText(
            document.get(
                "title",
                document.get("subject", "")
            )
        )

        self.date_input.setText(
            document.get("date", "")
        )

        self.mode_input.setCurrentText(
            document.get("mode", "")
        )

        self.source_input.setText(
            document.get("source", "")
        )

        self.deadline_input.setText(
            document.get("deadline", "")
        )

        self.selected_file = document.get(
            "file_path",
            ""
        )

        self.preview_label.setText(
            f"Source: {document.get('source', '')}\n\n"
            f"File type: {document.get('file_type', '')}\n\n"
            f"{document.get('title', document.get('subject', ''))}"
        )

        self.ocr_text.clear()

        self.department_label.setText(
            "Department: Not available"
        )

        self.employee_label.setText(
            "Employee: Not available"
        )

        self.confidence_label.setText(
            "Confidence: 0%"
        )