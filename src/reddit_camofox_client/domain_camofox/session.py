"""Camofox session object and Reddit surface routing."""
from __future__ import annotations

import uuid
from typing import Any

from .constants import (
    REDDIT_BASE_URL,
    REDDIT_SEARCH_URL,
    REDDIT_SUBMIT_URL,
    SUPPORTED_SURFACES,
    SURFACE_POST,
    SURFACE_SEARCH,
    SURFACE_SUBMIT,
    SURFACE_SUBREDDIT,
)


class CamofoxSession:
    def __init__(self, account_id: str, runtime: Any, browser: Any, context: Any) -> None:
        self.account_id = account_id
        self.session_id = str(uuid.uuid4())
        self.runtime = runtime
        self.browser = browser
        self.context = context
        self._closed = False

    async def new_page(self) -> Any:
        return await self.context.new_page()

    async def cookies(self, urls: list[str] | None = None) -> list[dict[str, Any]]:
        targets = urls or [REDDIT_BASE_URL, "https://old.reddit.com"]
        return await self.context.cookies(targets)

    async def open_surface(self, surface: str, target: dict[str, Any] | None = None) -> Any:
        target = target or {}
        if surface not in SUPPORTED_SURFACES:
            raise ValueError(f"unsupported surface: {surface}")
        if surface == SURFACE_SUBREDDIT:
            url = target.get("url") or f"{REDDIT_BASE_URL}/r/{target['subreddit']}/new"
        elif surface == SURFACE_SEARCH:
            url = target.get("url") or f"{REDDIT_SEARCH_URL}?q={target.get('query', '')}"
        elif surface == SURFACE_POST:
            url = target.get("url") or f"{REDDIT_BASE_URL}{target.get('permalink', '')}"
        elif surface == SURFACE_SUBMIT:
            url = target.get("url") or f"{REDDIT_BASE_URL}/r/{target.get('subreddit', '')}/submit"
        else:
            raise ValueError(f"unsupported surface: {surface}")
        page = await self.context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        return page

    async def execute(self, activity: str, params: dict[str, Any]) -> dict[str, Any]:
        page = params.get("_page")
        if page is None:
            page = self.context.pages[-1] if self.context.pages else None
        if page is None:
            return {"results": []}
        title = await page.title()
        url = page.url
        body_text = await page.locator("body").inner_text()

        posts = []
        try:
            articles = page.locator("shreddit-post")
            count = await articles.count()
            for i in range(min(count, params.get("limit", 25))):
                post = articles.nth(i)
                text = (await post.inner_text()).strip()
                if text:
                    posts.append({"index": i, "text": text[:2000]})
        except Exception:
            posts = []

        return {"results": posts, "page_title": title, "page_url": url, "preview": body_text[:5000]}
