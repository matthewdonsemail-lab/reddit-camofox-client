"""subreddits.search: find communities matching a query."""
from __future__ import annotations
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_subreddits.schemas import SubredditSearchInput, SubredditSearchOutput


class SubredditsSearchAction:
    ACTION_TYPE = "subreddits.search"

    def __init__(self, session_manager, event_emitter):
        self.session_manager = session_manager
        self.event_emitter = event_emitter

    async def execute(self, envelope: ActionEnvelope) -> SubredditSearchOutput:
        cookies = envelope.input.pop("_cookies", [])
        input_data = SubredditSearchInput(**envelope.input)
        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            page = await session.open_surface("reddit_search", {"query": f"subreddit:{input_data.query}"})
            raw = await session.execute("reddit_subreddit_search", {
                "_page": page, "limit": input_data.limit, "query": input_data.query,
            })
            results = [
                {"name": r.get("text", "")[:100], "query": input_data.query}
                for r in raw.get("results", [])[: input_data.limit]
            ]
            fresh: list[dict] = []
            try:
                fresh = await session.cookies()
            except Exception:
                pass
            await self.event_emitter.emit(
                "subreddits.search_completed",
                {"action_id": envelope.action_id, "results": len(results)},
                dedupe_key=f"{envelope.action_id}-completed",
            )
            return SubredditSearchOutput(results=results, cookies=fresh)
        finally:
            await self.session_manager.release(session)
