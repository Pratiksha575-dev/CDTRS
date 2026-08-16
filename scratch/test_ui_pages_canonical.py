import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)
QMessageBox.information = lambda *args, **kwargs: None
QMessageBox.warning = lambda *args, **kwargs: None
QMessageBox.critical = lambda *args, **kwargs: None

from config.settings import settings
settings.set_data_source("mock")

from repositories.provider import get_repository
from repositories.mock_repository import MockRepository
import repositories.provider as prov

# Reset repository to fresh state
prov._mock_repo_instance = MockRepository()
repo = get_repository()

from services.auth_service import auth_service
from pages.dashboard import DashboardPage
from pages.inbox import InboxPage
from pages.documents import DocumentsPage
from pages.history import HistoryPage
from pages.director_inbox import DirectorInboxPage
from pages.director_reviewed import DirectorReviewedPage
from pages.hod_inbox import HODInboxPage
from pages.employee_tasks import EmployeeTasksPage
from pages.document_intake import DocumentIntakePage
from components.document_viewer import DocumentViewer

print("--- Testing UI Pages with Canonical Dataset ---")

# 1. DS Session
auth_service.login("ds", "1234")
print("1. DS Pages:")
ds_dash = DashboardPage()
ds_dash.refresh()
print(f"   Dashboard KPI New Incoming count: {ds_dash.card_intake['value_label'].text()}")
assert int(ds_dash.card_intake['value_label'].text()) == 5

ds_inbox = InboxPage()
ds_inbox.load_documents()
print(f"   DS Intake Inbox table rows: {ds_inbox.table.rowCount()}")
assert ds_inbox.table.rowCount() == 5

ds_docs = DocumentsPage()
ds_docs.load_documents()
print(f"   DS Documents table rows: {ds_docs.table.rowCount()}")
assert ds_docs.table.rowCount() == 5

ds_history = HistoryPage()
ds_history.load_history()
print(f"   History count label: {ds_history.count_label.text()}")
assert "5 active document" in ds_history.count_label.text()

# Test DocumentViewer on Document 4 (Pre-reviewed)
doc4 = repo.get_document(4)
viewer = DocumentViewer(doc4, role="Director Secretary")
assert not viewer.suggestion_card.isHidden(), "Suggestion card should not be hidden for Doc 4"
print("   Document 4 Viewer shows Director Remark Detected card: True")

# Test DocumentViewer on Document 1 (Fresh)
doc1 = repo.get_document(1)
viewer1 = DocumentViewer(doc1, role="Director Secretary")
assert viewer1.suggestion_card.isHidden(), "Suggestion card should be hidden for Doc 1"
print("   Document 1 Viewer does not show suggestion card: True")

# 2. Director Session
print("\n2. Director Pages:")
auth_service.login("director", "1234")
dir_inbox = DirectorInboxPage()
dir_inbox.load_inbox()
print(f"   Director Inbox rows: {dir_inbox.table.rowCount()} (Expected 0 initially)")
assert dir_inbox.table.rowCount() == 0

dir_reviewed = DirectorReviewedPage()
dir_reviewed.load_documents()
print(f"   Director Reviewed archive rows: {dir_reviewed.table.rowCount()}")

# 3. HOD Session (Finance)
print("\n3. HOD Pages (Finance):")
auth_service.login("hod_finance", "1234")
hod_inbox = HODInboxPage()
hod_inbox.load_inbox()
print(f"   Finance HOD Inbox rows: {hod_inbox.table.rowCount()} (Expected 0 initially)")
assert hod_inbox.table.rowCount() == 0

# 4. Employee Session (Rahul Sharma)
print("\n4. Employee Pages (Rahul Sharma):")
auth_service.login("emp_rahul", "1234")
emp_tasks = EmployeeTasksPage()
emp_tasks.load_tasks()
print(f"   Rahul Sharma Tasks rows: {emp_tasks.table.rowCount()} (Expected 0 initially)")
assert emp_tasks.table.rowCount() == 0

print("\n[ALL UI PAGES RENDERED AND VERIFIED SUCCESSFULLY]")
