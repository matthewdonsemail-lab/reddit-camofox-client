"""comments.reply (domain_posts.reply): reply to a post or parent comment."""
from __future__ import annotations
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_camofox.interactions import (
    await_mount,
    click_first,
    fill_first,
    fill_focused,
)
from reddit_camofox_client.domain_camofox.selectors import COMMENT_BOX, REPLY_BUTTON
from reddit_camofox_client.domain_posts.schemas import PostReplyInput


class ReplyAction:
    ACTION_TYPE = "comments.reply"

    def __init__(self, session_manager, event_emitter):
        self.session_manager = session_manager
        self.event_emitter = event_emitter

    async def execute(self, envelope: ActionEnvelope) -> dict:
        cookies = envelope.input.pop("_cookies", [])
        input_data = PostReplyInput(**envelope.input)
        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            target = {"permalink": f"/comments/{input_data.post_id}"} if input_data.post_id else {}
            page = await session.open_surface("reddit_post", target)
            # Comments lazy-mount on scroll; ease down until Reply exists.
            mounted = await await_mount(page, REPLY_BUTTON)
            clicked = await click_first(page, [mounted] if mounted else REPLY_BUTTON)
            filled = await fill_first(page, COMMENT_BOX, input_data.text)
            if not filled:
                # Shadow-tree composer focused but unmatched: type as a user would.
                filled = await fill_focused(page, input_data.text)
            posted = await click_first(page, ["button:has-text('Comment')", "button[type='submit']"])
            fresh: list[dict] = []
            try:
                fresh = await session.cookies()
            except Exception:
                pass
            result = {
                "replied": bool(filled and posted),
                "post_id": input_data.post_id,
                "parent_id": input_data.parent_id,
                "_cookies": fresh,
            }
            await self.event_emitter.emit(
                "comments.replied" if result["replied"] else "comments.reply_failed",
                {"action_id": envelope.action_id, "post_id": input_data.post_id},
                dedupe_key=f"{envelope.action_id}-reply",
            )
            return result
        finally:
            await self.session_manager.release(session)
