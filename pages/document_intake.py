from datetime import datetime
from typing import Any, Dict, Optional, Union
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from models.enums import IngestionModeEnum, PriorityEnum, RouteTypeEnum
from repositories.provider import get_repository
from services.document_service import document_service
from services.ocr_service import ocr_service
from services.routing_service import routing_service


class DocumentIntakePage(QWidget):
    """
    Document Intake & Processing Page for Director Secretary.
    Captures incoming documents, metadata, OCR text, and routes initial intake
    directly to the Director for review or directly to HOD/Staff if a prior Director directive exists.
    Allows DS to edit suggested routing before confirmation.
    """

    document_processed = Signal(object)  # Emits newly created & routed DocumentModel

    def __init__(self):
        super().__init__()
        self.selected_file: Optional[str] = None
        self.current_inbox_item_id: Optional[int] = None
        self.extracted_ocr_text: str = ""
        self.has_prior_director_remark: bool = False
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # PAGE HEADER
        # --------------------------------
        header_layout = QHBoxLayout()
        vbox = QVBoxLayout()
        vbox.setSpacing(2)

        title = QLabel("Document Intake & Processing Verification")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Verify extracted metadata and routing intelligence from incoming dispatches before committing to CDTRS workflow."
        )
        subtitle.setObjectName("pageSubtitle")

        vbox.addWidget(title)
        vbox.addWidget(subtitle)
        header_layout.addLayout(vbox)
        header_layout.addStretch()

        # Manual File Upload Button
        manual_btn = QPushButton("📁 Manual Intake / Upload File")
        manual_btn.setStyleSheet("background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
        manual_btn.clicked.connect(self.select_document)
        header_layout.addWidget(manual_btn)

        main_layout.addLayout(header_layout)

        # --------------------------------
        # MAIN 2-COLUMN CONTENT
        # --------------------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        # LEFT - DOCUMENT SOURCE & PREVIEW CARD
        preview_card = QFrame()
        preview_card.setObjectName("contentCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(12)

        preview_title = QLabel("Document Source & Dispatch File")
        preview_title.setObjectName("sectionTitle")
        preview_layout.addWidget(preview_title)

        self.preview_label = QLabel("No document loaded\n\nSelect an incoming item from Inbox or click 'Manual Intake / Upload File' to process a document.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(260, 220)
        self.preview_label.setStyleSheet("background-color: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 8px; color: #64748B; padding: 18px; font-size: 12px;")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label, 1)

        # Compact OCR Status Badge
        self.ocr_status_frame = QFrame()
        self.ocr_status_frame.setStyleSheet("background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 5px; padding: 8px;")
        ocr_hlayout = QHBoxLayout(self.ocr_status_frame)
        ocr_hlayout.setContentsMargins(10, 6, 10, 6)
        
        self.ocr_status_lbl = QLabel("✓ OCR Processed • Content Extracted & Indexed")
        self.ocr_status_lbl.setStyleSheet("color: #166534; font-weight: 600; font-size: 12px;")
        ocr_hlayout.addWidget(self.ocr_status_lbl)
        self.ocr_status_frame.setVisible(False)
        preview_layout.addWidget(self.ocr_status_frame)

        content_layout.addWidget(preview_card, 1)

        # RIGHT - DOCUMENT INFORMATION FORM
        info_card = QFrame()
        info_card.setObjectName("contentCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 18, 18, 18)
        info_layout.setSpacing(10)

        info_title = QLabel("Extracted Document Information")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)

        form = QFormLayout()
        form.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter document title / subject")

        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Auto-generated reference number")

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("YYYY-MM-DD")

        self.mode_input = QComboBox()
        self.mode_input.addItems([
            IngestionModeEnum.GOVERNMENT_MAIL.value,
            IngestionModeEnum.INTERNAL_OUTLOOK.value,
            IngestionModeEnum.EMAIL.value,
            IngestionModeEnum.INTRANET.value,
            IngestionModeEnum.FAX.value,
            IngestionModeEnum.SCANNED.value,
            IngestionModeEnum.PHYSICAL.value,
            IngestionModeEnum.DIRECT_SUBMISSION.value,
            IngestionModeEnum.OTHER.value
        ])

        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("e.g. Finance Department, Cabinet Secretariat")

        self.format_input = QComboBox()
        self.format_input.addItems([
            "PDF", "DOCX", "Image (PNG/JPG)", "Scanned PDF", "Email Body", "Other"
        ])

        self.priority_input = QComboBox()
        self.priority_input.addItems([
            PriorityEnum.HIGH.value,
            PriorityEnum.MEDIUM.value,
            PriorityEnum.LOW.value
        ])
        self.priority_input.setCurrentText(PriorityEnum.MEDIUM.value)

        self.deadline_input = QLineEdit()
        self.deadline_input.setPlaceholderText("YYYY-MM-DD (optional)")

        form.addRow("Title / Subject:", self.title_input)
        form.addRow("Reference No:", self.ref_input)
        form.addRow("Received Date:", self.date_input)
        form.addRow("Ingestion Mode:", self.mode_input)
        form.addRow("Sender / Source:", self.source_input)
        form.addRow("Document Format:", self.format_input)
        form.addRow("Priority:", self.priority_input)
        form.addRow("Target Deadline:", self.deadline_input)

        info_layout.addLayout(form)
        content_layout.addWidget(info_card, 2)
        main_layout.addLayout(content_layout)

        # --------------------------------
        # ROUTING INTELLIGENCE & DIRECTOR REMARK CARD
        # --------------------------------
        bottom_cards_layout = QHBoxLayout()
        bottom_cards_layout.setSpacing(18)

        # 1. Routing Intelligence Card (Editable by DS)
        routing_card = QFrame()
        routing_card.setObjectName("contentCard")
        r_layout = QVBoxLayout(routing_card)
        r_layout.setContentsMargins(16, 14, 16, 14)
        r_layout.setSpacing(8)

        r_title = QLabel("Routing Intelligence & DS Destination")
        r_title.setObjectName("sectionTitle")
        r_layout.addWidget(r_title)

        r_form = QFormLayout()
        r_form.setSpacing(6)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems([
            "Finance",
            "Procurement",
            "Human Resources",
            "Maintenance",
            "IT",
            "Not Specified"
        ])

        self.emp_combo = QComboBox()
        self.emp_combo.addItem("Not Assigned", None)
        try:
            repo = get_repository()
            for emp in repo.get_users(role="Employee"):
                self.emp_combo.addItem(f"{emp.full_name} ({emp.department_name or 'General'})", emp.id)
        except Exception:
            self.emp_combo.addItem("Rahul Sharma (Finance)", 101)
            self.emp_combo.addItem("Priya Verma (Procurement)", 201)

        self.confidence_label = QLabel("Confidence: 92% • Source: Document / OCR")
        self.confidence_label.setStyleSheet("color: #059669; font-weight: 600; font-size: 11px;")

        r_form.addRow("Target Dept:", self.dept_combo)
        r_form.addRow("Target Staff:", self.emp_combo)
        r_layout.addLayout(r_form)
        r_layout.addWidget(self.confidence_label)

        bottom_cards_layout.addWidget(routing_card, 1)

        # 2. Pre-existing Director Remark Card
        self.director_remark_card = QFrame()
        self.director_remark_card.setObjectName("contentCard")
        self.director_remark_card.setStyleSheet("QFrame#contentCard { background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 6px; }")
        
        dr_layout = QVBoxLayout(self.director_remark_card)
        dr_layout.setContentsMargins(16, 14, 16, 14)
        dr_layout.setSpacing(6)

        dr_title = QLabel("Prior Director Directive Detected in Source")
        dr_title.setStyleSheet("font-weight: 700; color: #92400E; font-size: 13px;")
        dr_layout.addWidget(dr_title)

        self.prior_remark_lbl = QLabel("No pre-existing Director remark detected.")
        self.prior_remark_lbl.setStyleSheet("color: #78350F; font-size: 12px; font-style: italic;")
        self.prior_remark_lbl.setWordWrap(True)
        dr_layout.addWidget(self.prior_remark_lbl)

        self.bypass_director_check = QCheckBox("Document contains verified Director directive (Bypass Director Review queue)")
        self.bypass_director_check.setStyleSheet("color: #92400E; font-weight: 600;")
        self.bypass_director_check.toggled.connect(self._update_action_button_text)
        dr_layout.addWidget(self.bypass_director_check)

        self.director_remark_card.setVisible(False)
        bottom_cards_layout.addWidget(self.director_remark_card, 1)

        main_layout.addLayout(bottom_cards_layout)

        # --------------------------------
        # CONFIRMATION ACTION BAR
        # --------------------------------
        action_bar = QHBoxLayout()
        action_bar.addStretch()

        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 8px 16px; border-radius: 5px;")
        self.clear_btn.clicked.connect(self.clear_form)
        action_bar.addWidget(self.clear_btn)

        self.submit_btn = QPushButton("Confirm & Send for Director Review")
        self.submit_btn.setStyleSheet("background-color: #0F172A; color: white; font-size: 13px; font-weight: 600; padding: 9px 24px; border-radius: 6px;")
        self.submit_btn.clicked.connect(self.save_and_confirm_routing)
        action_bar.addWidget(self.submit_btn)

        main_layout.addLayout(action_bar)
        self.setLayout(main_layout)

    # ====================================
    # ACTIONS
    # ====================================

    def _update_action_button_text(self):
        if self.bypass_director_check.isChecked():
            self.submit_btn.setText("Confirm & Route Directly to HOD / Staff")
            self.submit_btn.setStyleSheet("background-color: #D97706; color: white; font-size: 13px; font-weight: 600; padding: 9px 24px; border-radius: 6px;")
        else:
            self.submit_btn.setText("Confirm & Send for Director Review")
            self.submit_btn.setStyleSheet("background-color: #0F172A; color: white; font-size: 13px; font-weight: 600; padding: 9px 24px; border-radius: 6px;")

    def select_document(self):
        """Allows manual upload of local PDFs, images, or scanned dispatches."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Intake Document",
            "",
            "Documents (*.pdf *.docx *.png *.jpg *.jpeg *.txt);;All Files (*)"
        )
        if not file_path:
            return

        self.selected_file = file_path
        fname = os.path.basename(file_path)
        self.incoming_attachments_list = [fname]
        self.incoming_attachment_count = 1
        self.preview_label.setText(f"Manual File Loaded:\n{fname}\n\nPath: {file_path}")

        # Run OCR extraction
        res = ocr_service.process_incoming_document(file_path, incoming_item={"title": fname, "source": "Manual Upload", "mode": "Manual Upload"})
        self._populate_extracted_data(res, file_path=file_path)

    def load_document(self, doc_dict_or_model: Union[DocumentModel, Dict[str, Any]]):
        """Pre-populates intake form and runs OCR extraction when opened from Inbox."""
        if isinstance(doc_dict_or_model, DocumentModel):
            doc = doc_dict_or_model
            self.current_inbox_item_id = doc.id
            self.incoming_attachments_list = doc.attachments_list or []
            self.incoming_attachment_count = doc.attachment_count if doc.attachment_count is not None else len(self.incoming_attachments_list)
            raw_data = {
                "title": doc.title,
                "date": doc.date,
                "mode": doc.mode,
                "source": doc.source,
                "priority": doc.priority,
                "deadline": doc.deadline,
                "file_path": doc.file_path,
                "format": doc.format or doc.file_type,
                "has_prior_director_remark": doc.has_prior_director_remark,
                "director_remark": doc.director_remark,
                "attachments_list": self.incoming_attachments_list,
                "attachment_count": self.incoming_attachment_count
            }
        else:
            raw_data = doc_dict_or_model
            self.current_inbox_item_id = raw_data.get("id")
            self.incoming_attachments_list = raw_data.get("attachments_list", [])
            self.incoming_attachment_count = raw_data.get("attachment_count", len(self.incoming_attachments_list))

        raw_file_path = raw_data.get("file_path", "")
        # Run OCR and routing analysis
        ocr_result = ocr_service.process_incoming_document(
            file_path=raw_file_path,
            incoming_item=raw_data
        )

        self._populate_extracted_data(ocr_result, file_path=raw_file_path)

    def _populate_extracted_data(self, ocr_result: Dict[str, Any], file_path: Optional[str] = None):
        self.extracted_ocr_text = ocr_result.get("extracted_text", "")
        self.title_input.setText(ocr_result.get("title", ""))
        self.ref_input.setText(f"CDTRS-2026-{self.current_inbox_item_id or 101:03d}")
        self.date_input.setText(ocr_result.get("date", datetime.now().strftime("%Y-%m-%d")))

        # Ingestion Mode
        mode_val = ocr_result.get("mode", IngestionModeEnum.GOVERNMENT_MAIL.value)
        idx = self.mode_input.findText(mode_val)
        if idx >= 0:
            self.mode_input.setCurrentIndex(idx)
        else:
            self.mode_input.setCurrentText(mode_val)

        self.source_input.setText(ocr_result.get("source", ""))

        # Format
        fmt_val = ocr_result.get("format", "PDF")
        f_idx = self.format_input.findText(fmt_val)
        if f_idx >= 0:
            self.format_input.setCurrentIndex(f_idx)
        else:
            self.format_input.setCurrentText(fmt_val)

        # Priority
        priority_val = PriorityEnum.normalize(ocr_result.get("priority", "Medium"))
        self.priority_input.setCurrentText(priority_val)

        self.deadline_input.setText(ocr_result.get("deadline", ""))

        # Routing Intelligence Dropdowns (Editable)
        dept = ocr_result.get("suggested_department", "Not Specified")
        emp = ocr_result.get("suggested_employee") or "Not Assigned"
        conf = ocr_result.get("confidence", 0)

        d_idx = self.dept_combo.findText(dept)
        if d_idx >= 0:
            self.dept_combo.setCurrentIndex(d_idx)

        e_idx = -1
        for i in range(self.emp_combo.count()):
            if emp and emp.lower() in self.emp_combo.itemText(i).lower():
                e_idx = i
                break
        if e_idx >= 0:
            self.emp_combo.setCurrentIndex(e_idx)
        else:
            self.emp_combo.setCurrentIndex(0)

        self.confidence_label.setText(f"Confidence: {conf}% • Source: Document / OCR")

        # Compact OCR Status
        pages = ocr_result.get("pages_extracted", 1)
        self.ocr_status_lbl.setText(f"✓ OCR Processed • {pages} page(s) extracted and indexed")
        self.ocr_status_frame.setVisible(True)

        # Prior Director Directive Handling
        has_remark = ocr_result.get("has_prior_director_remark", False)
        remark_text = ocr_result.get("director_remark", "")

        if has_remark and remark_text:
            self.has_prior_director_remark = True
            self.prior_remark_lbl.setText(f"Directive: \"{remark_text}\"")
            self.director_remark_card.setVisible(True)
            self.bypass_director_check.setChecked(True)
        else:
            self.has_prior_director_remark = False
            self.director_remark_card.setVisible(False)
            self.bypass_director_check.setChecked(False)

        self._update_action_button_text()

        # Update preview and selected file path
        if file_path and os.path.exists(file_path):
            self.selected_file = file_path
        elif ocr_result.get("file_path") and os.path.exists(ocr_result.get("file_path")):
            self.selected_file = ocr_result.get("file_path")
        elif self.selected_file and os.path.exists(self.selected_file):
            pass # Retain valid selected file
        else:
            self.selected_file = ocr_result.get("file_path") or f"data/incoming/{self.title_input.text()}"

        display_name = os.path.basename(self.selected_file) if self.selected_file else self.title_input.text()
        self.preview_label.setText(f"Dispatch File Loaded:\n{display_name}\n\nMode: {mode_val} | Format: {fmt_val}")

    def save_and_confirm_routing(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please provide a document Title / Subject.")
            return

        dept_text = self.dept_combo.currentText()
        if dept_text == "Not Specified":
            dept_text = None

        emp_raw = self.emp_combo.currentText()
        emp_text = emp_raw.split(" (")[0] if emp_raw != "Not Assigned" else None

        dept_id_map = {"Finance": 1, "Procurement": 2, "Human Resources": 3, "HR": 3, "Maintenance": 4, "IT": 5}
        target_dept_id = dept_id_map.get(dept_text) if dept_text else None
        emp_id = self.emp_combo.currentData()

        # Determine real physical upload path if exists on disk
        actual_upload_path = self.selected_file if (self.selected_file and os.path.exists(self.selected_file)) else None

        # Prepare DocumentModel
        doc_model = DocumentModel(
            id=self.current_inbox_item_id,
            title=title,
            reference_no=self.ref_input.text().strip() or None,
            date=self.date_input.text().strip() or datetime.now().strftime("%Y-%m-%d"),
            mode=self.mode_input.currentText(),
            source=self.source_input.text().strip() or "External",
            priority=self.priority_input.currentText(),
            deadline=self.deadline_input.text().strip() or None,
            format=self.format_input.currentText(),
            file_path=self.selected_file,
            ocr_text=self.extracted_ocr_text,
            attachment_count=getattr(self, "incoming_attachment_count", 1 if self.selected_file else 0),
            attachments_list=getattr(self, "incoming_attachments_list", [os.path.basename(self.selected_file)] if self.selected_file else []),
            target_department_name=dept_text,
            target_department_id=target_dept_id,
            assigned_employee_name=emp_text,
            assigned_employee_id=emp_id,
            suggested_department_name=dept_text,
            suggested_department_id=target_dept_id,
            suggested_employee_name=emp_text,
            suggested_employee_id=emp_id,
            has_prior_director_remark=self.bypass_director_check.isChecked(),
            director_remark=self.prior_remark_lbl.text().replace('Directive: "', '').rstrip('"') if self.bypass_director_check.isChecked() else None
        )

        try:
            # 1. Create canonical document
            created_doc = document_service.create_document(doc_model, file_path=actual_upload_path)

            # 2. Perform Routing Decision
            if self.bypass_director_check.isChecked():
                # Case A: Document already contains Director directive -> Route directly to Employee or HOD
                if emp_id:
                    routed_doc = routing_service.route_to_employee(
                        created_doc.id,
                        employee_id=emp_id
                    )
                    routed_doc.assigned_employee_name = emp_text
                    routed_doc.target_department_name = dept_text
                    msg = f"Document {routed_doc.reference} routed directly to Staff {emp_text} (Director review bypassed due to pre-existing directive)."
                else:
                    routed_doc = routing_service.route_to_hod(
                        created_doc.id,
                        department_id=target_dept_id or 1
                    )
                    routed_doc.target_department_name = dept_text
                    msg = f"Document {routed_doc.reference} routed directly to {dept_text or 'Department'} HOD (Director review bypassed due to pre-existing directive)."
            else:
                # Case B: Standard Intake -> Send for Director Review
                routed_doc = routing_service.route_to_director(created_doc.id)
                msg = f"Document {routed_doc.reference} ('{routed_doc.title}') successfully registered and sent for Director Review."

            # 3. Remove item from raw intake inbox
            if self.current_inbox_item_id:
                document_service.remove_inbox_item(self.current_inbox_item_id)
                self.current_inbox_item_id = None

            QMessageBox.information(self, "Intake Registered & Routed", msg)
            self.clear_form()
            self.document_processed.emit(routed_doc)

        except Exception as ex:
            QMessageBox.critical(self, "Intake Error", f"Failed to register and route document: {str(ex)}")

    def clear_form(self):
        self.title_input.clear()
        self.ref_input.clear()
        self.date_input.clear()
        self.source_input.clear()
        self.deadline_input.clear()
        self.extracted_ocr_text = ""
        self.selected_file = None
        self.current_inbox_item_id = None
        self.has_prior_director_remark = False
        self.ocr_status_frame.setVisible(False)
        self.director_remark_card.setVisible(False)
        self.bypass_director_check.setChecked(False)
        self.preview_label.setText("No document loaded\n\nSelect an incoming item from Inbox or click 'Manual Intake / Upload File' to process a document.")
        self.dept_combo.setCurrentIndex(0)
        self.emp_combo.setCurrentIndex(0)
        self.confidence_label.setText("Confidence: — • Source: Document / OCR")
        self._update_action_button_text()
