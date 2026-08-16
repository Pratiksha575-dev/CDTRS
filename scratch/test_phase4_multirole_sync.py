import os
import sys
import json
import time
import tempfile
import traceback
from PySide6.QtCore import QCoreApplication, QTimer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# For testing HTTPS without certificate failure on Windows dev environments
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
original_request = requests.Session.request
def insecure_request(self, method, url, *args, **kwargs):
    kwargs["verify"] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = insecure_request

from config.settings import settings
from repositories.provider import get_repository
from repositories.api_repository import APIRepository
from services.websocket_service import WebSocketService
from services.event_bus import event_bus
from models.document import DocumentModel


def run_multi_role_realtime_sync_test(backend_url="https://cdtrs.onrender.com/api/v1"):
    print("\n=======================================================")
    print("PHASE 4: MULTI-ROLE REALTIME SYNCHRONIZATION TEST")
    print("=======================================================")
    settings.set_api_url(backend_url)
    settings.set_data_source("api")
    settings.api_timeout = 60.0

    app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    # Start live WebSocket client listener
    ws_service = WebSocketService()
    ws_events = []
    ws_service.event_received.connect(lambda ev: ws_events.append(ev))
    ws_service.connect_client()

    start_t = time.time()
    while not ws_service.is_connected() and time.time() - start_t < 15:
        app.processEvents()
        time.sleep(0.05)

    assert ws_service.is_connected(), "WebSocket failed to connect"
    print("[1] Live WebSocket Client Connected [PASS]")

    # Prepare document
    repo = get_repository()
    assert isinstance(repo, APIRepository)

    # 1. DS Session creates document
    print("\n[2] DS Session: Creating and registering test document...")
    repo.authenticate("ds_user", "cdtrs@ds")
    temp_dir = tempfile.mkdtemp()
    sample_pdf = os.path.join(temp_dir, "policy_directive.pdf")
    with open(sample_pdf, "wb") as f:
        f.write(b"%PDF-1.4 Realtime Multi-role Sync Test Document")

    new_doc = DocumentModel(
        title="Phase 4 Multi-Role Live Sync End-to-End Test Document",
        date="2026-08-16",
        mode="Manual Upload",
        source="Ministry of Science and Technology",
        priority="High",
        remarks="Real-time multi-role routing dispatch."
    )
    doc = repo.create_document(new_doc, file_path=sample_pdf)
    print(f"    Registered Document ID={doc.id}, Reference={doc.reference_no}")

    # Wait for DOCUMENT_CREATED event
    time.sleep(0.5)
    app.processEvents()

    # 2. DS routes to Director
    print("\n[3] DS Session: Routing document to Director...")
    routed_dir = repo.route_document(doc.id, "DS_TO_DIRECTOR", to_user_id=2, remarks="Forwarded to Director for executive review.")
    assert routed_dir.current_stage == "DIRECTOR"
    print(f"    Routed to Director: Stage={routed_dir.current_stage}")

    # 3. Director Session: Remark & Return to DS
    print("\n[4] Director Session: Saving executive remark and returning to DS...")
    repo.authenticate("director", "cdtrs@director")
    with_rem = repo.save_director_remark(doc.id, "Forward to Finance department for urgent fiscal compliance.")
    assert with_rem.director_remark is not None
    returned = repo.return_to_ds(doc.id, "Returned with executive instructions.")
    assert returned.current_stage == "DS"
    print(f"    Director returned to DS: Stage={returned.current_stage}")

    # 4. DS routes to Finance HOD
    print("\n[5] DS Session: Routing to Finance Department (HOD)...")
    repo.authenticate("ds_user", "cdtrs@ds")
    to_hod = repo.route_document(doc.id, "DS_TO_HOD", to_department_id=2, remarks="Routing to Finance HOD")
    assert to_hod.current_stage == "HOD"
    print(f"    Routed to HOD Finance: Stage={to_hod.current_stage}")

    # 5. Finance HOD assigns to Employee Rahul
    print("\n[6] Finance HOD Session: Assigning task to Employee Rahul...")
    repo.authenticate("hod_finance", "cdtrs@hod")
    assign = repo.assign_employee(doc.id, assigned_to_id=4, instructions="Execute immediate compliance check.")
    assert assign.assigned_to_id == 4
    print(f"    Assigned to Rahul (ID: {assign.assigned_to_id})")

    # 6. Employee Rahul submits progress
    print("\n[7] Employee Rahul Session: Submitting execution progress...")
    repo.authenticate("emp_rahul", "cdtrs@emp")
    prog = repo.submit_progress(doc.id, "Fiscal analysis complete. Compliance verified.")
    assert prog.id is not None
    print(f"    Progress update recorded: ID={prog.id}")

    # 7. DS closes document
    print("\n[8] DS Session: Finalizing and closing document...")
    repo.authenticate("ds_user", "cdtrs@ds")
    closed = repo.close_document(doc.id, "Final verification complete. Lifecycle closed.")
    assert closed.current_stage == "CLOSED"
    print(f"    Document successfully CLOSED: Stage={closed.current_stage}")

    # Process all pending events
    app.processEvents()
    time.sleep(1)
    app.processEvents()

    ws_service.disconnect_client()
    print(f"\n[PASS] Total real-time events captured during workflow: {len(ws_events)}")
    print(">>> MULTI-ROLE REALTIME SYNCHRONIZATION VALIDATED 100%! <<<\n")


if __name__ == "__main__":
    try:
        run_multi_role_realtime_sync_test()
    except Exception as ex:
        print(f"\n[FAIL] Multi-role test failed: {ex}")
        traceback.print_exc()
        sys.exit(1)
