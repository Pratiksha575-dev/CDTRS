import sys
import json
from PySide6.QtCore import QCoreApplication, QUrl, QTimer
from PySide6.QtWebSockets import QWebSocket

app = QCoreApplication(sys.argv)

ws = QWebSocket()

def on_connected():
    print("[PASS] WebSocket Connected Successfully!")
    # Send a ping/heartbeat
    ws.sendTextMessage(json.dumps({"type": "ping"}))
    QTimer.singleShot(1000, app.quit)

def on_text(msg):
    print("[PASS] Received WebSocket Message:", msg)

def on_error(err):
    print("[ERROR] WebSocket Error:", err, ws.errorString())

def on_disconnected():
    print("[INFO] WebSocket Disconnected")

ws.connected.connect(on_connected)
ws.textMessageReceived.connect(on_text)
ws.errorOccurred.connect(on_error)
ws.disconnected.connect(on_disconnected)

ws_url = "wss://cdtrs.onrender.com/api/v1/ws"
print(f"Connecting to {ws_url}...")
ws.open(QUrl(ws_url))

# Timeout after 20 seconds
QTimer.singleShot(20000, lambda: (print("[TIMEOUT] Connection test timed out"), app.quit()))

sys.exit(app.exec())
