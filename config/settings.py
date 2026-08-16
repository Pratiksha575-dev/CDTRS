import os
from dataclasses import dataclass


@dataclass
class Settings:
    """
    Centralized configuration for CDTRS Frontend.
    Reads environment variables with sensible defaults.
    """

    # Backend API Base URL (Never hardcoded in individual pages)
    api_url: str = os.getenv("CDTRS_API_URL", "https://cdtrs.onrender.com/api/v1").rstrip("/")

    # Data Source Mode: 'api' for real backend, 'mock' for local development/testing
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
