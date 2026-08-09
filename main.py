import sys
from PySide6.QtWidgets import QApplication,QWidget

from ui.login import LoginWindow

app=QApplication(sys.argv)

with open("styles/theme.qss","r",encoding="utf-8") as file:
    app.setStyleSheet(file.read())

window=LoginWindow()
window.show()
sys.exit(app.exec())
