import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from config.settings import settings
settings.set_data_source("mock")

from models import DocumentModel
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum
from components.document_viewer import DocumentViewer

print("======================================================================")
print("TESTING CONDITIONAL YELLOW SUGGESTION CARD VISIBILITY")
print("======================================================================")

# Case 1: Generic Director Remark (NO department or employee mentioned)
doc_generic = DocumentModel(
    id=10,
    reference_no="CDTRS-2026-010",
    title="Quarterly Administrative Circular",
    current_stage=WorkflowStageEnum.DS.value,
    status=DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
    director_remark="Document reviewed and approved for standard execution.",
    suggested_department_name=None,
    suggested_employee_name=None
)
viewer = DocumentViewer(doc_generic, role="Director Secretary")
assert viewer.suggestion_card.isHidden(), "Yellow card MUST NOT appear for generic Director remarks without department/employee!"
print("[PASS] Case 1: Generic Director remark does NOT show the yellow suggestion card.")

# Case 2: Director Remark mentioning specific Department ("Finance")
doc_dept = DocumentModel(
    id=11,
    reference_no="CDTRS-2026-011",
    title="Capital Grant Allocation Notice",
    current_stage=WorkflowStageEnum.DS.value,
    status=DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
    director_remark="Approved in principle. Route to Finance department for financial verification.",
    suggested_department_name=None,
    suggested_employee_name=None
)
viewer.update_view_data(doc_dept)
assert not viewer.suggestion_card.isHidden(), "Yellow card MUST appear when Director mentions Finance department!"
assert "Finance" in viewer.sugg_detected_lbl.text(), "Detected department must be Finance"
print("[PASS] Case 2: Director remark mentioning 'Finance' shows the yellow suggestion card with 'Department: Finance'.")

# Case 3: Director Remark mentioning specific Employee ("Rahul Sharma")
doc_emp = DocumentModel(
    id=12,
    reference_no="CDTRS-2026-012",
    title="Security Audit & Compliance Protocol",
    current_stage=WorkflowStageEnum.DS.value,
    status=DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
    director_remark="Approved. Assign to Rahul Sharma for immediate execution.",
    suggested_department_name=None,
    suggested_employee_name=None
)
viewer.update_view_data(doc_emp)
assert not viewer.suggestion_card.isHidden(), "Yellow card MUST appear when Director mentions Rahul Sharma!"
assert "Rahul Sharma" in viewer.sugg_detected_lbl.text(), "Detected employee must be Rahul Sharma"
print("[PASS] Case 3: Director remark mentioning 'Rahul Sharma' shows the yellow suggestion card with 'Employee: Rahul Sharma'.")

# Case 4: Pre-reviewed Document from OCR with Director Directive (e.g. Document 4)
doc_ocr_directive = DocumentModel(
    id=13,
    reference_no="CDTRS-2026-013",
    title="Pre-Approved Security Infrastructure Upgrade",
    current_stage=WorkflowStageEnum.DS.value,
    status=DocumentStatusEnum.RECEIVED.value,
    has_prior_director_remark=True,
    director_remark="Approved. Expedite procurement and assign to Rahul Sharma for immediate execution.",
    suggested_department_name="Finance",
    suggested_employee_name="Rahul Sharma"
)
viewer.update_view_data(doc_ocr_directive)
assert not viewer.suggestion_card.isHidden(), "Yellow card MUST appear for pre-reviewed OCR directive with suggested staff!"
print("[PASS] Case 4: Pre-reviewed OCR directive with suggested staff shows the yellow suggestion card.")

# Case 5: Document at HOD stage (not DS stage)
doc_hod_stage = DocumentModel(
    id=14,
    reference_no="CDTRS-2026-014",
    title="Procurement Tender Document",
    current_stage=WorkflowStageEnum.HOD.value,
    status=DocumentStatusEnum.UNDER_HOD_PROCESSING.value,
    director_remark="Route to Procurement for implementation.",
    suggested_department_name="Procurement"
)
viewer.update_view_data(doc_hod_stage)
assert viewer.suggestion_card.isHidden(), "Yellow card MUST NOT appear when document is not in DS stage!"
print("[PASS] Case 5: Document at HOD stage does NOT show the yellow suggestion card.")

print("======================================================================")
print("ALL 5 CONDITIONAL YELLOW CARD TESTS PASSED SUCCESSFULLY! (100%)")
print("======================================================================")
