"""posts.create (domain_posts.submit): submit a self/text post to a subreddit."""
from __future__ import annotations
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_camofox.interactions import click_first, fill_first
from reddit_camofox_client.domain_camofox.selectors import SUBMIT_BODY, SUBMIT_BUTTON, SUBMIT_TITLE
from reddit_camofox_client.domain_posts.schemas import PostSubmitInput


class SubmitAction:
    ACTION_TYPE = "posts.create"

    def __init__(self, session_manager, event_emitter):
        self.session_manager = session_manager
        self.event_emitter = event_emitter

    async def execute(self, envelope: ActionEnvelope) -> dict:
        cookies = envelope.input.pop("_cookies", [])
        input_data = PostSubmitInput(**envelope.input)
        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            page = await session.open_surface("reddit_submit", {"subreddit": input_data.subreddit})
            await fill_first(page, SUBMIT_TITLE, input_data.title)
            if input_data.content:
                await fill_first(page, SUBMIT_BODY, input_data.content)
            submitted = await click_first(page, SUBMIT_BUTTON)
            fresh: list[dict] = []
            try:
                fresh = await session.cookies()
            except Exception:
                pass
            result = {
                "submitted": submitted,
                "subreddit": input_data.subreddit,
                "title": input_data.title,
                "url": page.url,
                "_cookies": fresh,
            }
            await self.event_emitter.emit(
                "posts.created" if submitted else "posts.create_failed",
                {"action_id": envelope.action_id, **{k: v for k, v in result.items() if k != "_cookies"}},
                dedupe_key=f"{envelope.action_id}-submit",
            )
            return result
        finally:
            await self.session_manager.release(session)
