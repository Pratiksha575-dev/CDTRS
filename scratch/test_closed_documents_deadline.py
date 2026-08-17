import os
import sys
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if os.path.join(ROOT_DIR, "frontend") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, "frontend"))

from config.settings import settings
settings.set_data_source("mock")

from PySide6.QtWidgets import QApplication
from models.document import DocumentModel
from pages.documents import DocumentsPage

app = QApplication.instance() or QApplication(sys.argv)

today = datetime.now().date()
deadline_3d = (today + timedelta(days=3)).strftime("%Y-%m-%d")

active_doc = DocumentModel(
    id=1,
    reference_no="CDTRS-2026-001",
    title="Active Document",
    deadline=deadline_3d,
    status="In Progress",
    current_stage="EMPLOYEE"
)

closed_doc = DocumentModel(
    id=2,
    reference_no="CDTRS-2026-002",
    title="Closed Document",
    deadline=deadline_3d,
    status="Closed",
    current_stage="CLOSED"
)

docs_page = DocumentsPage()
docs_page.set_filters(deadline="Due Within 7 Days")
docs_page.all_documents = [active_doc, closed_doc]
docs_page.apply_filters()

# Check filtered table
table_docs = [docs_page.table.item(r, 0).text() for r in range(docs_page.table.rowCount())]
print(f"Table documents for 'Due Within 7 Days': {table_docs}")

assert "CDTRS-2026-001" in table_docs, "Active document due in 3 days must be shown!"
assert "CDTRS-2026-002" not in table_docs, "Closed document must NOT be shown in Upcoming Deadlines!"

print("=" * 60)
print("[PASS] Verified: Closed documents are excluded from Upcoming Deadlines!")
print("=" * 60)
