DOCUMENTS = [
    {
    "reference": "CDTRS-2026-001",
    "subject": "Budget Approval Request",
    "department": "Finance",
    "employee": "Rahul Sharma",
    "source": "Outlook",
    "status": "New",
    "date": "11 Aug 2026",
    "deadline": "12 Aug 2026",
    "priority": "Red",
    "forwarded_to": "",
    "forwarded_by": "Master"
},
    {
        "reference": "CDTRS-2026-002",
        "subject": "Purchase Order Approval",
        "department": "Procurement",
        "employee": "Amit Patil",
        "source": "Fax",
        "status": "HOD Review",
        "date": "11 Aug 2026",
        "deadline": "15 Aug 2026",
        "priority": "Orange"
    },
    {
        "reference": "CDTRS-2026-003",
        "subject": "Employee Leave Request",
        "department": "HR",
        "employee": "Priya Shah",
        "source": "Intranet",
        "status": "New",
        "date": "10 Aug 2026",
        "deadline": "20 Aug 2026",
        "priority": "Yellow"
    },
    {
        "reference": "CDTRS-2026-004",
        "subject": "Technical Circular",
        "department": "FCTD",
        "employee": "Amit Kumar",
        "source": "Scanned",
        "status": "Completed",
        "date": "08 Aug 2026",
        "deadline": "30 Aug 2026",
        "priority": "Green"
    },
    {
    "reference": "CDTRS-2026-005",
    "subject": "Equipment Maintenance Request",
    "department": "Maintenance",
    "employee": "Suresh Patil",
    "source": "Outlook",
    "status": "New",
    "date": "09 Aug 2026",
    "deadline": "14 Aug 2026",
    "priority": "Orange",
    "forwarded_to": "",
    "forwarded_by": "Master"
}
]


HISTORY = {
    "CDTRS-2026-001": [
        {
            "timestamp": "11 Aug 2026 09:30",
            "user": "Master",
            "action": "Document Received",
            "reference": "CDTRS-2026-001",
            "details": "Received through Outlook"
        },
        {
            "timestamp": "11 Aug 2026 09:45",
            "user": "Master",
            "action": "Routing Confirmed",
            "reference": "CDTRS-2026-001",
            "details": "Finance / Rahul Sharma"
        },
        {
            "timestamp": "11 Aug 2026 10:00",
            "user": "Master",
            "action": "Forwarded",
            "reference": "CDTRS-2026-001",
            "details": "Forwarded to Director"
        }
    ],

    "CDTRS-2026-002": [
        {
            "timestamp": "11 Aug 2026 10:05",
            "user": "Master",
            "action": "Document Received",
            "reference": "CDTRS-2026-002",
            "details": "Received through Fax"
        },
        {
            "timestamp": "11 Aug 2026 11:15",
            "user": "HOD",
            "action": "Assigned",
            "reference": "CDTRS-2026-002",
            "details": "Assigned to Amit Patil"
        }
    ]
}