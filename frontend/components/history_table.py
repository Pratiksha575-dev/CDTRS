from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)


class HistoryTable(QTableWidget):

    def __init__(self):
        super().__init__()

        self.history = []

        self.setColumnCount(5)

        self.setHorizontalHeaderLabels([
            "Timestamp",
            "User",
            "Action",
            "Document",
            "Details"
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

    # ====================================
    # LOAD HISTORY
    # ====================================

    def load_history(self, history):

        self.history = history

        self.setRowCount(
            len(history)
        )

        for row, entry in enumerate(history):

            values = [
                entry.get("timestamp", ""),
                entry.get("user", ""),
                entry.get("action", ""),
                entry.get("reference", ""),
                entry.get("details", "")
            ]

            for column, value in enumerate(values):

                self.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        str(value)
                    )
                )

    # ====================================
    # GET SELECTED DOCUMENT
    # ====================================

    def get_selected_document_reference(self):

        row = self.currentRow()

        if row < 0 or row >= len(self.history):
            return None

        return self.history[row].get(
            "reference"
        )