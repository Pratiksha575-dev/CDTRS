class DocumentService:

    def create_document(self, document_data):
        """
        Create a document in the backend.

        Later:
        POST /documents
        """

        print("Mock document created:")
        print(document_data)

        return {
            "success": True,
            "message": "Document created successfully"
        }

    def get_documents(self):
        """
        Later:
        GET /documents
        """

        return []


document_service = DocumentService()