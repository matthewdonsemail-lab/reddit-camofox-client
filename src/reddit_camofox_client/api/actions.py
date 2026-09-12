"""Generic action registry - every domain action passable over REST.

Typed convenience routes stay; this is the future-proof surface the
frontend builds against: POST /api/actions/{action_type}.

Shape mirrors Kennedy's facebook-camofox-client api/actions.py exactly:
REGISTRY maps action_type -> builder(manager, emitter) -> (action, _),
plus action_types() and dispatch().
"""
from __future__ import annotations

from typing import Any


def _posts_listen(manager, emitter):
    from reddit_camofox_client.domain_cursors.repository import InMemoryCursorRepository
    from reddit_camofox_client.domain_posts.listen import PostsListenAction
    from reddit_camofox_client.domain_records.normalization import PostNormalizer

    collected: list = []

    async def commit(rec):
        collected.append(rec)
        return True

    return PostsListenAction(manager, InMemoryCursorRepository(),
                             PostNormalizer(), emitter, commit), None


def _posts_search(manager, emitter):
    from reddit_camofox_client.domain_posts.search import PostsSearchAction
    from reddit_camofox_client.domain_records.normalization import PostNormalizer

    return PostsSearchAction(manager, PostNormalizer(), emitter), None


def _posts_create(manager, emitter):
    from reddit_camofox_client.domain_posts.submit import SubmitAction

    return SubmitAction(manager, emitter), None


def _subreddits_search(manager, emitter):
    from reddit_camofox_client.domain_subreddits.search import SubredditsSearchAction

    return SubredditsSearchAction(manager, emitter), None


def _comments_reply(manager, emitter):
    from reddit_camofox_client.domain_posts.reply import ReplyAction

    return ReplyAction(manager, emitter), None


REGISTRY: dict[str, Any] = {
    "posts.listen": _posts_listen,
    "posts.search": _posts_search,
    "posts.create": _posts_create,
    "subreddits.search": _subreddits_search,
    "comments.reply": _comments_reply,
}


def action_types() -> list[str]:
    return sorted(REGISTRY)


async def dispatch(action_type: str, manager, emitter, envelope):
    try:
        builder = REGISTRY[action_type]
    except KeyError:
        raise KeyError(f"unknown action_type: {action_type}")
    action, _ = builder(manager, emitter)
    out = await action.execute(envelope)
    if hasattr(out, "model_dump"):
        return out.model_dump(mode="json")
    return out
