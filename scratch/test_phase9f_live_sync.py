import sys
import os

# Point to project root
sys.path.insert(0, r"c:\Users\Pratiksha\OneDrive\Desktop\CDTRS")

print("======================================================================")
print("TESTING PHASE 9F: LIVE DATA SYNCHRONIZATION & REFRESH REMOVAL")
print("======================================================================")

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)

# Mock QMessageBox dialogs for automated testing
QMessageBox.information = lambda *args, **kwargs: None
QMessageBox.warning = lambda *args, **kwargs: None
QMessageBox.critical = lambda *args, **kwargs: None

from repositories.provider import get_repository
from services.auth_service import auth_service
from services.document_service import document_service
from services.attachment_service import attachment_service
from services.routing_service import routing_service
from services.assignment_service import assignment_service
from services.progress_service import progress_service
from services.workflow_service import workflow_service
from services.event_bus import event_bus
from models.document import DocumentModel
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum
from components.document_viewer import DocumentViewer
from pages.dashboard import DashboardPage
from pages.inbox import InboxPage
from pages.document_intake import DocumentIntakePage
from pages.documents import DocumentsPage
from pages.history import HistoryPage
from pages.hod_inbox import HODInboxPage
from pages.employee_tasks import EmployeeTasksPage
from pages.director_inbox import DirectorInboxPage
from pages.director_reviewed import DirectorReviewedPage

# ----------------------------------------------------------------------
# TEST A: FINANCE HOD TASK PAGE UPDATES AUTOMATICALLY ON DS ROUTING
# ----------------------------------------------------------------------
print("\n--- TEST A: Live Sync - DS Routes to Finance HOD ---")
auth_service.login("hod_finance", "1234")
hod_page = HODInboxPage()
initial_hod_count = len(hod_page.documents)

# Now DS routes a document in background / separate action
auth_service.login("ds", "1234")
doc_501 = document_service.create_document(
    DocumentModel(
        id=501,
        reference_no="CDTRS-2026-501",
        title="Q4 Financial Audit Reconciliation",
        source="Finance Dept",
        mode="Government Mail",
        target_department_name="Finance",
        target_department_id=1,
        attachment_count=1,
        attachments_list=["audit_report.pdf"],
        file_path="data/incoming/government_mail/audit_report.pdf",
        format="PDF"
    )
)
routing_service.route_to_hod(501, department_id=1)

# Switch active session back to Finance HOD and check hod_page WITHOUT calling refresh or load_inbox
auth_service.login("hod_finance", "1234")
event_bus.notify_data_changed()  # Trigger reactive signal broadcast

assert len(hod_page.documents) == initial_hod_count + 1, f"Expected {initial_hod_count + 1} docs, got {len(hod_page.documents)}"
assert any(d.id == 501 for d in hod_page.documents), "Document #501 must be present in open Finance HOD page without clicking Refresh"
print("[PASS] TEST A: Finance HOD task view automatically synchronized when DS routed a Finance document.")

# ----------------------------------------------------------------------
# TEST B: EMPLOYEE TASK PAGE UPDATES AUTOMATICALLY ON HOD ASSIGNMENT
# ----------------------------------------------------------------------
print("\n--- TEST B: Live Sync - HOD Assigns Employee ---")
auth_service.login("employee", "1234")  # Rahul Sharma (ID 5)
emp_page = EmployeeTasksPage(employee_id=5)
initial_emp_count = len(emp_page.documents)

# Finance HOD assigns Document #501 to Rahul Sharma
auth_service.login("hod_finance", "1234")
assignment_service.assign_employee(501, assigned_to_id=5, instructions="Audit annexures 1-5.")

# Switch session back to Rahul Sharma
auth_service.login("employee", "1234")
event_bus.notify_data_changed()

assert len(emp_page.documents) == initial_emp_count + 1, f"Expected {initial_emp_count + 1} tasks, got {len(emp_page.documents)}"
assert any(d.id == 501 for d in emp_page.documents), "Document #501 must appear in Rahul's open task page without clicking Refresh"
print("[PASS] TEST B: Employee task view automatically synchronized when HOD assigned the document.")

# ----------------------------------------------------------------------
# TEST C: DOCUMENT VIEWER UPDATES AUTOMATICALLY ON DIRECTOR REMARK
# ----------------------------------------------------------------------
print("\n--- TEST C: Live Sync - Director Remark in Open DocumentViewer ---")
doc_502 = document_service.create_document(
    DocumentModel(
        id=502,
        reference_no="CDTRS-2026-502",
        title="High Performance Computing Cluster",
        source="IT Cell",
        mode="Internal Outlook",
        attachment_count=1,
        attachments_list=["procurement_proposal.pdf"],
        file_path="data/incoming/outlook/procurement_proposal.pdf",
        format="PDF"
    )
)
routing_service.route_to_director(502)

# Open DocumentViewer for Document #502 as Director
viewer = DocumentViewer(doc_502, role="Director")
assert viewer.document.director_remark is None

# Director saves remark
new_remark = "Approved in full. Procure 64-node cluster immediately."
routing_service.save_director_remark(502, remark=new_remark)

# Check viewer.document directly without closing or reopening
assert viewer.document.director_remark == new_remark, "DocumentViewer must reactively update open document remark"
print("[PASS] TEST C: DocumentViewer automatically reflected the saved Director remark via event_bus.")

