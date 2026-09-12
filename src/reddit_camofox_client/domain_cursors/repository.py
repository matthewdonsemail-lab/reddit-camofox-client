"""Storage interface for cursors: records COMMIT before the cursor advances."""
from __future__ import annotations
from abc import ABC, abstractmethod
from reddit_camofox_client.domain_cursors.models import Cursor


class CursorRepository(ABC):
    @abstractmethod
    async def load(self, cursor_key: str, account_id: str, scope_key: str) -> Cursor | None: ...

    @abstractmethod
    async def save(self, cursor: Cursor) -> None: ...


class InMemoryCursorRepository(CursorRepository):
    """Dev/test implementation: not durable across restarts."""

    def __init__(self) -> None:
        self._store: dict[str, Cursor] = {}

    def _key(self, cursor_key: str, account_id: str, scope_key: str) -> str:
        return f"{account_id}:{cursor_key}:{scope_key}"

    async def load(self, cursor_key: str, account_id: str, scope_key: str) -> Cursor | None:
        return self._store.get(self._key(cursor_key, account_id, scope_key))

    async def save(self, cursor: Cursor) -> None:
        key = self._key(cursor.cursor_key, cursor.account_id, cursor.scope_key)
        self._store[key] = cursor
