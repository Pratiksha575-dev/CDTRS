from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget
)

from api.client import api_client


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", note: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")

        note_label = QLabel(note)
        note_label.setObjectName("statNote")
        note_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(note_label)

    def set_value(self, value: Any) -> None:
        self.value_label.setText(str(value))


class AdminDashboardPage(QWidget):
    """Standalone Admin overview. No operational workflow controls live here."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("adminDashboardPage")

        self.users_card = StatCard("USERS", note="Configured application accounts")
        self.active_users_card = StatCard("ACTIVE USERS", note="Accounts currently enabled")
        self.departments_card = StatCard("DEPARTMENTS", note="Configured organisational units")
        self.audit_card = StatCard("ADMIN AUDIT", note="Recorded administrator changes")

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        cards.addWidget(self.users_card, 0, 0)
        cards.addWidget(self.active_users_card, 0, 1)
        cards.addWidget(self.departments_card, 0, 2)
        cards.addWidget(self.audit_card, 0, 3)
        for col in range(4):
            cards.setColumnStretch(col, 1)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Administration")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Manage users, work contexts, departments, system configuration, "
            "and the administrator audit history."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.status = QLabel("Loading…")
        self.status.setObjectName("muted")
        header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignRight)

        refresh = QPushButton("Refresh")
        refresh.setObjectName("secondaryButton")
        refresh.clicked.connect(self.load_dashboard)
        header.addWidget(refresh)

        actions_title = QLabel("Quick actions")
        actions_title.setObjectName("sectionTitle")

        actions = QHBoxLayout()
        for text in ("User Configuration", "Department Configuration", "System Configuration", "Audit History"):
            btn = QPushButton(text)
            btn.setObjectName("actionButton")
            # NavigationRegistry/MainWindow owns actual page navigation.
            # These buttons intentionally expose page names as properties.
            btn.setProperty("page_name", text)
            actions.addWidget(btn)
        actions.addStretch(1)

        activity_title = QLabel("Recent administrator changes")
        activity_title.setObjectName("sectionTitle")

        self.activity_box = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_box)
        self.activity_layout.setContentsMargins(0, 0, 0, 0)
        self.activity_layout.setSpacing(8)

        activity_scroll = QScrollArea()
        activity_scroll.setWidgetResizable(True)
        activity_scroll.setFrameShape(QFrame.Shape.NoFrame)
        activity_scroll.setWidget(self.activity_box)
        activity_scroll.setMinimumHeight(260)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 18, 20, 18)
        content_layout.setSpacing(14)
        content_layout.addLayout(header)
        content_layout.addLayout(cards)
        content_layout.addWidget(actions_title)
        content_layout.addLayout(actions)
        content_layout.addWidget(activity_title)
        content_layout.addWidget(activity_scroll, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(content)

        self.setStyleSheet("""
            QWidget#adminDashboardPage { background: #f6f8fb; }
            QLabel#pageTitle { font-size: 24px; font-weight: 750; color: #172033; }
            QLabel#sectionTitle { font-size: 15px; font-weight: 700; color: #172033; }
            QLabel#muted { color: #667085; }
            QFrame#statCard {
                background: white; border: 1px solid #e4e7ec; border-radius: 12px;
            }
            QLabel#statTitle { color: #667085; font-size: 11px; font-weight: 700; }
            QLabel#statValue { color: #172033; font-size: 28px; font-weight: 800; }
            QLabel#statNote { color: #667085; font-size: 11px; }
            QPushButton {
                min-height: 34px; border: 1px solid #d0d5dd; border-radius: 8px;
                background: white; padding: 0 12px;
            }
            QPushButton:hover { background: #f2f4f7; }
            QPushButton#actionButton { min-height: 42px; font-weight: 600; }
            QPushButton#secondaryButton { font-weight: 600; }
            QFrame#activityItem {
                background: white; border: 1px solid #e4e7ec; border-radius: 9px;
            }
        """)

        self.load_dashboard()

    @staticmethod
    def _as_list(data: Any, *keys: str) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def load_dashboard(self) -> None:
        try:
            users = self._as_list(api_client.get("/admin/users"), "users", "items")
            departments = self._as_list(
                api_client.get("/admin/departments"), "departments", "items"
            )
            audit = self._as_list(
                api_client.get("/admin/audit-logs"), "audit_logs", "logs", "items"
            )

            self.users_card.set_value(len(users))
            self.active_users_card.set_value(
                sum(bool(u.get("is_active", True)) for u in users)
            )
            self.departments_card.set_value(len(departments))
            self.audit_card.set_value(len(audit))

            self._render_activity(audit[:8])
            self.status.setText("Updated")
        except Exception as exc:
            self.status.setText("Unable to load")
            self._render_activity([])
            QMessageBox.warning(
                self,
                "Admin Dashboard",
                f"Unable to load administrator data.\n\n{exc}",
            )

    def _render_activity(self, rows: List[Dict[str, Any]]) -> None:
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not rows:
            label = QLabel("No administrator changes have been recorded.")
            label.setObjectName("muted")
            self.activity_layout.addWidget(label)
            self.activity_layout.addStretch(1)
            return

        for row in rows:
            card = QFrame()
            card.setObjectName("activityItem")

            action = str(row.get("action") or "ADMIN ACTION")
            actor = str(row.get("username") or row.get("user_name") or "Unknown admin")
            target = str(row.get("entity_type") or "System")
            details = str(row.get("description") or row.get("details") or "")
            timestamp = str(row.get("created_at") or "")

            layout = QVBoxLayout(card)
            layout.setContentsMargins(13, 10, 13, 10)
            layout.setSpacing(3)

            headline = QLabel(f"{action}  •  {actor}")
            headline.setStyleSheet("font-weight: 700; color: #172033;")
            meta = QLabel(f"{target}   {timestamp}")
            meta.setObjectName("muted")
            body = QLabel(details)
            body.setObjectName("muted")
            body.setWordWrap(True)

            layout.addWidget(headline)
            layout.addWidget(meta)
            if details:
                layout.addWidget(body)

            self.activity_layout.addWidget(card)

        self.activity_layout.addStretch(1)


AdminDashboard = AdminDashboardPage
