"""Outbound webhook push for posts.new (Kennedy parity).

Kennedy's facebook client pushes posts.new to POSTS_WEBHOOK_URL /
MARKETPLACE_WEBHOOK_URL after the cursor is durable. The Reddit client
does the same via POSTS_WEBHOOK_URL (fallback REDDIT_WEBHOOK_URL).
Failures are swallowed: the in-process emitter is the durable signal,
HTTP push is best-effort fan-out.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

LOGGER = logging.getLogger("reddit-camofox.webhooks")

DEFAULT_TIMEOUT_SECONDS = 10.0


def post_new_event(
    *,
    action_id: str,
    subreddit: str,
    record_id: str,
    post_id: str,
    title: str = "",
    content: str = "",
    url: str = "",
    author: str = "",
    occurred_at: str | None = None,
) -> dict[str, Any]:
    return {
        "event_type": "posts.new",
        "action_id": action_id,
        "record_id": record_id,
        "dedupe_key": f"reddit:{subreddit}:{post_id}",
        "payload": {
            "external_id": post_id,
            "kind": "new_post",
            "source": "reddit_subreddit",
            "subreddit": subreddit,
            "title": title,
            "content": content,
            "url": url,
            "author": author,
            "occurred_at": occurred_at,
        },
    }


def _webhook_urls(env_vars: tuple[str, ...]) -> list[str]:
    urls: list[str] = []
    for name in env_vars:
        value = os.getenv(name)
        if value:
            urls.extend(u.strip() for u in value.split(",") if u.strip())
    return urls


async def dispatch(event: dict[str, Any], env_vars: tuple[str, ...] = ("POSTS_WEBHOOK_URL", "REDDIT_WEBHOOK_URL")) -> None:
    urls = _webhook_urls(env_vars)
    if not urls:
        return

    async def _push(url: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                await client.post(url, json=event)
        except Exception as exc:
            LOGGER.warning("webhook push to %s failed: %s", url, exc)

    await asyncio.gather(*(_push(u) for u in urls))
