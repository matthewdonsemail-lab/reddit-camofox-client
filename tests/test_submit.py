"""Submit-action tests: pure receipt parsing + validation (no browser)."""
import pytest
from reddit_camofox_client.domain_posts.submit import SubmitAction, extract_post_id


def test_extract_post_id():
    assert extract_post_id("https://www.reddit.com/r/gtmengineering/comments/1wcltur/some_slug/") == "1wcltur"
    assert extract_post_id("https://www.reddit.com/r/gtmengineering/submit/") == ""
    assert extract_post_id("") == ""


def test_empty_title_rejected_without_browser():
    action = SubmitAction(session_manager=object(), event_emitter=object())
    import asyncio
    from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
    env = ActionEnvelope(action_id="t", action_type="posts.create", account_id="a",
                         input={"subreddit": "x", "title": "   "}, idempotency_key="k")
    with pytest.raises(ValueError):
        asyncio.run(action.execute(env))
