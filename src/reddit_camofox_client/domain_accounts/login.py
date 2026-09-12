"""Reddit login via Camofox (username/password + optional TOTP via authenticator app)."""
from __future__ import annotations
from typing import Any


class RedditLogin:
    async def execute(
        self,
        page: Any,
        username: str,
        password: str,
        totp_secret: str | None = None,
    ) -> dict:
        from reddit_camofox_client.domain_camofox.interactions import click_first, fill_first
        from reddit_camofox_client.domain_camofox.selectors import LOGIN_PASSWORD, LOGIN_SUBMIT, LOGIN_USERNAME

        await fill_first(page, LOGIN_USERNAME, username)
        await fill_first(page, LOGIN_PASSWORD, password)
        await click_first(page, LOGIN_SUBMIT)
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        title = ""
        try:
            title = await page.title()
        except Exception:
            pass
        authenticated = "login" not in (title or "").lower()
        return {"authenticated": authenticated, "state": "authenticated" if authenticated else "login_required"}
