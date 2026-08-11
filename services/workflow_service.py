from datetime import datetime

from data.mock_data import DOCUMENTS, HISTORY


class WorkflowService:

    @staticmethod
    def forward_to_director(document):

        print(
            "Forwarding document:",
            document
        )

        # --------------------------------
        # Find matching document
        # --------------------------------

        matched_document = None

        incoming_reference = document.get(
            "reference"
        )

        incoming_id = document.get(
            "id"
        )

        incoming_title = document.get(
            "title",
            document.get("subject", "")
        )

        for item in DOCUMENTS:

            # 1. Match by reference
            if (
                incoming_reference
                and item.get("reference")
                == incoming_reference
            ):
                matched_document = item
                break

            # 2. Match by ID
            if (
                incoming_id is not None
                and item.get("id")
                == incoming_id
            ):
                matched_document = item
                break

            # 3. Match by title / subject
            if (
                incoming_title
                and item.get("subject")
                == incoming_title
            ):
                matched_document = item
                break

        # --------------------------------
        # No match
        # --------------------------------

        if matched_document is None:

            print(
                "ERROR: Document could not be "
                "matched with DOCUMENTS"
            )

            return False

        # --------------------------------
        # Get actual system reference
        # --------------------------------

        actual_reference = matched_document.get(
            "reference"
        )

        print(
            "Matched document:",
            actual_reference
        )

        # --------------------------------
        # Update shared document
        # --------------------------------

        matched_document["status"] = (
            "Director Review"
        )

        matched_document["forwarded_to"] = (
            "Director"
        )

        matched_document["forwarded_by"] = (
            "Master"
        )

        # --------------------------------
        # Update current document
        # --------------------------------

        document["reference"] = (
            actual_reference
        )

        document["status"] = (
            "Director Review"
        )

        document["forwarded_to"] = (
            "Director"
        )

        document["forwarded_by"] = (
            "Master"
        )

        # --------------------------------
        # Add workflow history
        # --------------------------------

        if actual_reference not in HISTORY:

            HISTORY[actual_reference] = []

        HISTORY[actual_reference].append({

            "timestamp":
                datetime.now().strftime(
                    "%d %b %Y %H:%M"
                ),

            "user": "Master",

            "action": "Forwarded",

            "reference":
                actual_reference,

            "details":
                "Forwarded to Director"
        })

        print(
            f"SUCCESS: {actual_reference} "
            "forwarded to Director"
        )

        return True

    # ====================================
    # DIRECTOR INBOX
    # ====================================

    @staticmethod
    def get_director_inbox():

        inbox = []

        for document in DOCUMENTS:

            if (
                document.get("forwarded_to")
                == "Director"
            ):
                inbox.append(document)

        print(
            "Director Inbox:",
            [
                document.get("reference")
                for document in inbox
            ]
        )

        return inbox