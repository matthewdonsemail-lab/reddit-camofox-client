"""posts.create (domain_posts.submit): submit a self/text post to a subreddit."""
from __future__ import annotations

import re
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_camofox.interactions import click_first, fill_first
from reddit_camofox_client.domain_camofox.selectors import SUBMIT_BODY, SUBMIT_BUTTON, SUBMIT_TITLE
from reddit_camofox_client.domain_posts.schemas import PostSubmitInput

_POST_URL_RE = re.compile(r"/r/[^/]+/comments/([A-Za-z0-9]+)/")


def extract_post_id(url: str) -> str:
    match = _POST_URL_RE.search(url or "")
    return match.group(1) if match else ""


class SubmitAction:
    ACTION_TYPE = "posts.create"

    def __init__(self, session_manager, event_emitter):
        self.session_manager = session_manager
        self.event_emitter = event_emitter

    async def execute(self, envelope: ActionEnvelope) -> dict:
        cookies = envelope.input.pop("_cookies", [])
        input_data = PostSubmitInput(**envelope.input)
        if not input_data.title.strip():
            raise ValueError("posts.create needs a non-empty title")
        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            page = await session.open_surface("reddit_submit", {"subreddit": input_data.subreddit})
            jar = await session.cookies()
            from reddit_camofox_client.domain_camofox.cookies import is_logged_in_jar

            if not is_logged_in_jar(jar):
                await self.event_emitter.emit(
                    "posts.create_failed",
                    {"action_id": envelope.action_id, "reason": "login_required"},
                    dedupe_key=f"{envelope.action_id}-submit",
                )
                fresh = await session.cookies()
                return {
                    "submitted": False,
                    "subreddit": input_data.subreddit,
                    "reason": "login_required",
                    "_cookies": fresh,
                }

            if not await fill_first(page, SUBMIT_TITLE, input_data.title):
                raise RuntimeError("submit title field not found")
            if input_data.content:
                if not await fill_first(page, SUBMIT_BODY, input_data.content):
                    raise RuntimeError("submit body field not found")
            clicked = await click_first(page, SUBMIT_BUTTON)
            post_id = ""
            post_url = page.url
            if clicked:
                try:
                    await page.wait_for_url("**/comments/**", timeout=20000)
                except Exception:
                    pass
                post_url = page.url
                post_id = extract_post_id(post_url)
            submitted = bool(post_id)
            try:
                fresh = await session.cookies()
            except Exception:
                fresh = []
            result = {
                "submitted": submitted,
                "subreddit": input_data.subreddit,
                "title": input_data.title,
                "post_id": post_id,
                "url": post_url,
                "_cookies": fresh,
            }
            await self.event_emitter.emit(
                "posts.created" if submitted else "posts.create_failed",
                {
                    "action_id": envelope.action_id,
                    "subreddit": input_data.subreddit,
                    "post_id": post_id,
                    "url": post_url,
                    **({} if submitted else {"reason": "no post URL after submit"}),
                },
                dedupe_key=f"{envelope.action_id}-submit",
            )
            return result
        finally:
            await self.session_manager.release(session)
