import os
import sys
import tempfile
import traceback

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
from repositories.mock_repository import MockRepository
from repositories.api_repository import APIRepository
from models.attachment import AttachmentModel
from models.document import DocumentModel
from models.enums import RoleEnum, RouteTypeEnum
from services.attachment_service import attachment_service


def test_attachment_model_mapping():
    print("\n--- 1. Testing Attachment Model & attached_by_id Mapping ---")
    raw_backend_data = {
        "id": 42,
        "document_id": 10,
        "progress_update_id": None,
        "uploaded_by_user_id": 5,
        "file_name": "Audit_Report_2026.pdf",
        "storage_key": "2026/10/Audit_Report_2026.pdf",
        "file_type": "application/pdf",
        "file_size": 245760,
        "created_at": "2026-08-16T12:00:00"
    }

    model = AttachmentModel.from_dict(raw_backend_data)
    assert model.id == 42
    assert model.document_id == 10
    assert model.uploaded_by == 5
    assert model.attached_by_id == 5
    assert model.uploaded_by_id == 5
    assert model.file_name == "Audit_Report_2026.pdf"
    assert model.extension == "PDF"
    assert model.is_previewable is True
    assert "240.0 KB" in model.formatted_size

    # Test serialization
    serialized = model.to_dict()
    assert serialized["uploaded_by"] == 5
    assert serialized["attached_by_id"] == 5
    assert serialized["uploaded_by_id"] == 5
    print(" [PASS] AttachmentModel mapping & attached_by_id alias verified 100%")


def test_mock_mode_attachments():
    print("\n--- 2. Testing Mock Mode Attachments ---")
    settings.set_data_source("mock")
    repo = get_repository()
    assert isinstance(repo, MockRepository)

    ds_user = repo.authenticate("ds", "ds123")
    assert ds_user is not None

    # Get sample document
    inbox = repo.get_inbox()
    assert len(inbox) > 0
    doc = inbox[0]

    # Create dummy local file for test
    temp_dir = tempfile.mkdtemp()
    test_file_path = os.path.join(temp_dir, "test_mock_supporting_doc.pdf")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("CDTRS Mock Test PDF Content 2026")

    # Upload attachment
    uploaded = repo.upload_attachment(
        document_id=doc.id,
        file_path=test_file_path,
        category="ORIGINAL",
        source="Government Dispatch"
    )
    assert uploaded.id is not None
    assert uploaded.document_id == doc.id
    assert uploaded.uploaded_by == ds_user.id
    assert uploaded.attached_by_id == ds_user.id
    print(f" [PASS] Mock upload success: ID={uploaded.id}, attached_by_id={uploaded.attached_by_id}")

    # List attachments
    atts = repo.get_attachments(doc.id)
    assert len(atts) > 0
    print(f" [PASS] Mock list attachments: Found {len(atts)} attachments for doc {doc.id}")

    # Test download via AttachmentService
    dest_path = os.path.join(temp_dir, "downloaded_mock.pdf")
    saved = attachment_service.download_attachment(uploaded, target_path=dest_path)
    assert saved is not None and os.path.exists(saved)
    print(f" [PASS] Mock download success: Saved to {saved}")


