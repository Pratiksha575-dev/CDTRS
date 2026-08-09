import sys

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QPushButton
)

from PySide6.QtCore import Qt
from services.auth_service import authenticate
from ui.main_window import MainWindow

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.resize(700, 500)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)


        #login card
        card=QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(400)

        card_layout=QVBoxLayout()
        card_layout.setContentsMargins(35,35,35,35)
        card_layout.setSpacing(15)

        #title
        title=QLabel("CDTRS")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle=QLabel(
            "Centralised Document Tracking and Routing System"
        )

        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        username_label=QLabel("Username")
        self.username_input=QLineEdit()
        self.username_input.setPlaceholderText("Username")

        password_label=QLabel("Password")
        self.password_input=QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button=QPushButton("Login")
        self.login_button.clicked.connect(self.login)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)

        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(10)

        card_layout.addWidget(self.login_button)
        card.setLayout(card_layout)

        main_layout.addWidget(card)
        self.setLayout(main_layout)


    def login(self):
        username=self.username_input.text().strip()
        password=self.password_input.text()

        user=authenticate(username,password)
        if user:

            print("Login Successful")
            print("Username:", user["username"])
            print("Role:", user["role"])

            self.main_window = MainWindow(
                user["username"],
                user["role"]
            )

            self.main_window.show()
            self.close()

