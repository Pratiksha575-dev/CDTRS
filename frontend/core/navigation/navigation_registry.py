"""CDTRS context-aware navigation registry."""

from typing import Dict, List

from models.enums import RoleEnum


class NavigationRegistry:
    """Central definition of pages available to each operational context."""

    _MENUS: Dict[str, List[str]] = {
        RoleEnum.DIRECTOR_SECRETARY.value: [
            "Dashboard", "Inbox", "Document Processing",
            "Documents", "History / Audit",
        ],
        RoleEnum.DIRECTOR.value: [
            "Dashboard", "Review Queue", "History / Audit",
        ],
        RoleEnum.HOD.value: [
            "Dashboard", "Department Tasks", "History / Audit",
        ],
        RoleEnum.TSO.value: [
            "Dashboard", "My Tasks", "History / Audit",
        ],
        RoleEnum.EMPLOYEE.value: [
            "Dashboard", "My Tasks", "History / Audit",
        ],
        RoleEnum.ADMINISTRATOR.value: [
            "Dashboard", "Admin Suite", "Documents", "History / Audit",
        ],
        "Read-only User": [
            "Dashboard", "Documents", "History / Audit",
        ],
    }

    @classmethod
    def get_items(cls, context_type: str) -> List[str]:
        normalized = RoleEnum.normalize(context_type)
        return list(cls._MENUS.get(
            normalized,
            ["Dashboard", "My Tasks", "History / Audit"],
        ))

    @classmethod
    def is_valid_page(cls, context_type: str, page_key: str) -> bool:
        return page_key in cls.get_items(context_type)

    @classmethod
    def all_contexts(cls) -> List[str]:
        return list(cls._MENUS.keys())
