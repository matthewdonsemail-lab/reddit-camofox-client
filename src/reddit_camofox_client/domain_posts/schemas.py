"""Reddit post action schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field


class PostsListenInput(BaseModel):
    subreddits: list[str] = Field(default_factory=list)
    limit: int = Field(default=25, ge=1, le=100)
    since: str | None = None


class PostsListenOutput(BaseModel):
    new_posts: list[dict] = Field(default_factory=list)
    cursor_advanced: bool = False
    cookies: list[dict] = Field(default_factory=list)
    auth_state: str = "authenticated"
    auth_reason: str | None = None


class PostSearchInput(BaseModel):
    query: str
    subreddit: str = ""
    sort: str = "new"
    limit: int = Field(default=25, ge=1, le=100)


class PostSearchOutput(BaseModel):
    results: list[dict] = Field(default_factory=list)
    matched_subreddits: list[str] = Field(default_factory=list)
    cookies: list[dict] = Field(default_factory=list)


class PostSubmitInput(BaseModel):
    subreddit: str
    title: str
    content: str = ""
    kind: str = "self"


class PostReplyInput(BaseModel):
    post_id: str = ""
    parent_id: str = ""
    text: str
    subreddit: str = ""
