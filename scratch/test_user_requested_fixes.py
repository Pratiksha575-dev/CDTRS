import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "frontend"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from config.settings import settings
settings.set_data_source("mock")

from models import DocumentModel
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum
from services.routing_service import routing_service
from pages.history import HistoryPage
from pages.documents import DocumentsPage
from components.document_viewer import DocumentViewer

print("======================================================================")
print("TESTING 3 USER FIXES: HISTORY DS FILTER, DASHBOARD FILTERS, REMARK CLASSIFICATION")
print("======================================================================")

# -----------------------------------------------------------------------------
# 1. TEST HISTORY DS FILTER
# -----------------------------------------------------------------------------
print("\n--- 1. Testing History DS Filter ---")
history_page = HistoryPage()
# Initial state has all docs with "Document Ingested" by DS
assert history_page.role_filter.count() >= 5
# Select DS filter
ds_idx = -1
for i in range(history_page.role_filter.count()):
    if "director secretary" in history_page.role_filter.itemText(i).lower() or "ds" in history_page.role_filter.itemText(i).lower():
        ds_idx = i
        break
assert ds_idx > 0, "DS filter option must be present in History role filter"
history_page.role_filter.setCurrentIndex(ds_idx)
history_page.load_history()

# Check that cards are present
assert history_page.cards_layout.count() > 1, f"History cards MUST be shown when DS filter is active! Found: {history_page.cards_layout.count() - 1}"
print(f"[PASS] History page correctly shows {history_page.cards_layout.count() - 1} documents with events for DS filter.")

# -----------------------------------------------------------------------------
# 2. TEST DASHBOARD -> DOCUMENTS FILTER PRE-APPLICATION
# -----------------------------------------------------------------------------
print("\n--- 2. Testing Pre-Applied Filters on Documents Page ---")
docs_page = DocumentsPage(user_role="Director Secretary")

# Test Status Filter: "Director Review Completed"
docs_page.set_filters(status="Director Review Completed")
assert "Director Review Completed" in docs_page.status_filter.currentText(), "Status filter dropdown must be set to 'Director Review Completed'"
print("[PASS] Status filter 'Director Review Completed' pre-applied successfully.")

# Test Status Filter: "Progress Updated"
docs_page.set_filters(status="Progress Updated")
assert "Progress Updated" in docs_page.status_filter.currentText(), "Status filter dropdown must be set to 'Progress Updated'"
print("[PASS] Status filter 'Progress Updated' pre-applied successfully.")

# Test Deadline Filter: "Due Within 7 Days"
docs_page.set_filters(deadline="Due Within 7 Days")
assert "Due Within 7 Days" in docs_page.deadline_filter.currentText(), "Deadline filter dropdown must be set to 'Due Within 7 Days'"
print("[PASS] Deadline filter 'Due Within 7 Days' pre-applied successfully.")

# Test Priority Filter: "High Priority"
docs_page.set_filters(priority="High Priority")
assert "High Priority" in docs_page.priority_filter.currentText(), "Priority filter dropdown must be set to 'High Priority'"
print("[PASS] Priority filter 'High Priority' pre-applied successfully.")

# -----------------------------------------------------------------------------
# 3. TEST GENERAL REVIEW vs ASSIGNMENT IN ROUTING INTELLIGENCE
# -----------------------------------------------------------------------------
print("\n--- 3. Testing General Review vs Explicit Assignment ---")

# General Review Remarks (MUST NOT trigger routing instruction)
general_reviews = [
    "Reviewed and approved for standard execution.",
    "Reviewed it. Looks satisfactory, please proceed.",
    "Approved. File for administrative records.",
    "Checked financial figures in the report. Looks accurate.",
    "Please check and take necessary action.",
    "Seen and verified.",
    "Standard procurement procedure applies.",
]

for remark in general_reviews:
    res = routing_service.analyze_director_remark(remark)
    assert not res["has_routing_instruction"], f"General review '{remark}' must NOT be flagged as routing instruction! Got: {res}"
print(f"[PASS] All {len(general_reviews)} general review remarks correctly classified as NON-ROUTING (No yellow card).")

# Explicit Assignment / Delegation Directives (MUST trigger routing instruction)
assignment_directives = [
    ("Approved. Route to Finance department for audit.", "Finance", None),
    ("Send to Procurement for purchase order issuance.", "Procurement", None),
    ("Assign to Rahul Sharma for execution.", "Finance", "Rahul Sharma"),
    ("Refer to HR department for personnel clearance.", "Human Resources", None),
    ("Forward to IT department for technical review.", "IT", None),
    ("Assign to Priya Verma immediately.", "Procurement", "Priya Verma"),
]

for remark, exp_dept, exp_emp in assignment_directives:
    res = routing_service.analyze_director_remark(remark)
    assert res["has_routing_instruction"], f"Directive '{remark}' MUST be flagged as routing instruction!"
    if exp_dept:
        assert res["suggested_department"] == exp_dept, f"Expected dept {exp_dept}, got {res['suggested_department']}"
    if exp_emp:
        assert res["suggested_employee"] == exp_emp, f"Expected emp {exp_emp}, got {res['suggested_employee']}"
print(f"[PASS] All {len(assignment_directives)} explicit assignment directives correctly identified with target department/employee.")

# Test DocumentViewer Yellow Card with General Review vs Assignment
viewer = DocumentViewer(
    DocumentModel(
        id=20,
        reference_no="CDTRS-2026-020",
        title="General Policy Review",
        current_stage=WorkflowStageEnum.DS.value,
        status=DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
        director_remark="Reviewed it. Good to proceed with general workflow."
    ),
    role="Director Secretary"
)
assert viewer.suggestion_card.isHidden(), "Yellow card MUST NOT show for general review remark!"
print("[PASS] DocumentViewer hides yellow suggestion card for general review remark.")

viewer.update_view_data(
    DocumentModel(
        id=21,
        reference_no="CDTRS-2026-021",
        title="Delegated Tender Procurement",
        current_stage=WorkflowStageEnum.DS.value,
        status=DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value,
        director_remark="Approved. Route to Procurement department."
    )
)
assert not viewer.suggestion_card.isHidden(), "Yellow card MUST show for explicit department delegation directive!"
print("[PASS] DocumentViewer displays yellow suggestion card for explicit assignment directive.")

print("======================================================================")
print("ALL 3 USER-REQUESTED FIXES VERIFIED AND PASSING 100%!")
print("======================================================================")
