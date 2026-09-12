"""Registry + dispatch smoke: all 5 actions registered, no browser needed."""
import asyncio

import pytest

from reddit_camofox_client.api.actions import action_types, dispatch
from reddit_camofox_client.domain_actions.actions import build_default_runner
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope

EXPECTED = {"posts.listen", "posts.search", "posts.create", "subreddits.search", "comments.reply"}


def test_registry_names():
    runner = build_default_runner()
    assert set(runner.registry.names()) == EXPECTED


def test_api_action_types():
    assert set(action_types()) == EXPECTED


def test_unknown_action_rejected():
    runner = build_default_runner()
    env = ActionEnvelope(action_id="x", action_type="nope", account_id="a", input={}, idempotency_key="k")
    with pytest.raises(ValueError):
        asyncio.run(runner.run(env))


def test_dispatch_unknown_action_rejected():
    with pytest.raises(KeyError):
        asyncio.run(dispatch("nope", object(), object(), object()))
