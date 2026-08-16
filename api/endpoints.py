class Endpoints:
    """
    Centralized registry of backend API endpoint paths for CDTRS V2.
    Paths are structured as capability placeholders and can be centrally updated
    when the backend developer provides the finalized OpenAPI/Swagger contract.
    """

    # --- Authentication ---
    AUTH_LOGIN = "/auth/login"
    AUTH_ME = "/auth/me"
    AUTH_LOGOUT = "/auth/logout"

    # --- Users & Departments ---
    USERS_LIST = "/users"
    USER_DETAIL = lambda user_id: f"/users/{user_id}"
    DEPARTMENTS_LIST = "/departments"
    DEPARTMENT_EMPLOYEES = lambda dept_id: f"/departments/{dept_id}/employees"

    # --- Documents Lifecycle ---
    DOCUMENTS_INBOX = "/documents/inbox"
    DOCUMENTS_LIST = "/documents"
    DOCUMENT_CREATE = "/documents"
    DOCUMENT_DETAIL = lambda doc_id: f"/documents/{doc_id}"
    DOCUMENT_STATUS = lambda doc_id: f"/documents/{doc_id}/status"
    DOCUMENT_CLOSE = lambda doc_id: f"/documents/{doc_id}/close"

    # --- Document Routing (DS Workflow) ---
    DOCUMENT_ROUTE = lambda doc_id: f"/documents/{doc_id}/route"
    DOCUMENT_RETURN_TO_DS = lambda doc_id: f"/documents/{doc_id}/return-to-ds"
    DOCUMENT_FOLLOW_UP = lambda doc_id: f"/documents/{doc_id}/follow-up"

    # --- Remarks ---
    DIRECTOR_REMARK = lambda doc_id: f"/documents/{doc_id}/director-remark"
    HOD_REMARK = lambda doc_id: f"/documents/{doc_id}/hod-remark"

    # --- Work Assignment (HOD -> Employee Delegation) ---
    DOCUMENT_ASSIGN = lambda doc_id: f"/documents/{doc_id}/assign"

    # --- Employee Progress Updates ---
    PROGRESS_CREATE = lambda doc_id: f"/documents/{doc_id}/progress"
    PROGRESS_LIST = lambda doc_id: f"/documents/{doc_id}/progress"

    # --- Attachments ---
    ATTACHMENT_UPLOAD = lambda doc_id: f"/documents/{doc_id}/attachments"
    ATTACHMENT_LIST = lambda doc_id: f"/documents/{doc_id}/attachments"
    ATTACHMENT_DOWNLOAD = lambda attach_id: f"/attachments/{attach_id}/download"

    # --- Workflow History ---
    DOCUMENT_HISTORY = lambda doc_id: f"/documents/{doc_id}/history"

    # --- Remarks History ---
    DOCUMENT_REMARKS = lambda doc_id: f"/documents/{doc_id}/remarks"

    # --- Intake & Mail Ingestion ---
    INTAKE_LIST = "/intake"
    INTAKE_MANUAL_UPLOAD = "/intake/manual-upload"
    INTAKE_PROCESS = lambda intake_id: f"/intake/{intake_id}/process"

    # --- OCR & Field Verification ---
    DOCUMENT_OCR = lambda doc_id: f"/documents/{doc_id}/ocr"
    DOCUMENT_PROCESS_OCR = lambda doc_id: f"/documents/{doc_id}/process-ocr"
    DOCUMENT_VERIFY_FIELD = lambda doc_id: f"/documents/{doc_id}/verify-field"

    # --- Routing Suggestions ---
    DOCUMENT_ROUTING_SUGGESTION = lambda doc_id: f"/documents/{doc_id}/routing-suggestion"
    DOCUMENT_ANALYZE_ROUTING = lambda doc_id: f"/documents/{doc_id}/analyze-routing"

    # --- Notifications ---
    NOTIFICATIONS_LIST = "/notifications"
    NOTIFICATIONS_UNREAD = "/notifications/unread"
    NOTIFICATION_MARK_READ = lambda notif_id: f"/notifications/{notif_id}/read"

    # --- Reminders ---
    REMINDERS_LIST = "/reminders"
    REMINDERS_CHECK = "/reminders/check"
    REMINDER_MARK_READ = lambda rem_id: f"/reminders/{rem_id}/read"

    # --- Dashboard ---
    DASHBOARD_STATS = "/dashboard"

