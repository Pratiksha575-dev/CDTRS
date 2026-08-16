class Endpoints:
    """
    Centralized registry of backend API endpoint paths for CDTRS V2.
    All paths are relative to the client base_url (/api/v1).
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
    EMPLOYEES_LIST = "/employees"

    # --- Mail & Intake Pipeline ---
    INTAKE_LIST = "/intake"
    INTAKE_MANUAL_UPLOAD = "/intake/manual-upload"
    INTAKE_PROCESS = lambda intake_id: f"/intake/{intake_id}/process"

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
    DOCUMENT_REMARKS_HISTORY = lambda doc_id: f"/documents/{doc_id}/remarks"

    # --- Work Assignment (HOD -> Employee Delegation) ---
    DOCUMENT_ASSIGN = lambda doc_id: f"/documents/{doc_id}/assign"

    # --- Employee Progress Updates ---
    PROGRESS_CREATE = lambda doc_id: f"/documents/{doc_id}/progress"
    PROGRESS_LIST = lambda doc_id: f"/documents/{doc_id}/progress"

    # --- Attachments ---
    ATTACHMENT_UPLOAD = lambda doc_id: f"/documents/{doc_id}/attachments"
    ATTACHMENT_LIST = lambda doc_id: f"/documents/{doc_id}/attachments"
    ATTACHMENT_DETAIL = lambda attach_id: f"/attachments/{attach_id}"
    ATTACHMENT_DOWNLOAD = lambda attach_id: f"/attachments/{attach_id}/download"

    # --- Workflow History ---
    DOCUMENT_HISTORY = lambda doc_id: f"/documents/{doc_id}/history"

    # --- OCR & Verification Pipeline ---
    OCR_PROCESS = lambda doc_id: f"/documents/{doc_id}/process-ocr"
    OCR_GET = lambda doc_id: f"/documents/{doc_id}/ocr"
    OCR_VERIFY = lambda doc_id: f"/documents/{doc_id}/verify-field"
    OCR_REANALYZE = lambda doc_id: f"/documents/{doc_id}/reanalyze"

    # --- Routing Intelligence ---
    ROUTING_ANALYZE = lambda doc_id: f"/documents/{doc_id}/analyze-routing"
    ROUTING_SUGGESTION = lambda doc_id: f"/documents/{doc_id}/routing-suggestion"

    # --- Reminders ---
    REMINDERS_LIST = "/reminders"
    REMINDERS_CHECK = "/reminders/check"
    REMINDER_MARK_READ = lambda rem_id: f"/reminders/{rem_id}/read"

    # --- Notifications ---
    NOTIFICATIONS_LIST = "/notifications"
    NOTIFICATIONS_UNREAD = "/notifications/unread"
    NOTIFICATION_MARK_READ = lambda notif_id: f"/notifications/{notif_id}/read"
    NOTIFICATIONS_MARK_ALL_READ = "/notifications/read-all"

    # --- Dashboard & Events ---
    DASHBOARD_STATS = "/dashboard"
    EVENTS_RECENT = "/events/recent"
