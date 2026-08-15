from typing import List, Optional
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.notification import NotificationModel
from services.notification_service import notification_service


class NotificationBellWidget(QWidget):
    """
    Reusable notification bell widget displaying unread activity badge.
    Consumes NotificationService rather than hardcoded data.
    """

    notification_clicked = Signal(object)  # Emits NotificationModel

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notifications: List[NotificationModel] = []
        self.setup_ui()
        self.refresh()
        from services.event_bus import event_bus
        event_bus.notifications_updated.connect(self.refresh)
        event_bus.data_changed.connect(self.refresh)

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.bell_button = QPushButton("🔔")
        self.bell_button.setFixedSize(36, 36)
        self.bell_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #E2E8F0;
                border-radius: 18px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
        """)
        self.bell_button.clicked.connect(self._handle_click)

        self.badge = QLabel("0")
        self.badge.setFixedSize(18, 18)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet("""
            QLabel {
                background-color: #E11D48;
                color: white;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.badge.setVisible(False)

        layout.addWidget(self.bell_button)
        layout.addWidget(self.badge)
        self.setLayout(layout)

    def refresh(self) -> None:
        """Queries NotificationService for active unread alerts."""
        try:
            self.notifications = notification_service.get_notifications(unread_only=True)
            unread_count = len(self.notifications)
            if unread_count > 0:
                self.badge.setText(str(unread_count if unread_count <= 99 else "99+"))
                self.badge.setVisible(True)
            else:
                self.badge.setVisible(False)
        except Exception:
            self.badge.setVisible(False)

    def _handle_click(self) -> None:
        if self.notifications:
            self.notification_clicked.emit(self.notifications[0])
