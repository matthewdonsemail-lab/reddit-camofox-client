"""Cookie-jar helpers: browser-export format -> Playwright format.

Browser extensions export cookies in Chrome's extension shape
(`expirationDate`, `hostOnly`, `session`, `storeId`, `sameSite` as
`null | "no_restriction" | "lax" | "strict"`). Playwright's
`context.add_cookies()` wants `{name, value, domain, path, expires,
httpOnly, secure, sameSite: "Strict" | "Lax" | "None"}`.
This module bridges the two. No secrets live here; callers pass jars in.
"""
from __future__ import annotations

from typing import Any

_SAMESITE_MAP = {
    "no_restriction": "None",
    "none": "None",
    "lax": "Lax",
    "strict": "Strict",
}


def from_browser_export(exported: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert a browser-extension cookie export to Playwright records."""
    converted: list[dict[str, Any]] = []
    for c in exported:
        record: dict[str, Any] = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".reddit.com"),
            "path": c.get("path", "/"),
        }
        if c.get("session"):
            record["expires"] = -1
        else:
            exp = c.get("expirationDate", c.get("expires", -1))
            record["expires"] = float(exp) if exp is not None else -1
        record["httpOnly"] = bool(c.get("httpOnly", False))
        record["secure"] = bool(c.get("secure", True))
        ss = c.get("sameSite")
        if isinstance(ss, str):
            mapped = _SAMESITE_MAP.get(ss.lower())
            if mapped:
                record["sameSite"] = mapped
        # sameSite null/unknown: omit and let the browser default.
        converted.append(record)
    return converted


def is_logged_in_jar(jar: list[dict[str, Any]]) -> bool:
    """True when the jar carries a logged-in Reddit session (token_v2
    with sub == "user", or legacy reddit_session). Routing signal only."""
    from reddit_camofox_client.domain_accounts.auth_guard import token_v2_subject

    by_name = {c.get("name"): c.get("value", "") for c in jar}
    token = by_name.get("token_v2", "")
    if token and token_v2_subject(token) == "user":
        return True
    return bool(by_name.get("reddit_session"))
