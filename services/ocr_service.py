class OCRService:

    def extract_text(self, file_path):
        """
        Extract text from a document.

        Later:
        - PaddleOCR for printed documents
        - TrOCR for handwritten documents
        """

        print("Mock OCR:", file_path)

        return {
            "text": "",
            "confidence": 0.0
        }


ocr_service = OCRService()