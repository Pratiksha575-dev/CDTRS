import os
from typing import Any, Callable, Dict, Optional, Tuple, Union

from config.settings import settings
from api.exceptions import (
    APIException,
    NetworkError,
    TimeoutError,
    raise_for_status_code,
)

try:
    import requests
    HAS_REQUESTS = True
    _ReqTimeout = requests.exceptions.Timeout
    _ReqConnError = requests.exceptions.ConnectionError
    _ReqException = requests.exceptions.RequestException
except ImportError:
    requests = None
    HAS_REQUESTS = False
    _ReqTimeout = TimeoutError
    _ReqConnError = NetworkError
    _ReqException = APIException

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False
    class QObject:
        pass
    class QRunnable:
        def __init__(self): pass
        def setAutoDelete(self, val: bool): pass
    class QThreadPool:
        @staticmethod
        def globalInstance(): return None
    class _DummySignal:
        def emit(self, *args, **kwargs): pass
        def connect(self, *args, **kwargs): pass
    def Signal(*args): return _DummySignal()


class WorkerSignals(QObject):
    """
    Qt Signals emitted by background ApiWorker tasks to communicate with UI safely.
    """
    started = Signal()
    finished = Signal(object)      # Emits the returned result object
    error = Signal(Exception)      # Emits any caught APIException or standard Exception
    progress = Signal(int)         # Optional progress indicator (0 - 100)


