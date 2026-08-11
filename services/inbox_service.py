class InboxService:

    def get_inbox_documents(self):
        """
        Temporary mock inbox data.

        Later this will call the backend:
        GET /inbox
        """

        return [
            {
                "id": 1,
                "source": "Outlook",
                "title": "Budget Approval Request",
                "file_type": "PDF",
                "received": "11 Aug 2026 09:15",
                "status": "New",
                "mode": "Email",
                "file_path": ""
            },
            {
                "id": 2,
                "source": "Intranet",
                "title": "Department Circular",
                "file_type": "PDF",
                "received": "11 Aug 2026 10:05",
                "status": "New",
                "mode": "Intranet",
                "file_path": ""
            },
            {
                "id": 3,
                "source": "Fax",
                "title": "Purchase Order",
                "file_type": "Image",
                "received": "11 Aug 2026 11:20",
                "status": "New",
                "mode": "Fax",
                "file_path": ""
            },
            {
                "id": 4,
                "source": "Physical",
                "title": "Employee Application",
                "file_type": "PDF",
                "received": "11 Aug 2026 12:10",
                "status": "New",
                "mode": "Physical",
                "file_path": ""
            }
        ]


inbox_service = InboxService()