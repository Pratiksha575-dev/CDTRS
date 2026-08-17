import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWebSockets import QWebSocket

from config.settings import settings

logger = logging.getLogger("cdtrs.websocket")


class WebSocketService(QObject):
    """
    Real-time WebSocket client synchronization service for CDTRS V2.
    Connects to the FastAPI backend WebSocket stream to receive live workflow,
    document, notification, and remarks events without blocking the Qt UI thread.
    """

    connection_state_changed = Signal(bool, str)  # is_connected, status_text
    event_received = Signal(dict)                 # raw parsed event dict

    def __init__(self):
        super().__init__()
        self._ws: Optional[QWebSocket] = None
        self._is_connected: bool = False
        self._should_reconnect: bool = False
        self._reconnect_delay: float = 2.0  # Initial delay in seconds
        self._max_reconnect_delay: float = 30.0
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._do_reconnect)

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(25000)  # Ping every 25 seconds
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

    def _build_ws_url(self) -> str:
        """Derives websocket endpoint URL from current api_url."""
        base_api = settings.api_url.rstrip("/")
        parsed = urlparse(base_api)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        netloc = parsed.netloc
        path = parsed.path
        if not path.endswith("/ws"):
            ws_path = f"{path}/ws"
        else:
            ws_path = path
        return f"{scheme}://{netloc}{ws_path}"

    def connect_client(self) -> None:
        """Establishes WebSocket connection to backend if in API mode."""
        if not settings.is_api_mode:
            return

        if self._ws is not None:
            self.disconnect_client()

        self._should_reconnect = True
        self._ws = QWebSocket()
        self._ws.connected.connect(self._on_connected)
        self._ws.textMessageReceived.connect(self._on_text_message)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.errorOccurred.connect(self._on_error)

        ws_url = self._build_ws_url()
        logger.info(f"Connecting to WebSocket: {ws_url}")
        self.connection_state_changed.emit(False, "Connecting...")
        self._ws.open(QUrl(ws_url))

    def disconnect_client(self) -> None:
        """Cleanly terminates the WebSocket connection and stops reconnection timers."""
        self._should_reconnect = False
        self._reconnect_timer.stop()
        self._heartbeat_timer.stop()
        self._reconnect_delay = 2.0

        if self._ws is not None:
            try:
                self._ws.connected.disconnect(self._on_connected)
                self._ws.textMessageReceived.disconnect(self._on_text_message)
                self._ws.disconnected.disconnect(self._on_disconnected)
                self._ws.errorOccurred.disconnect(self._on_error)
            except Exception:
                pass
            self._ws.close()
            self._ws.deleteLater()
            self._ws = None

        self._is_connected = False
        self.connection_state_changed.emit(False, "Disconnected")

    def is_connected(self) -> bool:
        return self._is_connected

    # =========================================================
    # INTERNAL SOCKET HANDLERS
    # =========================================================

    def _on_connected(self) -> None:
        logger.info("WebSocket connected successfully.")
        self._is_connected = True
        self._reconnect_delay = 2.0
        self._heartbeat_timer.start()
        self.connection_state_changed.emit(True, "Live Connected")

    def _on_disconnected(self) -> None:
        logger.info("WebSocket disconnected.")
        self._is_connected = False
        self._heartbeat_timer.stop()
        self.connection_state_changed.emit(False, "Disconnected")

        if self._should_reconnect and settings.is_api_mode:
            logger.info(f"Scheduling reconnect in {self._reconnect_delay:.1f}s...")
            self._reconnect_timer.start(int(self._reconnect_delay * 1000))
            self._reconnect_delay = min(self._reconnect_delay * 1.5, self._max_reconnect_delay)

    def _on_error(self, error_code: Any) -> None:
        err_msg = self._ws.errorString() if self._ws else str(error_code)
        logger.warning(f"WebSocket error: {err_msg}")
        self.connection_state_changed.emit(False, f"Connection Error: {err_msg}")

    def _send_heartbeat(self) -> None:
        if self._ws and self._is_connected:
            try:
                self._ws.sendTextMessage(json.dumps({"type": "ping"}))
            except Exception:
                pass

    def _do_reconnect(self) -> None:
        if self._should_reconnect and settings.is_api_mode:
            self.connect_client()

    # =========================================================
    # EVENT DISPATCHING TO FRONTEND DOMAIN
    # =========================================================

    def _on_text_message(self, message_text: str) -> None:
        try:
            data = json.loads(message_text)
        except Exception:
            return

        self.event_received.emit(data)
        self._dispatch_event_to_bus(data)

    def _dispatch_event_to_bus(self, data: Dict[str, Any]) -> None:
        event_type = data.get("event_type", "").upper()
        doc_id = data.get("document_id")

        from services.event_bus import event_bus

        if event_type in ("DOCUMENT_CREATED", "INTAKE_REGISTERED"):
            event_bus.notify_inbox_updated()
            event_bus.notify_data_changed()

        elif event_type in (
            "DOCUMENT_ROUTED",
            "REMARK_UPDATED",
            "ASSIGNMENT_CREATED",
            "PROGRESS_SUBMITTED",
            "DOCUMENT_CLOSED",
            "OCR_COMPLETED",
            "ATTACHMENT_ADDED",
        ):
            if doc_id:
                try:
                    from services.document_service import document_service
                    updated_doc = document_service.get_document(doc_id)
                    if updated_doc:
                        event_bus.notify_document_updated(updated_doc)
                    else:
                        event_bus.notify_workflow_updated(doc_id)
                except Exception:
                    event_bus.notify_workflow_updated(doc_id)
            else:
                event_bus.notify_data_changed()

            event_bus.notify_inbox_updated()
            event_bus.notify_notifications_updated()
            event_bus.notify_data_changed()

        elif event_type in ("NOTIFICATION", "REMINDER"):
            event_bus.notify_notifications_updated()
            event_bus.notify_data_changed()

        else:
            event_bus.notify_data_changed()


# Global singleton instance
websocket_service = WebSocketService()
