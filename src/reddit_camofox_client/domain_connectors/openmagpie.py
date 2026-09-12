"""Adapter to wire Reddit domain actions into OpenMagpie (John parity)."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import ClassVar

from reddit_camofox_client.domain_accounts.login import RedditLogin
from reddit_camofox_client.domain_actions.actions import build_default_runner
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_actions.runner import ActionRunner
from reddit_camofox_client.domain_camofox.session_manager import CamofoxSessionManager
from reddit_camofox_client.domain_cursors.repository import InMemoryCursorRepository
from reddit_camofox_client.domain_events.emitter import InMemoryEventEmitter
from reddit_camofox_client.domain_records.normalization import PostNormalizer


class RedditCamofoxConnector:
    kind: ClassVar[str] = "reddit_subreddit"

    def __init__(self) -> None:
        self.session_manager = CamofoxSessionManager()
        self.cursor_repo = InMemoryCursorRepository()
        self.emitter = InMemoryEventEmitter()
        self.normalizer = PostNormalizer()
        self.runner: ActionRunner = build_default_runner(
            self.session_manager, self.cursor_repo, self.emitter
        )

    @staticmethod
    def _pop_cookies(input_data: dict) -> list[dict]:
        return input_data.pop("_cookies", [])

    @staticmethod
    async def _extract_cookies(session) -> list[dict]:
        try:
            return await session.cookies()
        except Exception:
            return []

    async def _acquire(self, envelope: ActionEnvelope) -> tuple:
        cookies = self._pop_cookies(envelope.input)
        session = await self.session_manager.acquire(
            envelope.account_id,
            proxy_config=envelope.input.get("proxy_config"),
            storage_state_path=envelope.input.get("storage_state_path"),
            cookies=cookies,
        )
        return session, cookies

    async def _release(self, session, result: dict) -> dict:
        try:
            fresh = await self._extract_cookies(session)
            if fresh:
                result["_cookies"] = fresh
        except Exception:
            pass
        await self.session_manager.release(session)
        return result

    async def poll(self, spec: dict, since: datetime | None = None) -> Iterator[dict]:
        envelope = ActionEnvelope(
            action_id=f"poll-{datetime.now().timestamp()}",
            action_type="posts.listen",
            account_id=spec.get("account_id", "default"),
            input=spec,
            idempotency_key=f"poll-{spec.get('subreddits', '')}-{since}",
        )
        result = await self.runner.run(envelope)
        if hasattr(result, "model_dump"):
            result = result.model_dump(mode="json")
        for record in result.get("new_posts", result.get("results", [])):
            yield record
