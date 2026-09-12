"""Central action registration for Reddit domain primitives."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[dict[str, Any]]]


class ActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, action_type: str, handler: Handler) -> None:
        if action_type in self._handlers:
            raise ValueError(f"Action already registered: {action_type}")
        self._handlers[action_type] = handler

    def get(self, action_type: str) -> Handler:
        try:
            return self._handlers[action_type]
        except KeyError as exc:
            raise ValueError(f"No handler for: {action_type}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
