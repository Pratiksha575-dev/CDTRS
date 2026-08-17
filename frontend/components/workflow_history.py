from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)


class WorkflowHistory(QFrame):

    def __init__(self, history=None):
        super().__init__()

        self.history = history or []

        self.setObjectName(
            "contentCard"
        )

        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            20, 20, 20, 20
        )

        layout.setSpacing(12)

        # --------------------------------
        # TITLE
        # --------------------------------

        title = QLabel(
            "Workflow History"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(title)

        # --------------------------------
        # TABLE
        # --------------------------------

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([
            "Timestamp",
            "User",
            "Action",
            "Document",
            "Details"
        ])

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(
            self.table
        )

        self.setLayout(layout)

        self.load_history()

    # ====================================
    # LOAD HISTORY
    # ====================================

    def load_history(self):

        self.table.setRowCount(
            len(self.history)
        )

        for row, entry in enumerate(
            self.history
        ):

            values = [
                entry.get(
                    "timestamp",
                    ""
                ),
                entry.get(
                    "user",
                    ""
                ),
                entry.get(
                    "action",
                    ""
                ),
                entry.get(
                    "reference",
                    ""
                ),
                entry.get(
                    "details",
                    ""
                )
            ]

            for column, value in enumerate(
                values
            ):

                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        str(value)
                    )
                )

    # ====================================
    # UPDATE HISTORY
    # ====================================

    def set_history(self, history):

        self.history = history or []

        self.load_history()