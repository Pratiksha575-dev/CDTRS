from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHeaderView
)

from PySide6.QtCore import Qt, Signal

from services.inbox_service import inbox_service


class InboxPage(QWidget):

    # Sends selected document to MainWindow
    process_requested = Signal(dict)

    def __init__(self):
        super().__init__()

        self.documents = []

        self.setup_ui()
        self.load_documents()

    def setup_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            30, 25, 30, 30
        )

        main_layout.setSpacing(15)

        # --------------------------------
        # PAGE HEADER
        # --------------------------------

        title = QLabel("Inbox")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Incoming documents received from different sources."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # TABLE
        # --------------------------------

        self.table = QTableWidget()

        self.table.setColumnCount(7)

        self.table.setHorizontalHeaderLabels([
            "Source",
            "Title",
            "Type",
            "Received",
            "Status",
            "Action",
            "ID"
        ])

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        # Make columns resize nicely
        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            1, QHeaderView.Stretch
        )

        header.setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            6, QHeaderView.ResizeToContents
        )

        main_layout.addWidget(self.table)

        # --------------------------------
        # BOTTOM BUTTONS
        # --------------------------------

        button_layout = QHBoxLayout()

        self.process_button = QPushButton(
            "Process Selected Document"
        )

        self.process_button.clicked.connect(
            self.process_selected
        )

        refresh_button = QPushButton("Refresh")

        refresh_button.clicked.connect(
            self.load_documents
        )

        button_layout.addWidget(refresh_button)

        button_layout.addStretch()

        button_layout.addWidget(
            self.process_button
        )

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    # ====================================
    # LOAD INBOX
    # ====================================

    def load_documents(self):

        self.documents = (
            inbox_service.get_inbox_documents()
        )

        self.table.setRowCount(
            len(self.documents)
        )

        for row, document in enumerate(
            self.documents
        ):

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(
                    document["source"]
                )
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    document["title"]
                )
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(
                    document["file_type"]
                )
            )

            self.table.setItem(
                row,
                3,
                QTableWidgetItem(
                    document["received"]
                )
            )

            self.table.setItem(
                row,
                4,
                QTableWidgetItem(
                    document["status"]
                )
            )

            self.table.setItem(
                row,
                5,
                QTableWidgetItem(
                    "Process"
                )
            )

            self.table.setItem(
                row,
                6,
                QTableWidgetItem(
                    str(document["id"])
                )
            )

    # ====================================
    # PROCESS DOCUMENT
    # ====================================

    def process_selected(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "No Document Selected",
                "Please select a document to process."
            )

            return

        document = self.documents[row]

        self.process_requested.emit(document)