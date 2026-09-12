"""Action runner dispatches envelopes to registered domain handlers."""
from __future__ import annotations

from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_actions.registry import ActionRegistry


class ActionRunner:
    def __init__(self, registry: ActionRegistry | None = None) -> None:
        self.registry = registry or ActionRegistry()

    def register(self, action_type: str, handler) -> None:
        self.registry.register(action_type, handler)

    async def run(self, envelope: ActionEnvelope) -> dict:
        handler = self.registry.get(envelope.action_type)
        envelope.status = "running"
        try:
            result = await handler(envelope)
            envelope.status = "completed"
            return result
        except Exception:
            envelope.status = "failed"
            raise