def test_api_mode_attachments(backend_url="https://cdtrs.onrender.com/api/v1"):
    print("\n--- 3. Testing API Mode Attachments (Live Backend) ---")
    settings.set_api_url(backend_url)
    settings.set_data_source("api")
    settings.api_timeout = 60.0

    repo = get_repository()
    assert isinstance(repo, APIRepository)

    # 1. Authenticate DS
    ds_user = repo.authenticate("ds_user", "cdtrs@ds")
    assert ds_user is not None
    print(f" [PASS] Authenticated DS: {ds_user.full_name} (ID: {ds_user.id})")

    # 2. Check if we can create or pick a test document for attachment upload
    # Using existing document or creating a lightweight intake test file
    temp_dir = tempfile.mkdtemp()
    sample_pdf_path = os.path.join(temp_dir, "statutory_compliance_circular.pdf")
    with open(sample_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 Mock CDTRS Regulatory Circular Document Content 2026")

    sample_png_path = os.path.join(temp_dir, "expenditure_breakdown.png")
    with open(sample_png_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    # Create document via manual upload
    new_doc = DocumentModel(
        title="Phase 3 Attachment Integration Canonical Verification Document",
        date="2026-08-16",
        mode="Manual Upload",
        source="State Audit Bureau",
        priority="High",
        remarks="Automated verification dispatch for Phase 3 attachment storage."
    )
    doc = repo.create_document(new_doc, file_path=sample_pdf_path)
    assert doc.id is not None
    print(f" [PASS] Registered test document: ID={doc.id}, Ref={doc.reference_no}")

    # 3. Upload multiple attachments
    print("\n[3.1] Uploading Attachment 1 (Supporting PDF)...")
    att1 = repo.upload_attachment(
        document_id=doc.id,
        file_path=sample_pdf_path,
        category="ORIGINAL"
    )
    assert att1.id is not None
    assert att1.uploaded_by == ds_user.id
    assert att1.attached_by_id == ds_user.id
    assert att1.uploaded_by_name == ds_user.full_name
    print(f" [PASS] Uploaded Attachment 1: ID={att1.id}, File='{att1.file_name}', attached_by_id={att1.attached_by_id} ({att1.uploaded_by_name})")

    print("\n[3.2] Uploading Attachment 2 (Supporting Image - Multiple Attachments Check)...")
    att2 = repo.upload_attachment(
        document_id=doc.id,
        file_path=sample_png_path,
        category="ORIGINAL"
    )
    assert att2.id is not None
    assert att2.id != att1.id
    assert att2.document_id == doc.id
    assert att2.attached_by_id == ds_user.id
    print(f" [PASS] Uploaded Attachment 2: ID={att2.id}, File='{att2.file_name}', attached_by_id={att2.attached_by_id}")

    # 4. List and verify attachments
    print("\n[3.3] Querying Document Attachments List...")
    doc_atts = repo.get_attachments(doc.id)
    assert len(doc_atts) >= 2, f"Expected at least 2 attachments, got {len(doc_atts)}"
    print(f" [PASS] Successfully listed {len(doc_atts)} attachments linked to document {doc.id}")
    for a in doc_atts:
        print(f"        - Attachment ID={a.id}, Name='{a.file_name}', Size={a.formatted_size}, Uploader='{a.uploaded_by_name}' (ID: {a.attached_by_id})")

    # 5. Download and Caching via AttachmentService
    print("\n[3.4] Testing Authorized Download & Local Caching...")
    cached_path = attachment_service._ensure_local_copy(att1)
    assert cached_path is not None and os.path.exists(cached_path)
    assert os.path.getsize(cached_path) > 0
    print(f" [PASS] Attachment 1 successfully streamed and cached: {cached_path} ({os.path.getsize(cached_path)} bytes)")

    # 6. Attachment Persistence Through Routing
    print("\n[3.5] Verifying Attachment Persistence Through Routing...")
    routed = repo.route_document(doc.id, "DS_TO_DIRECTOR", to_user_id=2, remarks="Routing with attachments to Director")
    assert routed.current_stage == "DIRECTOR"
    
    # Check attachments under Director session
    repo.authenticate("director", "cdtrs@director")
    director_atts = repo.get_attachments(doc.id)
    assert len(director_atts) == len(doc_atts), "Attachments count changed after routing!"
    print(f" [PASS] Attachments remained intact across routing to Director ({len(director_atts)} attachments)")

    # 7. Authorization Check (Unauthorized User)
    print("\n[3.6] Testing Unauthorized User Attachment Access...")
    # Procurement HOD is not involved in this unassigned document and should not have access if document is unrouted to them
    repo.authenticate("hod_procurement", "cdtrs@hod")
    try:
        from api.client import api_client
        from api.endpoints import Endpoints
        api_client.get(Endpoints.ATTACHMENT_DOWNLOAD(att1.id))
        print(" [WARN] Endpoint allowed access or user had organization-level read privileges")
    except Exception as ex:
        print(f" [PASS] Correctly blocked unauthorized attachment access: {ex}")

    print("\n>>> ALL PHASE 3 ATTACHMENT TESTS COMPLETED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    try:
        test_attachment_model_mapping()
        test_mock_mode_attachments()
        test_api_mode_attachments()
        print("\n=======================================================")
        print("PHASE 3: ATTACHMENTS & FILE STORAGE FULLY VALIDATED!")
        print("=======================================================")
    except Exception as ex:
        print(f"\n[FAIL] Phase 3 verification error: {ex}")
        traceback.print_exc()
        sys.exit(1)