class ApiWorker(QRunnable):
    """
    QRunnable background task for executing synchronous API calls off the Qt UI thread.
    Prevents desktop UI freezing during network latency or large file transfers.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        """Executes the callable in thread pool and emits result or error signal."""
        self.signals.started.emit()
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as ex:
            self.signals.error.emit(ex)


class APIClient:
    """
    Centralized HTTP client for all CDTRS backend interactions.
    Handles Base URL configuration, authentication token injection, request timeouts,
    JSON serialization, file uploads/downloads, error normalization, and non-blocking execution.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self._custom_base_url = base_url
        self._custom_timeout = timeout
        self._auth_token: Optional[str] = None
        self._session = requests.Session() if HAS_REQUESTS else None

    @property
    def base_url(self) -> str:
        """Resolves Base URL from custom property or global settings."""
        if self._custom_base_url:
            return self._custom_base_url.rstrip("/")
        return settings.api_url.rstrip("/")

    @property
    def timeout(self) -> float:
        """Resolves timeout from custom property or global settings."""
        if self._custom_timeout is not None:
            return self._custom_timeout
        return settings.api_timeout

    def set_auth_token(self, token: Optional[str]) -> None:
        """Sets the active authentication token (e.g. JWT Bearer token)."""
        self._auth_token = token

    def clear_auth_token(self) -> None:
        """Clears stored authentication token upon logout."""
        self._auth_token = None

    def get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Constructs headers including Authorization Bearer token if present."""
        headers = {
            "Accept": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        if custom_headers:
            headers.update(custom_headers)
        return headers

    def _parse_response(self, response: Any) -> Any:
        """Parses response body into JSON or plain text with typed error handling."""
        status_code = response.status_code

        # Attempt to parse response body as JSON
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if not (200 <= status_code < 300):
            # Extract detail message if provided in standard FastAPI format
            detail = None
            if isinstance(data, dict):
                detail = data.get("detail") or data.get("message")
            elif isinstance(data, str) and data.strip():
                detail = data

            raise_for_status_code(status_code, detail_message=detail, error_data=data)

        return data

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Synchronous request execution core.
        Catches network and timeout errors and converts them to typed exceptions.
        """
        if not HAS_REQUESTS:
            raise NetworkError("The 'requests' package is required for live API communication. Please run: pip install requests")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req_headers = self.get_headers(headers)
        req_timeout = timeout or self.timeout

        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                files=files,
                headers=req_headers,
                timeout=req_timeout
            )
            return self._parse_response(response)

        except _ReqTimeout as ex:
            raise TimeoutError(f"Request to {endpoint} timed out after {req_timeout}s.", error_data=str(ex))
        except _ReqConnError as ex:
            raise NetworkError(f"Connection failed when reaching {self.base_url}.", error_data=str(ex))
        except _ReqException as ex:
            raise APIException(f"Network request failed: {str(ex)}", error_data=str(ex))

    # --- Standard HTTP Method Helpers ---

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Optional[Any] = None, data: Optional[Any] = None, **kwargs: Any) -> Any:
        return self.request("POST", endpoint, json=json, data=data, **kwargs)

    def put(self, endpoint: str, json: Optional[Any] = None, data: Optional[Any] = None, **kwargs: Any) -> Any:
        return self.request("PUT", endpoint, json=json, data=data, **kwargs)

    def patch(self, endpoint: str, json: Optional[Any] = None, data: Optional[Any] = None, **kwargs: Any) -> Any:
        return self.request("PATCH", endpoint, json=json, data=data, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> Any:
        return self.request("DELETE", endpoint, **kwargs)

    # --- File Upload & Download Operations ---

    def upload(
        self,
        endpoint: str,
        file_path_or_tuple: Union[str, Tuple[str, Any, str]],
        field_name: str = "file",
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        """
        Uploads a file as multipart/form-data.
        `file_path_or_tuple` can be an absolute file path or a tuple: (filename, file_bytes, content_type)
        """
        opened_file = None
        try:
            if isinstance(file_path_or_tuple, str):
                if not os.path.exists(file_path_or_tuple):
                    raise FileNotFoundError(f"File not found for upload: {file_path_or_tuple}")
                opened_file = open(file_path_or_tuple, "rb")
                filename = os.path.basename(file_path_or_tuple)
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                    if ext == "pdf":
                        content_type = "application/pdf"
                    elif ext in ("xlsx", "xls"):
                        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    elif ext in ("docx", "doc"):
                        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif ext in ("png", "jpg", "jpeg"):
                        content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
                    elif ext == "txt":
                        content_type = "text/plain"
                    else:
                        content_type = "application/pdf"
                files = {field_name: (filename, opened_file, content_type)}
            else:
                files = {field_name: file_path_or_tuple}

            return self.request("POST", endpoint, data=extra_data, files=files, **kwargs)
        finally:
            if opened_file:
                opened_file.close()

    def download(
        self,
        endpoint: str,
        dest_file_path: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Downloads a binary stream and writes to `dest_file_path`.
        Returns the destination file path upon completion.
        """
        if not HAS_REQUESTS:
            raise NetworkError("The 'requests' package is required for live API communication. Please run: pip install requests")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req_headers = self.get_headers()
        req_timeout = timeout or self.timeout

        try:
            response = self._session.get(
                url,
                params=params,
                headers=req_headers,
                timeout=req_timeout,
                stream=True
            )
            if not (200 <= response.status_code < 300):
                self._parse_response(response)

            os.makedirs(os.path.dirname(os.path.abspath(dest_file_path)), exist_ok=True)
            with open(dest_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return dest_file_path

        except _ReqTimeout as ex:
            raise TimeoutError(f"Download from {endpoint} timed out.", error_data=str(ex))
        except _ReqConnError as ex:
            raise NetworkError(f"Connection failed during download.", error_data=str(ex))
        except _ReqException as ex:
            raise APIException(f"Download failed: {str(ex)}", error_data=str(ex))

    # --- Asynchronous Background Dispatch for PySide6 ---

    def execute_async(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_started: Optional[Callable[[], None]] = None,
        **kwargs: Any
    ) -> ApiWorker:
        """
        Convenience helper to run any API client method in Qt's QThreadPool asynchronously.
        Connects success, error, and started callbacks to worker signals.
        """
        worker = ApiWorker(fn, *args, **kwargs)
        if on_started:
            worker.signals.started.connect(on_started)
        if on_success:
            worker.signals.finished.connect(on_success)
        if on_error:
            worker.signals.error.connect(on_error)

        QThreadPool.globalInstance().start(worker)
        return worker


# Global singleton client instance
api_client = APIClient()
