"""Reddit navigation helpers (URL builders)."""
from __future__ import annotations
from .constants import REDDIT_BASE_URL


def subreddit_new_url(subreddit: str) -> str:
    return f"{REDDIT_BASE_URL}/r/{subreddit}/new"


def search_url(query: str, subreddit: str = "", sort: str = "new") -> str:
    scope = f"/r/{subreddit}" if subreddit else ""
    return f"{REDDIT_BASE_URL}{scope}/search?q={query}&sort={sort}"


def post_url(permalink: str) -> str:
    return f"{REDDIT_BASE_URL}{permalink}"


def submit_url(subreddit: str) -> str:
    return f"{REDDIT_BASE_URL}/r/{subreddit}/submit"
