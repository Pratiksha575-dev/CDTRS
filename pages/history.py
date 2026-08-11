from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton
)

from components.history_table import HistoryTable
from data.mock_data import HISTORY


class HistoryPage(QWidget):

    def __init__(self):
        super().__init__()

        self.all_history = self.flatten_history()

        self.setup_ui()
        self.load_history()

    # ====================================
    # CONVERT HISTORY DICTIONARY
    # TO ONE LIST
    # ====================================

    def flatten_history(self):

        history_list = []

        for document_history in HISTORY.values():

            history_list.extend(
                document_history
            )

        return history_list

    # ====================================
    # UI
    # ====================================

    def setup_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            30, 25, 30, 30
        )

        main_layout.setSpacing(15)

        # --------------------------------
        # HEADER
        # --------------------------------

        title = QLabel(
            "History / Audit"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "View the complete document activity history."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------

        filter_layout = QHBoxLayout()

        self.user_filter = QComboBox()

        self.user_filter.addItems([
            "All Users",
            "Master",
            "Director",
            "HOD",
            "Employee"
        ])

        self.action_filter = QComboBox()

        self.action_filter.addItems([
            "All Actions",
            "Document Received",
            "Routing Confirmed",
            "Forwarded",
            "Remark Added",
            "Assigned",
            "Completed"
        ])

        apply_button = QPushButton(
            "Apply Filters"
        )

        apply_button.clicked.connect(
            self.apply_filters
        )

        clear_button = QPushButton(
            "Clear"
        )

        clear_button.clicked.connect(
            self.clear_filters
        )

        filter_layout.addWidget(
            self.user_filter
        )

        filter_layout.addWidget(
            self.action_filter
        )

        filter_layout.addWidget(
            apply_button
        )

        filter_layout.addWidget(
            clear_button
        )

        filter_layout.addStretch()

        main_layout.addLayout(
            filter_layout
        )

        # --------------------------------
        # HISTORY TABLE
        # --------------------------------

        self.table = HistoryTable()

        main_layout.addWidget(
            self.table
        )

        # --------------------------------
        # FOOTER
        # --------------------------------

        self.count_label = QLabel(
            "0 activities"
        )

        self.count_label.setObjectName(
            "pageSubtitle"
        )

        main_layout.addWidget(
            self.count_label
        )

        self.setLayout(
            main_layout
        )

    # ====================================
    # LOAD
    # ====================================

    def load_history(self):

        self.table.load_history(
            self.all_history
        )

        self.update_count(
            self.all_history
        )

    # ====================================
    # FILTER
    # ====================================

    def apply_filters(self):

        user = self.user_filter.currentText()
        action = self.action_filter.currentText()

        filtered = []

        for entry in self.all_history:

            if (
                user != "All Users"
                and entry.get("user") != user
            ):
                continue

            if (
                action != "All Actions"
                and entry.get("action") != action
            ):
                continue

            filtered.append(entry)

        self.table.load_history(
            filtered
        )

        self.update_count(
            filtered
        )

    # ====================================
    # CLEAR
    # ====================================

    def clear_filters(self):

        self.user_filter.setCurrentIndex(0)
        self.action_filter.setCurrentIndex(0)

        self.load_history()

    # ====================================
    # COUNT
    # ====================================

    def update_count(self, history):

        count = len(history)

        self.count_label.setText(
            f"{count} activities"
        )