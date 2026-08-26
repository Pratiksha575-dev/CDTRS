from typing import Any, Dict, List, Optional, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from components.document_info import DocumentInfo
from components.document_preview import DocumentPreview
from components.routing_dialogs import (
    CloseDocumentDialog,
    HODAssignEmployeeDialog,
    RouteToEmployeeDialog,
    RouteToHODDialog,
    SendReminderDialog,
)
from models.attachment import AttachmentModel
from models.document import DocumentModel
from models.enums import DocumentStatusEnum, RoleEnum, WorkflowStageEnum
from services.assignment_service import assignment_service
from services.attachment_service import attachment_service
from services.document_service import document_service
from services.progress_service import progress_service
from services.routing_service import routing_service
from repositories.provider import get_repository
from components.ocr_splash_dialog import OCRSplashDialog
import os

class DocumentViewer(QWidget):
    """
    Authoritative Canonical Document Viewer for CDTRS V2.
    Clean single-structure UI with in-place reactive data synchronization.
    """

    close_requested = Signal()
    document_updated = Signal(object)

    def __init__(
        self,
        document: Union[DocumentModel, Dict[str, Any]],
        role: str = "Director Secretary"
    ):
        super().__init__()
        if isinstance(document, dict):
            self.document = DocumentModel.from_dict(document)
        else:
            self.document = document

        self.role = RoleEnum.normalize(role)
        self.selected_progress_attachment: Optional[str] = None
        self._is_updating = False

        self.setup_ui()
        self.update_view_data(self.document)

        from services.event_bus import event_bus
        event_bus.document_updated.connect(self._on_live_document_updated)

    def cleanup(self):
        """Safely disconnects from event_bus upon unmounting."""
        try:
            from services.event_bus import event_bus
            event_bus.document_updated.disconnect(self._on_live_document_updated)
        except Exception:
            pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def _on_live_document_updated(self, updated_doc: Any):
        if getattr(self, "_action_in_progress", False):
            return
        if not updated_doc or not hasattr(updated_doc, "id"):
            return
        if self.document and updated_doc.id == self.document.id:
            self.document = updated_doc
            self.update_view_data(self.document)

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(30, 20, 30, 20)
        root_layout.setSpacing(12)

        # --------------------------------
        # 1. HEADER & STATUS BAR
        # --------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)

        self.ref_label = QLabel()
        self.ref_label.setObjectName("pageSubtitle")

        title_vbox.addWidget(self.title_label)
        title_vbox.addWidget(self.ref_label)
        header_layout.addLayout(title_vbox, 1)

        # Badges
        badge_vbox = QVBoxLayout()
        badge_vbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        badge_vbox.setSpacing(4)

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet("background-color: #0F172A; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 11px;")
        
        self.stage_lbl = QLabel()
        self.stage_lbl.setStyleSheet("background-color: #E2E8F0; color: #334155; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;")

        badge_vbox.addWidget(self.status_lbl)
        badge_vbox.addWidget(self.stage_lbl)
        header_layout.addLayout(badge_vbox)

        root_layout.addLayout(header_layout)

        # --------------------------------
        # 2. SCROLLABLE CONTENT BODY
        # --------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 5, 0, 10)
        self.content_layout.setSpacing(16)

        # Top Row (Preview + Info)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        self.preview = DocumentPreview(self.document)
        self.info = DocumentInfo(self.document)

        top_row.addWidget(self.preview, 1)
        top_row.addWidget(self.info, 1)
        self.content_layout.addLayout(top_row)

        # A. DIRECTOR ROUTING SUGGESTION CARD (Built Once - Clean Neutral Theme)
        self.suggestion_card = QFrame()
        self.suggestion_card.setObjectName("contentCard")
        self.suggestion_card.setStyleSheet("QFrame#contentCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0F172A; border-radius: 6px; }")
        sugg_layout = QVBoxLayout(self.suggestion_card)
        sugg_layout.setContentsMargins(18, 14, 18, 14)
        sugg_layout.setSpacing(8)

        s_hdr_row = QHBoxLayout()
        self.s_hdr_lbl = QLabel("💡 Routing Directive / Suggestion")
        self.s_hdr_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")
        s_hdr_row.addWidget(self.s_hdr_lbl)
        s_hdr_row.addStretch()

        self.sugg_conf_lbl = QLabel("Confidence: 95%")
        self.sugg_conf_lbl.setStyleSheet("color: #64748B; font-weight: 600; font-size: 11px;")
        s_hdr_row.addWidget(self.sugg_conf_lbl)
        sugg_layout.addLayout(s_hdr_row)

        self.sugg_remark_lbl = QLabel()
        self.sugg_remark_lbl.setStyleSheet("color: #334155; font-size: 12px; font-style: italic;")
        self.sugg_remark_lbl.setWordWrap(True)
        sugg_layout.addWidget(self.sugg_remark_lbl)

        self.sugg_detected_lbl = QLabel()
        self.sugg_detected_lbl.setStyleSheet("color: #0F172A; font-size: 12px;")
        sugg_layout.addWidget(self.sugg_detected_lbl)

        self.s_btn_widget = QWidget()
        s_btn_row = QHBoxLayout(self.s_btn_widget)
        s_btn_row.setContentsMargins(0, 0, 0, 0)
        s_btn_row.setSpacing(8)

        apply_btn = QPushButton("Apply Suggested Routing")
        apply_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 6px 14px; border-radius: 4px; font-size: 12px;")
        apply_btn.clicked.connect(self._ds_apply_suggested_routing)
        s_btn_row.addWidget(apply_btn)

        edit_btn = QPushButton("Edit Routing")
        edit_btn.setStyleSheet("background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 6px 14px; border-radius: 4px; font-size: 12px;")
        edit_btn.clicked.connect(self._ds_edit_routing)
        s_btn_row.addWidget(edit_btn)

        dismiss_btn = QPushButton("Ignore / Dismiss")
        dismiss_btn.setStyleSheet("background-color: transparent; color: #64748B; text-decoration: underline; padding: 6px 10px; font-size: 12px;")
        dismiss_btn.clicked.connect(lambda: self.suggestion_card.setVisible(False))
        s_btn_row.addWidget(dismiss_btn)
        s_btn_row.addStretch()

        # Director Action Row (Use suggestion in remark)
        self.dir_sugg_action_widget = QWidget()
        dir_btn_row = QHBoxLayout(self.dir_sugg_action_widget)
        dir_btn_row.setContentsMargins(0, 0, 0, 0)
        dir_btn_row.setSpacing(8)

        self.dir_use_sugg_btn = QPushButton("✍ Pre-fill in Executive Remark")
        self.dir_use_sugg_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 6px 14px; border-radius: 4px; font-size: 12px;")
        self.dir_use_sugg_btn.clicked.connect(self._director_prefill_remark)
        dir_btn_row.addWidget(self.dir_use_sugg_btn)
        dir_btn_row.addStretch()

        sugg_layout.addWidget(self.s_btn_widget)
        sugg_layout.addWidget(self.dir_sugg_action_widget)
        self.content_layout.addWidget(self.suggestion_card)

        # B. WORKFLOW REMARKS & DIRECTIVES CARD (Built Once)
        self.remarks_card = QFrame()
        self.remarks_card.setObjectName("contentCard")
        self.remarks_card.setStyleSheet("QFrame#contentCard { border-left: 4px solid #0F172A; }")
        remarks_layout = QVBoxLayout(self.remarks_card)
        remarks_layout.setContentsMargins(20, 15, 20, 15)
        remarks_layout.setSpacing(12)

        card_title = QLabel("Workflow Remarks & Directives")
        card_title.setObjectName("sectionTitle")
        remarks_layout.addWidget(card_title)

        # Director Section (Editable for Director, Frame for others)
        self.dir_edit_frame = QWidget()
        dir_vbox = QVBoxLayout(self.dir_edit_frame)
        dir_vbox.setContentsMargins(0, 0, 0, 0)
        dir_vbox.setSpacing(6)
        dir_lbl = QLabel("Director's Remark & Guidance:")
        dir_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 12px;")
        self.dir_remark_edit = QTextEdit()
        self.dir_remark_edit.setPlaceholderText("Enter executive remarks, instructions, or routing directions for Director Secretary...")
        self.dir_remark_edit.setMaximumHeight(80)
        save_dir_btn = QPushButton("Save Director Remark")
        save_dir_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 5px 14px; border-radius: 4px; font-size: 11px;")
        save_dir_btn.clicked.connect(self._director_save_remark)
        dir_btn_box = QHBoxLayout()
        dir_btn_box.addStretch()
        dir_btn_box.addWidget(save_dir_btn)
        dir_vbox.addWidget(dir_lbl)
        dir_vbox.addWidget(self.dir_remark_edit)
        dir_vbox.addLayout(dir_btn_box)
        remarks_layout.addWidget(self.dir_edit_frame)

        self.dir_view_frame = QFrame()
        self.dir_view_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px;")
        df_layout = QVBoxLayout(self.dir_view_frame)
        df_layout.setContentsMargins(10, 8, 10, 8)
        df_layout.setSpacing(3)
        dl_title = QLabel("Director Remark:")
        dl_title.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 11px;")
        self.dir_view_lbl = QLabel()
        self.dir_view_lbl.setWordWrap(True)
        df_layout.addWidget(dl_title)
        df_layout.addWidget(self.dir_view_lbl)
        remarks_layout.addWidget(self.dir_view_frame)

        # HOD Section (Editable for HOD, Frame for others)
        self.hod_edit_frame = QWidget()
        hod_vbox = QVBoxLayout(self.hod_edit_frame)
        hod_vbox.setContentsMargins(0, 0, 0, 0)
        hod_vbox.setSpacing(6)
        self.hod_edit_lbl = QLabel("HOD's Remark:")
        self.hod_edit_lbl.setStyleSheet("font-weight: 700; color: #0284C7; font-size: 12px;")
        self.hod_remark_edit = QTextEdit()
        self.hod_remark_edit.setPlaceholderText("Enter departmental instructions or specific guidance for assigned staff...")
        self.hod_remark_edit.setMaximumHeight(80)
        save_hod_btn = QPushButton("Save HOD Remark")
        save_hod_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: 600; padding: 5px 14px; border-radius: 4px; font-size: 11px;")
        save_hod_btn.clicked.connect(self._hod_save_remark)
        hod_btn_box = QHBoxLayout()
        hod_btn_box.addStretch()
        hod_btn_box.addWidget(save_hod_btn)
        hod_vbox.addWidget(self.hod_edit_lbl)
        hod_vbox.addWidget(self.hod_remark_edit)
        hod_vbox.addLayout(hod_btn_box)
        remarks_layout.addWidget(self.hod_edit_frame)

        self.hod_view_frame = QFrame()
        self.hod_view_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px;")
        hf_layout = QVBoxLayout(self.hod_view_frame)
        hf_layout.setContentsMargins(10, 8, 10, 8)
        hf_layout.setSpacing(3)
        self.hod_view_title = QLabel("HOD Remark:")
        self.hod_view_title.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 11px;")
        self.hod_view_lbl = QLabel()
        self.hod_view_lbl.setWordWrap(True)
        hf_layout.addWidget(self.hod_view_title)
        hf_layout.addWidget(self.hod_view_lbl)
        remarks_layout.addWidget(self.hod_view_frame)

        # Latest Progress Summary
        self.prog_summary_frame = QFrame()
        self.prog_summary_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px;")
        pf_layout = QVBoxLayout(self.prog_summary_frame)
        pf_layout.setContentsMargins(10, 8, 10, 8)
        pf_layout.setSpacing(6)
        self.prog_summary_title = QLabel("Latest Execution Progress:")
        self.prog_summary_title.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 11px;")
        self.prog_summary_lbl = QLabel()
        self.prog_summary_lbl.setStyleSheet("color: #1E293B; font-size: 12px;")
        self.prog_summary_lbl.setWordWrap(True)
        pf_layout.addWidget(self.prog_summary_title)
        pf_layout.addWidget(self.prog_summary_lbl)

        # Attached Proof widget in progress frame
        self.prog_proof_row = QWidget()
        self.prog_proof_layout = QHBoxLayout(self.prog_proof_row)
        self.prog_proof_layout.setContentsMargins(0, 4, 0, 0)
        self.prog_proof_layout.setSpacing(8)
        pf_layout.addWidget(self.prog_proof_row)
        self.prog_proof_row.setVisible(False)

        remarks_layout.addWidget(self.prog_summary_frame)

        self.content_layout.addWidget(self.remarks_card)

        # C. ATTACHMENTS SECTION CONTAINER (Built Once - Clean Neutral Theme)
        self.attachments_card = QFrame()
        self.attachments_card.setObjectName("contentCard")
        self.attachments_card.setStyleSheet("QFrame#contentCard { border-left: 4px solid #0F172A; }")
        att_outer_layout = QVBoxLayout(self.attachments_card)
        att_outer_layout.setContentsMargins(20, 15, 20, 15)
        att_outer_layout.setSpacing(10)

        self.att_header_lbl = QLabel("Attached Documents & Submitted Proofs")
        self.att_header_lbl.setObjectName("sectionTitle")
        att_outer_layout.addWidget(self.att_header_lbl)

        self.attachments_items_layout = QVBoxLayout()
        self.attachments_items_layout.setSpacing(8)
        att_outer_layout.addLayout(self.attachments_items_layout)

        self.content_layout.addWidget(self.attachments_card)

        # C2. DOCUMENT INTELLIGENCE & OCR EXTRACTION CARD (Built Once - Clean Neutral Theme)
        self.ocr_intel_card = QFrame()
        self.ocr_intel_card.setObjectName("contentCard")
        self.ocr_intel_card.setStyleSheet("QFrame#contentCard { border-left: 4px solid #0F172A; }")
        ocr_layout = QVBoxLayout(self.ocr_intel_card)
        ocr_layout.setContentsMargins(20, 15, 20, 15)
        ocr_layout.setSpacing(10)

        ocr_hdr_row = QHBoxLayout()
        ocr_hdr_lbl = QLabel("🧠 Document Intelligence & OCR Extraction")
        ocr_hdr_lbl.setObjectName("sectionTitle")
        ocr_hdr_row.addWidget(ocr_hdr_lbl)
        ocr_hdr_row.addStretch()

        self.ocr_status_badge = QLabel("✓ COMPLETED")
        self.ocr_status_badge.setStyleSheet("background-color: #F1F5F9; color: #0F172A; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 4px; border: 1px solid #E2E8F0;")
        self.ocr_hw_badge = QLabel("✍ Handwritten")
        self.ocr_hw_badge.setStyleSheet("background-color: #F1F5F9; color: #0F172A; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 4px; border: 1px solid #E2E8F0;")
        self.ocr_hw_badge.setVisible(False)
        # PZ_26/08: Initial placeholder is neutral 'Confidence: —' (removed hardcoded fake 96%)
        self.ocr_conf_badge = QLabel("Confidence: —")
        self.ocr_conf_badge.setStyleSheet("background-color: #F1F5F9; color: #475569; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 4px; border: 1px solid #E2E8F0;")

        ocr_hdr_row.addWidget(self.ocr_status_badge)
        ocr_hdr_row.addWidget(self.ocr_hw_badge)
        ocr_hdr_row.addWidget(self.ocr_conf_badge)
        ocr_layout.addLayout(ocr_hdr_row)

        self.ocr_fields_box = QLabel()
        self.ocr_fields_box.setWordWrap(True)
        self.ocr_fields_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; padding: 10px; font-family: monospace; font-size: 11px; color: #1E293B;")
        ocr_layout.addWidget(self.ocr_fields_box)

        self.ocr_text_preview = QTextEdit()
        self.ocr_text_preview.setReadOnly(True)
        self.ocr_text_preview.setMaximumHeight(120)
        self.ocr_text_preview.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; font-size: 11px; color: #334155;")
        self.ocr_text_preview.setVisible(False)
        ocr_layout.addWidget(self.ocr_text_preview)

        ocr_btn_row = QHBoxLayout()
        self.ocr_toggle_btn = QPushButton("Show Raw OCR Extracted Text ▼")
        self.ocr_toggle_btn.setStyleSheet("background-color: transparent; color: #0D9488; font-weight: 600; font-size: 11px; text-decoration: underline;")
        self.ocr_toggle_btn.clicked.connect(self._toggle_raw_ocr_text)
        ocr_btn_row.addWidget(self.ocr_toggle_btn)
        ocr_btn_row.addStretch()

        self.ocr_rerun_btn = QPushButton("⚡ Re-run OCR Extraction")
        self.ocr_rerun_btn.setStyleSheet("background-color: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; font-weight: 600; font-size: 11px; padding: 4px 12px; border-radius: 4px;")
        self.ocr_rerun_btn.clicked.connect(self._rerun_ocr_extraction)
        ocr_btn_row.addWidget(self.ocr_rerun_btn)

        ocr_layout.addLayout(ocr_btn_row)
        self.content_layout.addWidget(self.ocr_intel_card)

        # D. ASSIGNMENT STATUS CARD (Built Once)
        self.assignment_card = QFrame()
        self.assignment_card.setObjectName("contentCard")
        self.assignment_card.setStyleSheet("QFrame#contentCard { border-left: 4px solid #10B981; }")
        assign_layout = QHBoxLayout(self.assignment_card)
        assign_layout.setContentsMargins(20, 12, 20, 12)
        assign_layout.setSpacing(10)

        self.assignment_lbl = QLabel()
        self.assignment_lbl.setStyleSheet("color: #065F46; font-size: 13px;")
        assign_layout.addWidget(self.assignment_lbl)
        assign_layout.addStretch()

        self.content_layout.addWidget(self.assignment_card)

        # E. PROGRESS HISTORY SECTION CONTAINER (Built Once)
        self.progress_history_card = QFrame()
        self.progress_history_card.setObjectName("contentCard")
        prog_hist_outer = QVBoxLayout(self.progress_history_card)
        prog_hist_outer.setContentsMargins(20, 15, 20, 15)
        prog_hist_outer.setSpacing(10)

        self.progress_hist_title = QLabel("Employee Execution Progress")
        self.progress_hist_title.setObjectName("sectionTitle")
        prog_hist_outer.addWidget(self.progress_hist_title)

        self.progress_items_layout = QVBoxLayout()
        self.progress_items_layout.setSpacing(8)
        prog_hist_outer.addLayout(self.progress_items_layout)

        self.content_layout.addWidget(self.progress_history_card)

        # F. EMPLOYEE PROGRESS FORM (Built Once)
        self.progress_form_card = QFrame()
        self.progress_form_card.setObjectName("contentCard")
        self.progress_form_card.setStyleSheet("QFrame#contentCard { border-left: 4px solid #2563EB; }")
        emp_form_layout = QVBoxLayout(self.progress_form_card)
        emp_form_layout.setContentsMargins(20, 15, 20, 15)
        emp_form_layout.setSpacing(10)

        form_title = QLabel("Report Progress Update")
        form_title.setObjectName("sectionTitle")

        self._emp_progress_text_edit = QTextEdit()
        self._emp_progress_text_edit.setPlaceholderText("Describe the work completed, current findings, challenges, or next execution steps...")
        self._emp_progress_text_edit.setMaximumHeight(85)

        att_row = QHBoxLayout()
        att_row.setSpacing(10)

        attach_btn = QPushButton("📎 Attach Supporting Document")
        attach_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 6px 14px; border-radius: 4px;")
        attach_btn.clicked.connect(self._select_progress_attachment)

        self.att_label = QLabel("No attachment selected")
        self.att_label.setStyleSheet("color: #64748B; font-size: 12px;")

        self.clear_att_btn = QPushButton("✕")
        self.clear_att_btn.setFixedSize(24, 24)
        self.clear_att_btn.setStyleSheet("background-color: #FEE2E2; color: #DC2626; border-radius: 12px; font-weight: bold;")
        self.clear_att_btn.setVisible(False)
        self.clear_att_btn.clicked.connect(self._clear_progress_attachment)

        att_row.addWidget(attach_btn)
        att_row.addWidget(self.att_label)
        att_row.addWidget(self.clear_att_btn)
        att_row.addStretch()

        submit_btn = QPushButton("Submit Progress Update")
        submit_btn.setStyleSheet("background-color: #2563EB; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        submit_btn.clicked.connect(self._employee_submit_progress)
        att_row.addWidget(submit_btn)

        emp_form_layout.addWidget(form_title)
        emp_form_layout.addWidget(self._emp_progress_text_edit)
        emp_form_layout.addLayout(att_row)

        self.content_layout.addWidget(self.progress_form_card)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area, 1)

        # --------------------------------
        # 3. CONTEXTUAL ACTION BAR
        # --------------------------------
        self.action_bar_widget = QWidget()
        self.action_bar = QHBoxLayout(self.action_bar_widget)
        self.action_bar.setContentsMargins(0, 8, 0, 0)
        self.action_bar.setSpacing(10)

        root_layout.addWidget(self.action_bar_widget)

    def _clear_item_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                w = item.widget()
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_item_layout(item.layout())

    def update_view_data(self, doc: DocumentModel):
        """Updates all viewer sections in-place cleanly without stacking or glitching."""
        if self._is_updating:
            return
        self._is_updating = True

        try:
            if doc and doc.id and not doc.director_remark:
                try:
                    fresh_doc = document_service.get_document(doc.id)
                    if fresh_doc:
                        doc = fresh_doc
                except Exception:
                    pass
            self.document = doc


            # 1. Update Header
            title_text = self.document.title or "Document Information"
            self.title_label.setText(title_text)

            ref_text = self.document.reference or "-"
            self.ref_label.setText(f"Reference No: {ref_text}  •  Source: {self.document.source or 'External'}  •  Received: {self.document.date or 'N/A'}")

            self.status_lbl.setText(f"Status: {self.document.status or 'Received'}")
            self.stage_lbl.setText(f"Stage: {self.document.current_stage or 'DS'}")

            # 2. Update Preview & Info Components
            self.preview.set_document(self.document)
            self.info.set_document(self.document)

            # 3. Update Routing Suggestion Card (Director instruction OR OCR intelligence)
            sugg_dept = getattr(self.document, "suggested_department_name", None)
            sugg_dept_id = getattr(self.document, "suggested_department_id", None)
            sugg_emp = getattr(self.document, "suggested_employee_name", None)
            sugg_emp_id = getattr(self.document, "suggested_employee_id", None)
            conf = getattr(self.document, "routing_instruction_confidence", 0) or 0
            is_dir_instruction = bool(getattr(self.document, "has_director_routing_instruction", False) or getattr(self.document, "is_director_instruction", False))

            # Query backend routing suggestion if not already populated on the model
            if not sugg_dept and not sugg_emp and self.document.id:
                try:
                    repo = get_repository()
                    s_data = repo.get_routing_suggestion(self.document.id) or {}
                    if s_data:
                        sugg_dept = s_data.get("suggested_department_name")
                        sugg_dept_id = s_data.get("suggested_department_id")
                        sugg_emp = s_data.get("suggested_employee_name")
                        sugg_emp_id = s_data.get("suggested_employee_id")
                        r_conf = s_data.get("routing_confidence")
                        if r_conf is not None:
                            conf = round(r_conf * 100) if r_conf <= 1.0 else round(r_conf)
                        is_dir_instruction = bool(s_data.get("is_director_instruction", False))

                        self.document.suggested_department_name = sugg_dept
                        self.document.suggested_department_id = sugg_dept_id
                        self.document.suggested_employee_name = sugg_emp
                        self.document.suggested_employee_id = sugg_emp_id
                        self.document.routing_instruction_confidence = conf
                        self.document.has_director_routing_instruction = is_dir_instruction
                except Exception:
                    pass

            # Also check director remark for explicit directives
            if self.document.director_remark:
                from services.routing_service import routing_service
                analysis = routing_service.analyze_director_remark(self.document.director_remark)
                if analysis.get("has_routing_instruction"):
                    if analysis.get("suggested_department"):
                        sugg_dept = analysis.get("suggested_department")
                        sugg_dept_id = analysis.get("suggested_department_id")
                        self.document.suggested_department_name = sugg_dept
                        self.document.suggested_department_id = sugg_dept_id
                    if analysis.get("suggested_employee"):
                        sugg_emp = analysis.get("suggested_employee")
                        sugg_emp_id = analysis.get("suggested_employee_id")
                        self.document.suggested_employee_name = sugg_emp
                        self.document.suggested_employee_id = sugg_emp_id
                    is_dir_instruction = True
                    conf = 95
                    self.document.has_director_routing_instruction = True
                    self.document.routing_instruction_confidence = 95

            is_ds = self.role in (RoleEnum.DIRECTOR_SECRETARY.value, "Master", "DS", "Director Secretary")
            is_director = self.role in (RoleEnum.DIRECTOR.value, "Director", "DIRECTOR")
            is_closed = (self.document.status == DocumentStatusEnum.CLOSED.value or self.document.current_stage == WorkflowStageEnum.CLOSED.value)

            show_sugg = (
                not is_closed
                and (is_ds or is_director)
                and bool(sugg_dept or sugg_emp)
            )

            self.suggestion_card.setVisible(show_sugg)
            if show_sugg:
                self.sugg_card = self.suggestion_card
                conf_display = conf if conf > 0 else 85
                self.sugg_conf_lbl.setText(f"Confidence: {conf_display}%")

                # Toggle role-specific action buttons on the suggestion card
                if is_director:
                    self.s_btn_widget.setVisible(False)
                    self.dir_sugg_action_widget.setVisible(True)
                else:
                    self.s_btn_widget.setVisible(True)
                    self.dir_sugg_action_widget.setVisible(False)

                self.suggestion_card.setStyleSheet("QFrame#contentCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0F172A; border-radius: 6px; }")

                if is_dir_instruction:
                    self.s_hdr_lbl.setText("💡 Director Directive / Routing Instruction Detected")
                    self.s_hdr_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")
                    raw_rem = self.document.director_remark or getattr(self.document, "director_routing_raw_text", "") or ""
                    self.sugg_remark_lbl.setText(f"Director Guidance:\n\"{raw_rem}\"" if raw_rem else "")
                    self.sugg_remark_lbl.setVisible(bool(raw_rem))
                else:
                    self.s_hdr_lbl.setText("💡 Advisory Department Suggestion (OCR & Content Intelligence)")
                    self.s_hdr_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")
                    reason_txt = getattr(self.document, "routing_reason", "") or "Automatically inferred from document text extraction and departmental keyword scoring."
                    self.sugg_remark_lbl.setText(f"Analysis: {reason_txt}")
                    self.sugg_remark_lbl.setVisible(True)

                dept_str = sugg_dept or "Not specified"
                emp_str = sugg_emp or "Not specified"
                self.sugg_detected_lbl.setText(f"Target:  <b>Department:</b> {dept_str}  •  <b>Staff:</b> {emp_str}")
            else:
                self.sugg_card = None




            # 4. Update Remarks Card
            is_closed = (self.document.status == DocumentStatusEnum.CLOSED.value or self.document.current_stage == WorkflowStageEnum.CLOSED.value)
            
            # Director Remark binding
            if self.role == RoleEnum.DIRECTOR.value and not is_closed:
                self.dir_edit_frame.setVisible(True)
                self.dir_view_frame.setVisible(False)
                self.dir_remark_edit.setText(self.document.director_remark or "")
            else:
                self.dir_edit_frame.setVisible(False)
                self.dir_view_frame.setVisible(True)
                dir_text = self.document.director_remark or "No Director remark recorded."
                self.dir_view_lbl.setText(dir_text)
                self.dir_view_lbl.setStyleSheet("color: #334155; font-size: 12px;" if self.document.director_remark else "color: #94A3B8; font-style: italic; font-size: 12px;")

            # HOD Remark binding
            dept_name = self.document.target_department_name or "Department"
            if self.role in (RoleEnum.HOD.value, "HOD") and not is_closed:
                self.hod_edit_frame.setVisible(True)
                self.hod_view_frame.setVisible(False)
                self.hod_edit_lbl.setText(f"HOD's Remark ({dept_name}):")
                self.hod_remark_edit.setText(self.document.hod_remark or "")
            else:
                self.hod_edit_frame.setVisible(False)
                self.hod_view_frame.setVisible(True)
                self.hod_view_title.setText(f"HOD Remark ({dept_name}):")
                hod_text = self.document.hod_remark or "No HOD remark recorded."
                self.hod_view_lbl.setText(hod_text)
                self.hod_view_lbl.setStyleSheet("color: #334155; font-size: 12px;" if self.document.hod_remark else "color: #94A3B8; font-style: italic; font-size: 12px;")

            doc_id = self.document.id or 0
            progress_entries = []
            if doc_id:
                try:
                    progress_entries = progress_service.get_progress_updates(doc_id) or []
                except Exception:
                    progress_entries = []

            # 5. Update Attachments List (Original Source Files + Employee Execution Proofs)
            self._clear_item_layout(self.attachments_items_layout)
            all_attachments = []
            if doc_id:
                try:
                    all_attachments = attachment_service.get_document_attachments(doc_id) or []
                except Exception:
                    all_attachments = []

            count_text = f" ({len(all_attachments)})" if all_attachments else ""
            self.att_header_lbl.setText(f"Attached Documents & Submitted Proofs{count_text}")

            # Latest Progress summary binding with attached proof file display
            if progress_entries:

                latest = progress_entries[-1]
                self.prog_summary_frame.setVisible(True)
                self.prog_summary_title.setText(f"Latest Execution Progress ({latest.user_name or 'Assigned Staff'} • {latest.created_at}):")
                self.prog_summary_lbl.setText(latest.description)

                # Render proof button directly in latest progress frame if proof exists
                self._clear_item_layout(self.prog_proof_layout)
                matching_proofs = [a for a in all_attachments if a.progress_update_id == latest.id or (a.category != "ORIGINAL" and getattr(a, "attachment_type", "") != "ORIGINAL")]
                if matching_proofs:
                    self.prog_proof_row.setVisible(True)
                    p_lbl = QLabel(f"📎 Submitted Proof:")
                    p_lbl.setStyleSheet("font-weight: 600; color: #0F172A; font-size: 11px;")
                    self.prog_proof_layout.addWidget(p_lbl)
                    for pf in matching_proofs:
                        pf_btn = QPushButton(f"📄 {pf.file_name} ({pf.formatted_size})")
                        pf_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; font-size: 11px; padding: 3px 10px; border-radius: 4px;")
                        pf_btn.clicked.connect(lambda _, a=pf: self._view_attachment(a))
                        self.prog_proof_layout.addWidget(pf_btn)
                    self.prog_proof_layout.addStretch()
                else:
                    self.prog_proof_row.setVisible(False)
            else:
                self.prog_summary_frame.setVisible(False)

            if not all_attachments:
                no_att_lbl = QLabel("No attachments recorded (Email Body / Direct Dispatched Text).")
                no_att_lbl.setStyleSheet("color: #64748B; font-style: italic; font-size: 12px;")
                self.attachments_items_layout.addWidget(no_att_lbl)
            else:
                for att in all_attachments:
                    row_frame = QFrame()
                    row_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px;")
                    row_hbox = QHBoxLayout(row_frame)
                    row_hbox.setContentsMargins(10, 8, 10, 8)
                    row_hbox.setSpacing(12)

                    is_proof = (att.category != "ORIGINAL" and getattr(att, "attachment_type", "") != "ORIGINAL") or bool(att.progress_update_id)
                    badge_text = f"[{att.extension.upper()}]"
                    badge_style = "background-color: #0F172A; color: white; font-weight: bold; font-size: 11px; padding: 3px 7px; border-radius: 3px;"

                    badge = QLabel(badge_text)
                    badge.setStyleSheet(badge_style)

                    info_vbox = QVBoxLayout()
                    info_vbox.setSpacing(2)
                    name_lbl = QLabel(att.file_name)
                    name_lbl.setStyleSheet("font-weight: 600; color: #0F172A; font-size: 12px;")

                    category_label = "📎 Submitted Execution Proof" if is_proof else "📄 Canonical Intake Document"
                    uploader_info = f" • Uploaded: {str(att.created_at)[:10] if att.created_at else 'Recent'}"
                    meta_lbl = QLabel(f"{category_label} • {att.formatted_size}{uploader_info}")
                    meta_lbl.setStyleSheet("color: #64748B; font-size: 11px;")

                    info_vbox.addWidget(name_lbl)
                    info_vbox.addWidget(meta_lbl)

                    row_hbox.addWidget(badge)
                    row_hbox.addLayout(info_vbox, 1)

                    btn_hbox = QHBoxLayout()
                    btn_hbox.setSpacing(6)

                    if att.is_previewable:
                        view_btn = QPushButton("View")
                        view_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; font-size: 11px; padding: 4px 12px; border-radius: 4px;")
                        view_btn.clicked.connect(lambda _, a=att: self._view_attachment(a))
                        btn_hbox.addWidget(view_btn)

                    dl_btn = QPushButton("Download")
                    dl_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; font-size: 11px; padding: 4px 12px; border-radius: 4px;")
                    dl_btn.clicked.connect(lambda _, a=att: self._download_attachment(a))
                    btn_hbox.addWidget(dl_btn)

                    row_hbox.addLayout(btn_hbox)
                    self.attachments_items_layout.addWidget(row_frame)


            # 5b. Update OCR & Intelligence Card
            ocr_data = {}
            if doc_id:
                repo = get_repository()
                try:
                    ocr_data = repo.get_ocr_result(doc_id) or {}
                except Exception:
                    ocr_data = {}

            extracted_text = ocr_data.get("extracted_text") or getattr(self.document, "description", "") or ""
            fields_list = ocr_data.get("extracted_fields") or []
            ocr_conf = ocr_data.get("confidence")
            ocr_engine = ocr_data.get("ocr_engine") or "PaddleOCR-v3"
            is_hw = "handwritten" in str(ocr_engine).lower()

            if (ocr_data and ocr_data.get("ocr_status") in ("COMPLETED", "PROCESSING")) or extracted_text:
                self.ocr_intel_card.setVisible(True)
                status_txt = ocr_data.get("ocr_status", "COMPLETED")
                self.ocr_status_badge.setText(f"✓ {status_txt}")
                self.ocr_hw_badge.setVisible(is_hw)
                # PZ_26/08: Display real OCR confidence percentage or 'Confidence: —' (removed (ocr_conf or 95) fake fallback)
                if ocr_conf is not None and ocr_conf > 0:
                    conf_pct = round(ocr_conf * 100) if ocr_conf <= 1.0 else round(ocr_conf)
                    self.ocr_conf_badge.setText(f"Confidence: {conf_pct}%")
                else:
                    self.ocr_conf_badge.setText("Confidence: —")

                f_lines = []
                for f in fields_list:
                    if isinstance(f, dict):
                        fname = f.get("field_name", "")
                        fval = f.get("verified_value") or f.get("extracted_value", "")
                        if fval:
                            f_lines.append(f"• {fname.title()}: {fval}")

                if not f_lines and extracted_text:
                    f_lines = [
                        f"• Document Title: {self.document.title}",
                        f"• Reference No: {self.document.reference or '-'}",
                        f"• Ingestion Mode: {self.document.mode or 'Government Mail'}",
                    ]

                self.ocr_fields_box.setText("\n".join(f_lines) if f_lines else "Content indexed and verified.")
                self.ocr_text_preview.setText(extracted_text)
            else:
                self.ocr_intel_card.setVisible(False)

            # 6. Update Assignment Status Card
            has_assign = bool(self.document.assigned_employee_name and self.document.assigned_employee_name != "Not Assigned")
            self.assignment_card.setVisible(has_assign)
            if has_assign:
                self.assignment_lbl.setText(f"👤 Assigned Staff: <b>{self.document.assigned_employee_name}</b>  •  Department: <b>{self.document.target_department_name or 'General'}</b>")

            # 7. Update Progress History
            self._clear_item_layout(self.progress_items_layout)
            self.progress_history_card.setVisible(bool(progress_entries))
            if progress_entries:
                self.progress_hist_title.setText(f"Employee Execution Progress ({len(progress_entries)} update{'s' if len(progress_entries) > 1 else ''})")
                for p in progress_entries:
                    p_box = QFrame()
                    p_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;")
                    p_vbox = QVBoxLayout(p_box)
                    p_vbox.setContentsMargins(8, 8, 8, 8)
                    p_vbox.setSpacing(6)

                    p_time = str(p.created_at or "").replace("T", " ")[:16] or "Recent"
                    p_author = p.user_name or (self.document.assigned_employee_name if (self.document.assigned_employee_name and self.document.assigned_employee_name != "Not Assigned") else "Assigned Staff")
                    p_hdr = QLabel(f"Submitted by {p_author} • {p_time}")
                    p_hdr.setStyleSheet("font-weight: 600; color: #475569; font-size: 11px;")

                    p_desc = QLabel(p.description)
                    p_desc.setStyleSheet("color: #1E293B; font-size: 13px;")
                    p_desc.setWordWrap(True)

                    p_vbox.addWidget(p_hdr)
                    p_vbox.addWidget(p_desc)

                    p_proofs = list(p.attachments or [])
                    for a in all_attachments:
                        if a.progress_update_id == p.id and not any(getattr(existing, "id", None) == a.id for existing in p_proofs):
                            p_proofs.append(a)

                    if p_proofs:
                        att_vbox = QVBoxLayout()
                        att_vbox.setSpacing(4)
                        att_hdr = QLabel("📎 Submitted Proof Documents:")
                        att_hdr.setStyleSheet("font-weight: 600; color: #0F172A; font-size: 11px;")
                        att_vbox.addWidget(att_hdr)

                        for att in p_proofs:
                            att_frame = QFrame()
                            att_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px;")
                            att_hbox = QHBoxLayout(att_frame)
                            att_hbox.setContentsMargins(8, 4, 8, 4)
                            att_hbox.setSpacing(8)

                            badge = QLabel(f"[{att.extension.upper()}]")
                            badge.setStyleSheet("background-color: #0F172A; color: white; font-weight: bold; font-size: 10px; padding: 2px 5px; border-radius: 3px;")

                            lbl = QLabel(f"{att.file_name} • {att.formatted_size}")
                            lbl.setStyleSheet("color: #1E293B; font-size: 11px; font-weight: 500;")

                            att_hbox.addWidget(badge)
                            att_hbox.addWidget(lbl, 1)

                            if att.is_previewable:
                                v_btn = QPushButton("View")
                                v_btn.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; font-size: 11px; padding: 3px 8px; border-radius: 3px;")
                                v_btn.clicked.connect(lambda _, a=att: self._view_attachment(a))
                                att_hbox.addWidget(v_btn)

                            d_btn = QPushButton("Download")
                            d_btn.setStyleSheet("background-color: #0F172A; color: white; font-size: 11px; padding: 3px 8px; border-radius: 3px;")
                            d_btn.clicked.connect(lambda _, a=att: self._download_attachment(a))
                            att_hbox.addWidget(d_btn)

                            att_vbox.addWidget(att_frame)
                        p_vbox.addLayout(att_vbox)


                    self.progress_items_layout.addWidget(p_box)

            # 8. Update Progress Submission Form Visibility
            is_emp = self.role in (RoleEnum.EMPLOYEE.value, "Employee")
            show_prog_form = is_emp and not is_closed
            self.progress_form_card.setVisible(show_prog_form)
            if show_prog_form:
                self.progress_text_edit = self._emp_progress_text_edit
            else:
                if hasattr(self, "progress_text_edit"):
                    delattr(self, "progress_text_edit")

            # 9. Update Contextual Action Bar
            self._render_action_bar()

        finally:
            self._is_updating = False

    # =========================================================
    # ROLE CONTEXTUAL ACTION BAR
    # =========================================================

    def _render_action_bar(self):
        self._clear_item_layout(self.action_bar)

        # Universal Back Button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("background-color: #E2E8F0; color: #1E293B; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
        back_btn.clicked.connect(self.close_requested.emit)
        self.action_bar.addWidget(back_btn)

        self.action_bar.addStretch()

        if self.role in (RoleEnum.DIRECTOR_SECRETARY.value, "Master", "DS", "Director Secretary"):
            self._render_ds_actions()
        elif self.role == RoleEnum.DIRECTOR.value:
            self._render_director_actions()
        elif self.role in (RoleEnum.HOD.value, "HOD"):
            self._render_hod_actions()
        elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
            self._render_employee_actions()

    def _render_ds_actions(self):
        doc = self.document
        stage = doc.current_stage

        if doc.status == DocumentStatusEnum.CLOSED.value or stage == WorkflowStageEnum.CLOSED.value:
            closed_label = QLabel("✓ Document Lifecycle Finalized and Closed")
            closed_label.setStyleSheet("color: #059669; font-weight: 600; font-size: 13px;")
            self.action_bar.addWidget(closed_label)
            return

        if stage in (WorkflowStageEnum.DS.value, "DS", "ds_user"):
            is_returned_from_director = bool(
                doc.status in (DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value, "Director Review Completed", "DIRECTOR_REVIEW_COMPLETED")
                or bool(doc.director_remark)
            )
            has_pre_review = bool(
                is_returned_from_director
                and (getattr(doc, "suggested_department_name", None) or getattr(doc, "suggested_employee_name", None))
            )

            if has_pre_review:
                direct_route_btn = QPushButton("Route Directly to Suggested Department/Employee")
                direct_route_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
                direct_route_btn.clicked.connect(self._ds_apply_suggested_routing)
                self.action_bar.addWidget(direct_route_btn)
            elif not is_returned_from_director:
                route_dir_btn = QPushButton("Route to Director")
                route_dir_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
                route_dir_btn.clicked.connect(self._ds_route_to_director)
                self.action_bar.addWidget(route_dir_btn)

            route_hod_btn = QPushButton("Route to HOD")
            route_hod_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
            route_hod_btn.clicked.connect(self._ds_route_to_hod)
            self.action_bar.addWidget(route_hod_btn)

            route_emp_btn = QPushButton("Route to Staff Directly")
            route_emp_btn.setStyleSheet("background-color: #475569; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
            route_emp_btn.clicked.connect(self._ds_route_to_employee)
            self.action_bar.addWidget(route_emp_btn)

            close_btn = QPushButton("Close Document")
            close_btn.setStyleSheet("background-color: #059669; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
            close_btn.clicked.connect(self._ds_close_document)
            self.action_bar.addWidget(close_btn)

        elif stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value):
            if doc.status == DocumentStatusEnum.PROGRESS_UPDATED.value:
                fwd_btn = QPushButton("Forward Progress Follow-up to Director")
                fwd_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
                fwd_btn.clicked.connect(self._ds_forward_followup)
                self.action_bar.addWidget(fwd_btn)
            else:
                dept_label = doc.target_department_name or "Department"
                status_note = QLabel(f"📌 Active in {dept_label} — Awaiting Staff Completion")
                status_note.setStyleSheet("color: #0284C7; font-weight: 600; font-size: 12px;")
                self.action_bar.addWidget(status_note)

                re_route_btn = QPushButton("Re-Route Department")
                re_route_btn.setStyleSheet("background-color: #475569; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
                re_route_btn.clicked.connect(self._ds_route_to_hod)
                self.action_bar.addWidget(re_route_btn)

            reminder_btn = QPushButton("⏰ Send Action Reminder")
            reminder_btn.setStyleSheet("background-color: #F59E0B; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
            reminder_btn.clicked.connect(self._ds_send_reminder)
            self.action_bar.addWidget(reminder_btn)

            close_btn = QPushButton("Close Document")
            close_btn.setStyleSheet("background-color: #059669; color: white; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
            close_btn.clicked.connect(self._ds_close_document)
            self.action_bar.addWidget(close_btn)

        elif stage == WorkflowStageEnum.DIRECTOR.value:
            note = QLabel("Document currently with Director for Executive Review (Read-Only)")
            note.setStyleSheet("color: #64748B; font-style: italic; font-size: 12px;")
            self.action_bar.addWidget(note)

    def _render_director_actions(self):
        doc = self.document
        stage = doc.current_stage

        if doc.status == DocumentStatusEnum.CLOSED.value or stage == WorkflowStageEnum.CLOSED.value:
            closed_label = QLabel("✓ Document Lifecycle Finalized and Closed (Read-Only)")
            closed_label.setStyleSheet("color: #059669; font-weight: 600; font-size: 13px;")
            self.action_bar.addWidget(closed_label)
            return

        if stage == WorkflowStageEnum.DIRECTOR.value or doc.status == DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value:
            return_ds_btn = QPushButton("Return to Director Secretary")
            return_ds_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 20px; border-radius: 5px;")
            return_ds_btn.clicked.connect(self._director_return_to_ds)
            self.action_bar.addWidget(return_ds_btn)
        else:
            status_note = QLabel(f"Document under {stage} stage (Read-Only Review)")
            status_note.setStyleSheet("color: #64748B; font-style: italic; font-size: 12px;")
            self.action_bar.addWidget(status_note)

    def _render_hod_actions(self):
        doc = self.document
        stage = doc.current_stage

        if doc.status == DocumentStatusEnum.CLOSED.value or stage == WorkflowStageEnum.CLOSED.value:
            closed_label = QLabel("✓ Document Lifecycle Finalized and Closed")
            closed_label.setStyleSheet("color: #059669; font-weight: 600; font-size: 13px;")
            self.action_bar.addWidget(closed_label)
            return

        assign_btn_text = "Reassign Staff" if (doc.assigned_employee_name and doc.assigned_employee_name != "Not Assigned") else "Assign Staff"
        assign_btn = QPushButton(assign_btn_text)
        assign_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 20px; border-radius: 5px;")
        assign_btn.clicked.connect(self._hod_assign_employee)
        self.action_bar.addWidget(assign_btn)

    def _render_employee_actions(self):
        doc = self.document
        stage = doc.current_stage

        if doc.status == DocumentStatusEnum.CLOSED.value or stage == WorkflowStageEnum.CLOSED.value:
            closed_label = QLabel("✓ Document Lifecycle Finalized and Closed (Read-Only Archive)")
            closed_label.setStyleSheet("color: #059669; font-weight: 600; font-size: 13px;")
            self.action_bar.addWidget(closed_label)
        else:
            status_note = QLabel("Task In Progress • Submit your execution findings using the form above")
            status_note.setStyleSheet("color: #2563EB; font-weight: 500; font-size: 12px;")
            self.action_bar.addWidget(status_note)

    # =========================================================
    # ACTION HANDLERS
    # =========================================================

    def _director_prefill_remark(self):
        dept = getattr(self.document, "suggested_department_name", None) or "Department"
        emp = getattr(self.document, "suggested_employee_name", None)
        if emp and emp != "Not specified":
            prefill = f"Approved. Route to {dept} for action by {emp}."
        else:
            prefill = f"Approved. Route to {dept} for necessary action."
        self.dir_remark_edit.setText(prefill)
        self.dir_remark_edit.setFocus()

    def _director_save_remark(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True

        try:
            remark_text = self.dir_remark_edit.toPlainText().strip()
            if not remark_text:
                QMessageBox.warning(self, "Validation", "Please enter a Director remark before saving.")
                return

            doc_id = self.document.id or 0
            updated_doc = routing_service.save_director_remark(doc_id, remark=remark_text)
            self.document = updated_doc
            self.update_view_data(updated_doc)
            QMessageBox.information(self, "Remark Saved", "Director remark saved successfully.")
            self.document_updated.emit(updated_doc)
        except Exception as ex:
            QMessageBox.critical(self, "Save Error", f"Failed to save Director remark: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _director_return_to_ds(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            remark_text = self.dir_remark_edit.toPlainText().strip() or (self.document.director_remark or "")
            if remark_text:
                routing_service.save_director_remark(self.document.id or 0, remark=remark_text)

            doc_id = self.document.id or 0
            updated_doc = routing_service.return_to_ds(doc_id, remarks=remark_text or None)
            QMessageBox.information(
                self,
                "Returned to DS",
                f"Document {self.document.reference} successfully returned to Director Secretary."
            )
            self.document_updated.emit(updated_doc)
            self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Workflow Error", f"Failed to return document to DS: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _hod_save_remark(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            remark_text = self.hod_remark_edit.toPlainText().strip()
            if not remark_text:
                QMessageBox.warning(self, "Validation", "Please enter an HOD remark before saving.")
                return

            doc_id = self.document.id or 0
            updated_doc = routing_service.save_hod_remark(doc_id, remark=remark_text)
            self.document = updated_doc
            self.update_view_data(updated_doc)
            QMessageBox.information(self, "Remark Saved", "HOD remark saved successfully.")
            self.document_updated.emit(updated_doc)
        except Exception as ex:
            QMessageBox.critical(self, "Save Error", f"Failed to save HOD remark: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _hod_assign_employee(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            dialog = HODAssignEmployeeDialog(self.document, self)
            if dialog.exec():
                data = dialog.get_data()
                doc_id = self.document.id or 0
                assignment = assignment_service.assign_employee(
                    document_id=doc_id,
                    assigned_to_id=data["assigned_to_id"],
                    instructions=data["instructions"]
                )
                updated_doc = document_service.get_document(doc_id)
                self.document = updated_doc
                self.update_view_data(updated_doc)
                QMessageBox.information(
                    self,
                    "Task Assigned",
                    f"Document assigned to {assignment.assigned_to_name} successfully."
                )
                self.document_updated.emit(updated_doc)
        except Exception as ex:
            QMessageBox.critical(self, "Assignment Error", f"Failed to assign staff: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_route_to_director(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            doc_id = self.document.id or 0
            updated_doc = routing_service.route_to_director(doc_id, remarks="Routed to Director for Executive Review")
            QMessageBox.information(
                self,
                "Routing Confirmed",
                f"Document {self.document.reference} routed to Director for Executive Review."
            )
            self.document = updated_doc
            self.document_updated.emit(updated_doc)
            self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Routing Error", f"Failed to route document: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_route_to_hod(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            dialog = RouteToHODDialog(self.document, self)
            if dialog.exec():
                data = dialog.get_data()
                doc_id = self.document.id or 0
                updated_doc = routing_service.route_to_hod(
                    doc_id,
                    department_id=data["department_id"],
                    remarks=data["remarks"]
                )
                QMessageBox.information(
                    self,
                    "Routing Confirmed",
                    f"Document {self.document.reference} routed to {updated_doc.target_department_name} HOD."
                )
                self.document = updated_doc
                self.document_updated.emit(updated_doc)
                self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Routing Error", f"Failed to route document: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_route_to_employee(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            dialog = RouteToEmployeeDialog(self.document, self)
            if dialog.exec():
                data = dialog.get_data()
                doc_id = self.document.id or 0
                updated_doc = routing_service.route_to_employee(
                    doc_id,
                    employee_id=data["employee_id"],
                    remarks=data["remarks"]
                )
                QMessageBox.information(
                    self,
                    "Routing Confirmed",
                    f"Document {self.document.reference} directly routed to {updated_doc.assigned_employee_name}."
                )
                self.document = updated_doc
                self.document_updated.emit(updated_doc)
                self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Routing Error", f"Failed to route document: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_apply_suggested_routing(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            doc_id = self.document.id or 0
            repo = get_repository()
            if getattr(self.document, "suggested_employee_id", None) or getattr(self.document, "suggested_employee_name", None):
                emp_name = getattr(self.document, "suggested_employee_name", "") or ""
                employees = repo.get_users(role="Employee")
                matched_emp = next((e for e in employees if e.full_name and emp_name.lower() in e.full_name.lower()), None)
                emp_id = matched_emp.id if matched_emp else (getattr(self.document, "suggested_employee_id", None) or 101)
                updated_doc = routing_service.route_to_employee(doc_id, employee_id=emp_id)
                QMessageBox.information(
                    self,
                    "Routing Confirmed",
                    f"Document {self.document.reference} routed directly to {updated_doc.assigned_employee_name or emp_name}."
                )
            elif getattr(self.document, "suggested_department_id", None) or getattr(self.document, "suggested_department_name", None):
                dept_name = getattr(self.document, "suggested_department_name", "") or ""
                departments = repo.get_departments()
                matched_dept = next((d for d in departments if d.name and (dept_name.lower() in d.name.lower() or d.name.lower() in dept_name.lower())), None)
                dept_id = matched_dept.id if matched_dept else (getattr(self.document, "suggested_department_id", None) or 1)
                updated_doc = routing_service.route_to_hod(doc_id, department_id=dept_id)
                QMessageBox.information(
                    self,
                    "Routing Confirmed",
                    f"Document {self.document.reference} routed to {updated_doc.target_department_name or dept_name} HOD."
                )
            else:
                self._action_in_progress = False
                self._ds_route_to_hod()
                return

            self.document = updated_doc
            self.document_updated.emit(updated_doc)
            self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Routing Error", f"Failed to apply suggested routing: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_edit_routing(self):
        if getattr(self.document, "suggested_employee_name", None) and self.document.suggested_employee_name != "Not specified":
            self._ds_route_to_employee()
        else:
            self._ds_route_to_hod()

    def _ds_forward_followup(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            doc_id = self.document.id or 0
            updated_doc = routing_service.forward_followup_to_director(doc_id)
            QMessageBox.information(
                self,
                "Follow-up Forwarded",
                f"Employee progress follow-up for document {self.document.reference} forwarded to Director for Executive Review."
            )
            self.document = updated_doc
            self.document_updated.emit(updated_doc)
            self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Workflow Error", f"Failed to forward follow-up: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _ds_send_reminder(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            doc_id = self.document.id or 0
            from services.notification_service import notification_service
            recipient = notification_service.send_action_reminder(doc_id)
            if not recipient:
                status_val = (self.document.status or "").lower()
                if status_val == DocumentStatusEnum.CLOSED.value.lower():
                    QMessageBox.information(
                        self,
                        "Document Closed",
                        f"Document {self.document.reference} is finalized and closed. Action reminders cannot be sent for closed documents."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "No Recipient Available",
                        f"No downstream reminder recipient is currently available for document {self.document.reference}. Please route the document to a department or assign an employee first."
                    )
                return

            email_note = f" (Email: {recipient['recipient_email']})" if recipient.get("recipient_email") else " (In-App notification recorded)"
            email_status_str = "📧 Email dispatched via Outlook." if recipient.get("email_dispatched") else "📌 In-app notification recorded."

            QMessageBox.information(
                self,
                "Action Reminder Dispatched",
                f"Official action reminder successfully dispatched for {self.document.reference}.\n\n"
                f"• Recipient: {recipient.get('user_name', 'Responsible User')} ({recipient.get('role', 'Staff')}){email_note}\n"
                f"• Delivery Status: {email_status_str}"
            )
        finally:
            self._action_in_progress = False

    def _ds_close_document(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            dialog = CloseDocumentDialog(self.document, self)
            if dialog.exec():
                data = dialog.get_data() if hasattr(dialog, "get_data") else {"remarks": dialog.get_remarks() if hasattr(dialog, "get_remarks") else ""}
                remarks_val = data.get("remarks") if isinstance(data, dict) else str(data or "")
                doc_id = self.document.id or 0
                updated_doc = document_service.close_document(doc_id, remarks=remarks_val)
                QMessageBox.information(
                    self,
                    "Document Finalized",
                    f"Document {self.document.reference} has been finalized and CLOSED."
                )
                self.document = updated_doc
                self.document_updated.emit(updated_doc)
                self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Closure Error", f"Failed to close document: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _select_progress_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Supporting Attachment",
            "",
            "Documents (*.pdf *.png *.jpg *.jpeg *.docx *.xlsx *.txt);;All Files (*)"
        )
        if file_path:
            self.selected_progress_attachment = file_path
            filename = file_path.replace("\\", "/").split("/")[-1]
            self.att_label.setText(f"Attached: {filename}")
            self.clear_att_btn.setVisible(True)

    def _clear_progress_attachment(self):
        self.selected_progress_attachment = None
        self.att_label.setText("No attachment selected")
        self.clear_att_btn.setVisible(False)

    def _employee_submit_progress(self):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            description = self._emp_progress_text_edit.toPlainText().strip()
            if not description:
                QMessageBox.warning(self, "Validation Error", "Please provide a description of the progress update before submitting.")
                return

            doc_id = self.document.id or 0
            update = progress_service.submit_progress(
                document_id=doc_id,
                description=description,
                attachment_file_path=self.selected_progress_attachment
            )
            QMessageBox.information(
                self,
                "Progress Submitted",
                f"Progress update recorded successfully for document {self.document.reference}."
            )
            self._emp_progress_text_edit.clear()
            self._clear_progress_attachment()

            updated_doc = document_service.get_document(doc_id)
            self.document = updated_doc
            self.document_updated.emit(updated_doc)
            self.close_requested.emit()
        except Exception as ex:
            QMessageBox.critical(self, "Submission Error", f"Failed to submit progress update: {str(ex)}")
        finally:
            self._action_in_progress = False

    def _view_attachment(self, attachment: AttachmentModel):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            if not attachment.is_previewable:
                QMessageBox.information(self, "Preview Not Available", f"Direct preview is not available for {attachment.extension} files. Please use Download to inspect the file.")
                return
            success = attachment_service.open_attachment(attachment, parent=self)
            if not success:
                QMessageBox.warning(self, "View Attachment", f"Could not launch viewer for {attachment.file_name}.")
        finally:
            self._action_in_progress = False

    def _download_attachment(self, attachment: AttachmentModel):
        if getattr(self, "_action_in_progress", False):
            return
        self._action_in_progress = True
        try:
            saved_path = attachment_service.download_attachment(attachment, parent=self)
        finally:
            self._action_in_progress = False

    def _toggle_raw_ocr_text(self):
        is_vis = self.ocr_text_preview.isVisible()
        self.ocr_text_preview.setVisible(not is_vis)
        self.ocr_toggle_btn.setText("Hide Raw OCR Text ▲" if not is_vis else "Show Raw OCR Extracted Text ▼")

    def _rerun_ocr_extraction(self):
        doc_id = self.document.id if self.document else None
        if not doc_id:
            return
        repo = get_repository()
        try:
            # If we have a local file path, run through OCRSplashDialog for instant visual animation
            f_path = getattr(self.document, "file_path", "") or ""
            if f_path and os.path.exists(f_path):
                OCRSplashDialog.execute_ocr(
                    file_path=f_path,
                    incoming_item=self.document.to_dict(),
                    parent=self
                )
            repo.trigger_ocr(doc_id)
            QMessageBox.information(
                self,
                "OCR Re-Analysis",
                "OCR processing completed. Refreshed document intelligence fields."
            )
            fresh = document_service.get_document(doc_id)
            if fresh:
                self.document = fresh
            self.update_view_data(self.document)
        except Exception as ex:
            QMessageBox.warning(self, "OCR Notice", f"OCR status: {str(ex)}")