from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)

from PySide6.QtCore import Signal


class DocumentTable(QTableWidget):

    document_selected = Signal(dict)

    def __init__(self):
        super().__init__()

        self.documents = []

        self.setColumnCount(7)

        self.setHorizontalHeaderLabels([
            "Reference",
            "Subject",
            "Department",
            "Status",
            "Deadline",
            "Source",
            "Priority"
        ])

        self.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.itemSelectionChanged.connect(
            self.on_selection_changed
        )

    def load_documents(self, documents):

        self.documents = documents

        self.setRowCount(len(documents))

        for row, document in enumerate(documents):

            values = [
                document.get("reference", ""),
                document.get("subject", ""),
                document.get("department", ""),
                document.get("status", ""),
                document.get("deadline", ""),
                document.get("source", ""),
                document.get("priority", "")
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                self.setItem(
                    row,
                    column,
                    item
                )

    def on_selection_changed(self):

        row = self.currentRow()

        if 0 <= row < len(self.documents):

            self.document_selected.emit(
                self.documents[row]
            )

    def get_selected_document(self):

        row = self.currentRow()

        if 0 <= row < len(self.documents):
            return self.documents[row]

        return None