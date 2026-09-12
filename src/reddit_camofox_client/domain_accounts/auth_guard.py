"""Auth guard: validate the live Reddit cookie jar against the loaded page.

Reddit's live session cookie is `token_v2` (a JWT); `reddit_session` is
legacy and only present on some accounts. A `token_v2` whose JWT payload
has `sub == "user"` is a logged-in session; `sub == "loid"` is anonymous.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class AuthResult:
    authenticated: bool
    state: str = "authenticated"
    requires_action: str | None = None
    login_type: str = "anonymous"  # "user" | "anonymous" | "legacy"


def token_v2_subject(value: str) -> str | None:
    """Best-effort read of a token_v2 JWT `sub` claim (no signature check;
    routing signal only, never a security decision)."""
    try:
        parts = value.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("sub")
    except Exception:
        return None


class AuthGuard:
    async def validate_cookies(
        self, jar: list[dict[str, Any]], page_title: str = "", page_url: str = ""
    ) -> AuthResult:
        by_name = {c.get("name"): c.get("value", "") for c in jar}

        token = by_name.get("token_v2", "")
        if token:
            sub = token_v2_subject(token)
            if sub == "user":
                return AuthResult(authenticated=True, login_type="user")
            # Anonymous token (sub == "loid") or unreadable: fall through to
            # legacy checks, then treat as anonymous-but-usable for reads.

        if by_name.get("reddit_session"):
            return AuthResult(authenticated=True, login_type="legacy")

        title_lower = (page_title or "").lower()
        if "login" in title_lower and "/login" in (page_url or ""):
            return AuthResult(authenticated=False, state="login_required",
                              requires_action="login", login_type="anonymous")

        # Anonymous browsing still works for read-only actions (listen/search);
        # login-gated writes fail at their own step.
        return AuthResult(authenticated=True, login_type="anonymous")
