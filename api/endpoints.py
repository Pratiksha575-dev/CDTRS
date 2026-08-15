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

    # --- Notifications ---
    NOTIFICATIONS_LIST = "/notifications"
    NOTIFICATIONS_UNREAD = "/notifications/unread"
    NOTIFICATION_MARK_READ = lambda notif_id: f"/notifications/{notif_id}/read"

    # --- Dashboard ---
    DASHBOARD_STATS = "/dashboard"
