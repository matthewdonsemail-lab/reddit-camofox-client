"""Webhook payload contracts (John parity).

Mirrors John's `NewRedditPostPayload` (kind `reddit_subreddit`,
PAYLOAD_KIND `new_post`) so `posts.new` webhooks hydrate directly
into OpenMagpie FeedItems.
"""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

SOURCE_KIND = "reddit_subreddit"
PAYLOAD_KIND = "new_post"


class RedditPostWebhook(BaseModel):
    external_id: str
    kind: str = PAYLOAD_KIND
    source: str = SOURCE_KIND
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str = ""
    content: str = ""
    url: str = ""
    permalink: str = ""
    subreddit: str = ""
    author: str = ""
    parent_external_id: str = ""

    def dedupe_key(self) -> str:
        return f"reddit:{self.subreddit}:{self.external_id}"

    def to_openmagpie_item(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PostsNewEvent(BaseModel):
    """Envelope emitted on `posts.new`: one normalized record per post."""

    event_type: str = "posts.new"
    action_id: str
    record_id: str
    dedupe_key: str
    payload: RedditPostWebhook
