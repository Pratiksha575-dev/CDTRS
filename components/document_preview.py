from typing import Any, Dict, Optional, Union
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from models.document import DocumentModel


class DocumentPreview(QFrame):
    """
    Document preview panel for DocumentViewer and Document Intake.
    Displays file metadata, source dispatch preview, or loaded document details.
    """

    def __init__(self, document: Optional[Union[DocumentModel, Dict[str, Any]]] = None):
        super().__init__()
        self.document = document or {}
        self.setObjectName("contentCard")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel("Document Preview")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.preview_area = QLabel()
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setMinimumHeight(220)
        self.preview_area.setMinimumWidth(260)
        self.preview_area.setObjectName("documentPreview")
        self.preview_area.setStyleSheet("""
            QLabel#documentPreview {
                background-color: #F8FAFC;
                border: 2px dashed #CBD5E1;
                border-radius: 6px;
                color: #475569;
                font-size: 13px;
                padding: 16px;
            }
        """)

        self.update_preview()
        layout.addWidget(self.preview_area, 1)
        self.setLayout(layout)

    def update_preview(self):
        if hasattr(self.document, "file_path"):
            file_path = self.document.file_path or ""
            file_type = self.document.format or self.document.file_type or "PDF"
            ref = self.document.reference or "Document"
            title = self.document.title or "Untitled"
            mode = self.document.mode or "Direct"
        elif isinstance(self.document, dict):
            file_path = self.document.get("file_path", "")
            file_type = self.document.get("format", self.document.get("file_type", "PDF"))
            ref = self.document.get("reference", "Document")
            title = self.document.get("title", "Untitled")
            mode = self.document.get("mode", "Direct")
        else:
            file_path = ""
            file_type = "PDF"
            ref = "Document"
            title = "Untitled"
            mode = "Direct"

        if file_path:
            filename = file_path.replace("\\", "/").split("/")[-1]
            self.preview_area.setText(
                f"📄 {ref}\n\n"
                f"Title: {title}\n"
                f"Source File: {filename}\n"
                f"Ingestion Mode: {mode} ({file_type})\n\n"
                f"✓ Canonical Original Document Attached"
            )
        else:
            self.preview_area.setText(
                f"📄 {ref}\n\n"
                f"Title: {title}\n\n"
                f"Dispatched via {mode}\n(Direct Text / Communication Body)"
            )

    def set_document(self, document: Optional[Union[DocumentModel, Dict[str, Any]]]):
        self.document = document or {}
        self.update_preview()