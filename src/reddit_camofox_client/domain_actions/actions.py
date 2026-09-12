"""Standardized domain action registry: the 5 core Reddit actions.

Dispatch signature matches Kennedy's facebook client exactly:
each handler takes an ActionEnvelope and returns a dict (or pydantic
model, normalized by the HTTP layer).
"""
from __future__ import annotations

from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_camofox.session_manager import CamofoxSessionManager
from reddit_camofox_client.domain_cursors.repository import InMemoryCursorRepository
from reddit_camofox_client.domain_events.emitter import InMemoryEventEmitter
from reddit_camofox_client.domain_posts.listen import PostsListenAction
from reddit_camofox_client.domain_posts.reply import ReplyAction
from reddit_camofox_client.domain_posts.schemas import (
    PostReplyInput,
    PostSearchInput,
    PostSubmitInput,
)
from reddit_camofox_client.domain_posts.search import PostsSearchAction
from reddit_camofox_client.domain_posts.submit import SubmitAction
from reddit_camofox_client.domain_records.normalization import PostNormalizer
from reddit_camofox_client.domain_subreddits.schemas import SubredditSearchInput
from reddit_camofox_client.domain_subreddits.search import SubredditsSearchAction

# action_type -> (domain handler path, payload input, output/event)
# | posts.listen      | domain_posts.listen      | { subreddits: [...], limit: 25 }                 | emits posts.new webhook |
# | posts.search      | domain_posts.search      | { query, subreddit, sort }                      | list of normalized posts |
# | posts.create      | domain_posts.submit      | { subreddit, title, content }                   | created post receipt |
# | subreddits.search | domain_subreddits.search | { query }                                       | list of matching communities |
# | comments.reply    | domain_posts.reply       | { post_id, parent_id, text }                    | reply confirmation |


def build_default_runner(
    session_manager: CamofoxSessionManager | None = None,
    cursor_repo: InMemoryCursorRepository | None = None,
    emitter: InMemoryEventEmitter | None = None,
):
    """Build an ActionRunner with the 5 core Reddit actions registered."""
    from reddit_camofox_client.domain_actions.runner import ActionRunner

    session_manager = session_manager or CamofoxSessionManager()
    cursor_repo = cursor_repo or InMemoryCursorRepository()
    emitter = emitter or InMemoryEventEmitter()
    normalizer = PostNormalizer()

    async def _commit(rec) -> bool:
        return True

    listen = PostsListenAction(session_manager, cursor_repo, normalizer, emitter, _commit)
    search = PostsSearchAction(session_manager, normalizer, emitter)
    submit = SubmitAction(session_manager, emitter)
    subreddits = SubredditsSearchAction(session_manager, emitter)
    reply = ReplyAction(session_manager, emitter)

    runner = ActionRunner()
    runner.register("posts.listen", listen.execute)
    runner.register("posts.search", search.execute)
    runner.register("posts.create", submit.execute)
    runner.register("subreddits.search", subreddits.execute)
    runner.register("comments.reply", reply.execute)
    return runner


__all__ = [
    "ActionEnvelope",
    "PostSearchInput",
    "PostSubmitInput",
    "PostReplyInput",
    "SubredditSearchInput",
    "build_default_runner",
]
