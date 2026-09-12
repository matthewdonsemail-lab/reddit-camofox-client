"""Subreddit search schemas."""
from pydantic import BaseModel, Field


class SubredditSearchInput(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class SubredditSearchOutput(BaseModel):
    results: list[dict] = Field(default_factory=list)
    cookies: list[dict] = Field(default_factory=list)
