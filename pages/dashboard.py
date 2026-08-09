from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)


class DashboardPage(QWidget):

    def __init__(self, role):
        super().__init__()

        layout = QVBoxLayout()

        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(10)

        title = QLabel(f"{role} Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Overview of your documents, tasks and activities."
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Keep remaining space below the content
        layout.addStretch()

        self.setLayout(layout)