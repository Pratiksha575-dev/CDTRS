import os
from dataclasses import dataclass


def _load_env_file():
    """Attempts to load .env file from current, frontend, or root directory."""
    search_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
    ]
    for env_path in search_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
                break
            except Exception:
                pass


_load_env_file()


@dataclass
class Settings:
    """
    Centralized configuration for CDTRS Frontend.
    Reads environment variables with sensible defaults.
    """

    # 1. API Base URL (defaults to local backend http://127.0.0.1:8000/api/v1 or LAN / Cloud URL)
    api_url: str = os.getenv("CDTRS_API_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")).rstrip("/")
    
    # 2. Data source mode ('api' for live FastAPI backend, 'mock' for standalone in-memory demo)
    data_source: str = os.getenv("CDTRS_DATA_SOURCE", "api").lower()

    # Network Request Timeout in seconds
    api_timeout: float = float(os.getenv("CDTRS_API_TIMEOUT", "15.0"))

    # Application Information
    app_name: str = os.getenv("CDTRS_APP_NAME", "CDTRS")
    app_version: str = os.getenv("CDTRS_APP_VERSION", "2.0.0")

    @property
    def is_api_mode(self) -> bool:
        """Returns True if the application is configured to connect to live backend API."""
        return self.data_source == "api"

    @property
    def is_mock_mode(self) -> bool:
        """Returns True if the application is operating with local mock repository."""
        return self.data_source == "mock"

    def set_api_url(self, url: str) -> None:
        """Dynamically update the API Base URL at runtime."""
        self.api_url = url.strip().rstrip("/")

    def set_data_source(self, mode: str) -> None:
        """Dynamically update data source mode ('api' or 'mock')."""
        self.data_source = mode.strip().lower()


# Global singleton settings instance
settings = Settings()

