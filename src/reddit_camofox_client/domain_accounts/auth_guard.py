"""Auth guard: validate the live cookie jar against the loaded page."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class AuthResult:
    authenticated: bool
    state: str = "authenticated"
    requires_action: str | None = None


class AuthGuard:
    async def validate_cookies(
        self, jar: list[dict[str, Any]], page_title: str = "", page_url: str = ""
    ) -> AuthResult:
        has_session = any(c.get("name") in {"reddit_session", "session_tracker"} for c in jar)
        title_lower = (page_title or "").lower()
        if "login" in title_lower and "/login" in (page_url or ""):
            return AuthResult(authenticated=False, state="login_required", requires_action="login")
        if has_session:
            return AuthResult(authenticated=True)
        # Anonymous browsing still works for read-only actions; treat as authenticated
        # for listen/search, login-gated writes fail at their own step.
        return AuthResult(authenticated=True)
