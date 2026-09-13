"""posts.search: query-scoped search within a subreddit (or site-wide)."""
from __future__ import annotations
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_posts.schemas import PostSearchInput, PostSearchOutput


class PostsSearchAction:
    ACTION_TYPE = "posts.search"

    def __init__(self, session_manager, normalizer, event_emitter):
        self.session_manager = session_manager
        self.normalizer = normalizer
        self.event_emitter = event_emitter

    async def execute(self, envelope: ActionEnvelope):
        cookies = envelope.input.pop("_cookies", [])
        input_data = PostSearchInput(**envelope.input)
        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            page = await session.open_surface("reddit_search", {
                "query": input_data.query,
                "subreddit": input_data.subreddit,
            })
            try:
                from reddit_camofox_client.domain_camofox.constants import SCROLL_VIEWPORT_FRACTION
                from reddit_camofox_client.domain_camofox.scroll import human_scroll_by

                vp = page.viewport_size or {"height": 800}
                await human_scroll_by(page, vp["height"] * SCROLL_VIEWPORT_FRACTION)
            except Exception:
                pass
            raw = await session.execute("reddit_search", {
                "_page": page, "limit": input_data.limit,
                "query": input_data.query, "subreddit": input_data.subreddit, "sort": input_data.sort,
            })
            records = []
            for post in raw.get("results", []):
                post.setdefault("subreddit", input_data.subreddit)
                rec = self.normalizer.normalize(raw=post, account_id=envelope.account_id, source_action="posts.search")
                records.append(rec)
            fresh: list[dict] = []
            try:
                fresh = await session.cookies()
            except Exception:
                pass
            return PostSearchOutput(
                results=[r.model_dump(mode="json") for r in records],
                matched_subreddits=[input_data.subreddit] if input_data.subreddit else [],
                cookies=fresh,
            )
        finally:
            await self.session_manager.release(session)
