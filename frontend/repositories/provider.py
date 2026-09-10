from typing import Optional
from repositories.base import BaseRepository
from repositories.api_repository import APIRepository

_api_repo_instance: Optional[APIRepository] = None


def get_repository() -> BaseRepository:
    """
    Central repository provider for the CDTRS client.
    Returns either APIRepository or MockRepository based on centralized configuration (CDTRS_DATA_SOURCE).
    Services and UI never manually check 'if data_source == mock'.
    """
    global _mock_repo_instance, _api_repo_instance

    if _api_repo_instance is None:
        _api_repo_instance = APIRepository()
    return _api_repo_instance

