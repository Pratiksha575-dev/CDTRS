# ==============================================================================
# PZ_26/08 - Hardware-Accelerated In-App Document Previewer (QPdfView / QPdfDocument)
# Renders PDF documents, scanned images, and intake email dispatches with zoom & fit controls
# ==============================================================================

import os
from typing import Any, Dict, Optional, Union
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QImage, QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    HAS_QT_PDF = True
except ImportError:
    HAS_QT_PDF = False

from models.document import DocumentModel
from services.attachment_service import attachment_service


class DocumentPreview(QFrame):
    """
    Production In-App Document Preview Widget for CDTRS.
    Natively renders multi-page PDF files, images, text dispatches, and email bodies
    inside the application pane without relying on local machine paths.
    """

    def __init__(self, document: Optional[Union[DocumentModel, Dict[str, Any]]] = None):
        super().__init__()
        self.document = document or {}
        self.setObjectName("contentCard")
        self._current_resolved_path: Optional[str] = None
        self._pdf_doc: Optional[Any] = None

        if HAS_QT_PDF:
            self._pdf_doc = QPdfDocument(self)

        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # Header Row
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(8)

        title = QLabel("Document Preview")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        hdr_layout.addWidget(title)

        self.format_badge = QLabel("PDF")
        self.format_badge.setStyleSheet(
            "background-color: #0F172A; color: white; padding: 2px 8px; border-radius: 3px; font-weight: 600; font-size: 10px;"
        )
        hdr_layout.addWidget(self.format_badge)
        hdr_layout.addStretch()

        # PDF Control Toolbar (Zoom + Page navigation)
        self.pdf_toolbar = QWidget()
        tb_layout = QHBoxLayout(self.pdf_toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)

        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
        self.fit_btn.clicked.connect(self._fit_width)
        tb_layout.addWidget(self.fit_btn)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; font-weight: bold; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        tb_layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; font-weight: bold; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        tb_layout.addWidget(self.zoom_out_btn)

        self.page_info_lbl = QLabel("1 / 1")
        self.page_info_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600; padding: 0 4px;")
        tb_layout.addWidget(self.page_info_lbl)

        hdr_layout.addWidget(self.pdf_toolbar)
        root_layout.addLayout(hdr_layout)

        # Content Stack
        self.stack = QStackedWidget()

        # Page 0: PDF Viewer
        if HAS_QT_PDF:
            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self._pdf_doc)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.pdf_view.setStyleSheet("background-color: #525659; border: 1px solid #CBD5E1; border-radius: 4px;")
            self.stack.addWidget(self.pdf_view)
        else:
            self.pdf_fallback_lbl = QLabel("PDF engine initializing...")
            self.stack.addWidget(self.pdf_fallback_lbl)

        # Page 1: Image Viewer
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setAlignment(Qt.AlignCenter)
        self.image_scroll.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        self.stack.addWidget(self.image_scroll)

        # Page 2: Text / Dispatch Browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 12px; font-size: 12px; color: #1E293B;"
        )
        self.stack.addWidget(self.text_browser)

        # Page 3: Metadata / Info Fallback
        self.fallback_frame = QFrame()
        self.fallback_frame.setStyleSheet("background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 16px;")
        fb_layout = QVBoxLayout(self.fallback_frame)
        fb_layout.setAlignment(Qt.AlignCenter)
        fb_layout.setSpacing(8)

        self.fallback_text = QLabel()
        self.fallback_text.setAlignment(Qt.AlignCenter)
        self.fallback_text.setStyleSheet("color: #475569; font-size: 12px;")
        fb_layout.addWidget(self.fallback_text)

        self.stack.addWidget(self.fallback_frame)

        self.stack.setMinimumHeight(240)
        root_layout.addWidget(self.stack, 1)

    def _resolve_document_file_path(self) -> Optional[str]:
        """
        Resolves the local cached copy of the document or its original attachment.
        Does NOT rely on permanent local paths — downloads on-demand into client cache.
        """
        # 1. Direct file_path attribute if present and exists on disk
        if hasattr(self.document, "file_path") and self.document.file_path:
            if os.path.exists(self.document.file_path):
                return self.document.file_path
        elif isinstance(self.document, dict) and self.document.get("file_path"):
            if os.path.exists(self.document.get("file_path")):
                return self.document.get("file_path")

        # 2. Query attachments from attachment_service
        doc_id = getattr(self.document, "id", None) or (self.document.get("id") if isinstance(self.document, dict) else None)
        if doc_id:
            try:
                attachments = attachment_service.get_document_attachments(doc_id) or []
                if attachments:
                    # Prefer ORIGINAL attachment
                    orig = next((a for a in attachments if a.category == "ORIGINAL"), attachments[0])
                    cached_path = attachment_service._ensure_local_copy(orig, parent=self)
                    if cached_path and os.path.exists(cached_path):
                        return cached_path
            except Exception:
                pass

        return None

    def update_preview(self):
        """Updates the preview area according to the current document."""
        file_path = self._resolve_document_file_path()
        self._current_resolved_path = file_path

        ref = getattr(self.document, "reference_no", None) or getattr(self.document, "reference", None) or (self.document.get("reference") if isinstance(self.document, dict) else "Document")
        title = getattr(self.document, "title", None) or getattr(self.document, "subject", None) or (self.document.get("title") if isinstance(self.document, dict) else "Untitled")
        mode = getattr(self.document, "mode", None) or (self.document.get("mode") if isinstance(self.document, dict) else "Outlook")
        desc = getattr(self.document, "description", None) or getattr(self.document, "ocr_text", None) or (self.document.get("description") if isinstance(self.document, dict) else "")

        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            self.format_badge.setText(ext.replace(".", "").upper() or "FILE")

            if ext == ".pdf" and HAS_QT_PDF:
                self.pdf_toolbar.setVisible(True)
                self.stack.setCurrentIndex(0)
                self._pdf_doc.load(file_path)
                page_count = self._pdf_doc.pageCount()
                self.page_info_lbl.setText(f"1 / {page_count}" if page_count > 0 else "1 / 1")
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
                return

            elif ext in (".png", ".jpg", ".jpeg", ".bmp"):
                self.pdf_toolbar.setVisible(False)
                self.stack.setCurrentIndex(1)
                pixmap = QPixmap(file_path)
                scaled = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                return

            elif ext in (".txt", ".log", ".csv", ".json"):
                self.pdf_toolbar.setVisible(False)
                self.stack.setCurrentIndex(2)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    self.text_browser.setPlainText(content)
                except Exception:
                    self.text_browser.setPlainText(desc or "Unable to read text file.")
                return

        # If no binary file or unrenderable format (e.g. email communication body or docx)
        self.pdf_toolbar.setVisible(False)
        self.format_badge.setText(mode.upper() if mode else "INTAKE")

        if desc and len(desc.strip()) > 0:
            self.stack.setCurrentIndex(2)
            html = f"""
            <div style="font-family: Arial, sans-serif; color: #1E293B;">
              <h4 style="margin: 0 0 6px 0; color: #0F172A;">{title}</h4>
              <p style="font-size: 11px; color: #64748B; margin: 0 0 10px 0;">Source: {mode} • Ref: {ref}</p>
              <hr style="border: 0; border-top: 1px solid #E2E8F0; margin-bottom: 10px;" />
              <div style="white-space: pre-wrap; line-height: 1.5; font-size: 12px;">{desc}</div>
            </div>
            """
            self.text_browser.setHtml(html)
        else:
            self.stack.setCurrentIndex(3)
            self.fallback_text.setText(
                f"Document Ref: {ref}\n\n"
                f"Title: {title}\n"
                f"Ingestion Mode: {mode}\n\n"
                f"(Direct Communication / Intake Dispatch Body)"
            )

    def _fit_width(self):
        if HAS_QT_PDF and hasattr(self, "pdf_view"):
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _zoom_in(self):
        if HAS_QT_PDF and hasattr(self, "pdf_view"):
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(self.pdf_view.zoomFactor() * 1.2)

    def _zoom_out(self):
        if HAS_QT_PDF and hasattr(self, "pdf_view"):
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(max(0.2, self.pdf_view.zoomFactor() / 1.2))

    def set_document(self, document: Optional[Union[DocumentModel, Dict[str, Any]]]):
        self.document = document or {}
        self.update_preview()