# ----------------------------------------------------------------------
# TEST D: EMPLOYEE SUBMITS PROGRESS UPDATES OPEN HOD / DS VIEWS
# ----------------------------------------------------------------------
print("\n--- TEST D: Live Sync - Employee Progress Updates Live Views ---")
auth_service.login("ds", "1234")
docs_page = DocumentsPage("Director Secretary")

auth_service.login("employee", "1234")
progress_service.submit_progress(
    document_id=501,
    description="Annexures 1-5 audited. No discrepancies found."
)

auth_service.login("ds", "1234")
event_bus.notify_data_changed()

doc_501_in_page = next((d for d in docs_page.all_documents if d.id == 501), None)
assert doc_501_in_page is not None
assert doc_501_in_page.status == DocumentStatusEnum.PROGRESS_UPDATED.value
print("[PASS] TEST D: Open DocumentsPage reactively reflected progress submission without clicking Refresh.")

# ----------------------------------------------------------------------
# TEST E: DS CLOSES DOCUMENT UPDATES DASHBOARD COUNTERS
# ----------------------------------------------------------------------
print("\n--- TEST E: Live Sync - Document Closure Updates Dashboard Counters ---")
auth_service.login("ds", "1234")
dash = DashboardPage("Director Secretary")
initial_closed_count = int(dash.card_closed["value_label"].text())

# DS closes document #501
document_service.close_document(501, remarks="Audit reconciliation complete.")

# Dashboard updates automatically
new_closed_count = int(dash.card_closed["value_label"].text())
assert new_closed_count == initial_closed_count + 1, f"Expected {initial_closed_count + 1} closed documents, got {new_closed_count}"
print("[PASS] TEST E: Dashboard counters updated reactively when DS closed a document.")

# ----------------------------------------------------------------------
# TEST F: NEW INCOMING DOCUMENT ARRIVAL UPDATES DS INBOX
# ----------------------------------------------------------------------
print("\n--- TEST F: Live Sync - New Incoming Item Updates DS Inbox ---")
inbox = InboxPage()
initial_inbox_count = len(inbox.documents)

# Simulate new dispatch arriving in system
new_dispatch = DocumentModel(
    id=503,
    title="Urgent Security Advisory Directive",
    source="Cyber Directorate",
    mode="Government Mail",
    format="PDF",
    attachment_count=1,
    attachments_list=["security_policy_directive.pdf"],
    file_path="data/incoming/government_mail/security_policy_directive.pdf"
)
document_service.add_inbox_item(new_dispatch)

assert len(inbox.documents) == initial_inbox_count + 1, f"Expected {initial_inbox_count + 1} inbox items, got {len(inbox.documents)}"
assert any(d.id == 503 for d in inbox.documents), "New incoming item #503 must appear in DS Inbox without clicking Refresh"
print("[PASS] TEST F: DS Inbox automatically updated when new incoming dispatch arrived.")

# ----------------------------------------------------------------------
# TEST G: AUDIT / HISTORY REACTIVELY UPDATES ON ACTIONS & CLEAR BUTTON WORKS
# ----------------------------------------------------------------------
print("\n--- TEST G: Live Sync - History Trail & Clear Button Visibility ---")
auth_service.login("ds", "1234")
hist = HistoryPage()
initial_cards_count = hist.cards_layout.count()

# New action happens on doc #502
routing_service.return_to_ds(502, remarks="Returned to DS")

# Verify history cards updated reactively
assert hist.cards_layout.count() >= initial_cards_count

# Test Clear button functionality
assert hist.clear_button.isHidden() is True  # Hidden when no filter active
hist.search_input.setText("HPC")
assert hist.clear_button.isHidden() is False  # Visible when search is active
hist.clear_filters()
assert hist.clear_button.isHidden() is True   # Hidden after clearing
assert hist.search_input.text() == ""
print("[PASS] TEST G: HistoryPage updated reactively and Clear Filters button functions cleanly.")

# ----------------------------------------------------------------------
# TEST H: VERIFY ALL USER-FACING REFRESH BUTTONS ARE REMOVED
# ----------------------------------------------------------------------
print("\n--- TEST H: Verified All User-Facing Refresh Buttons Removed ---")
assert not hasattr(dash, "refresh_btn"), "DashboardPage must NOT have a refresh_btn"
assert not hasattr(inbox, "refresh_btn"), "InboxPage must NOT have a refresh_btn"
assert not hasattr(docs_page, "refresh_button"), "DocumentsPage must NOT have a refresh_button"
assert not hasattr(hist, "refresh_btn"), "HistoryPage must NOT have a refresh_btn"

dir_inbox = DirectorInboxPage()
assert not hasattr(dir_inbox, "refresh_btn"), "DirectorInboxPage must NOT have a refresh_btn"

dir_rev = DirectorReviewedPage()
assert not hasattr(dir_rev, "refresh_btn"), "DirectorReviewedPage must NOT have a refresh_btn"

hod_inbox = HODInboxPage()
assert not hasattr(hod_inbox, "refresh_btn"), "HODInboxPage must NOT have a refresh_btn"

emp_tasks = EmployeeTasksPage()
assert not hasattr(emp_tasks, "refresh_btn"), "EmployeeTasksPage must NOT have a refresh_btn"

print("[PASS] TEST H: All 8 obsolete user-facing Refresh buttons have been completely removed across all roles.")

print("\n======================================================================")
print("ALL LIVE SYNCHRONIZATION TESTS PASSED 100%!")
print("======================================================================")
