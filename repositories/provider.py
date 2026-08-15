from typing import Optional

from config.settings import settings
from repositories.base import BaseRepository
from repositories.mock_repository import MockRepository
from repositories.api_repository import APIRepository

_mock_repo_instance: Optional[MockRepository] = None
_api_repo_instance: Optional[APIRepository] = None


def get_repository() -> BaseRepository:
    """
    Central repository provider for the CDTRS client.
    Returns either APIRepository or MockRepository based on centralized configuration (CDTRS_DATA_SOURCE).
    Services and UI never manually check 'if data_source == mock'.
    """
    global _mock_repo_instance, _api_repo_instance

    if settings.is_api_mode:
        if _api_repo_instance is None:
            _api_repo_instance = APIRepository()
        return _api_repo_instance
    else:
        if _mock_repo_instance is None:
            _mock_repo_instance = MockRepository()
        return _mock_repo_instance
