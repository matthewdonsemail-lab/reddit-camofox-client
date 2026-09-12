"""Login challenge detection (captcha / OTP / rate-limit)."""
from __future__ import annotations
from typing import Any


async def detect_challenge(page: Any) -> str | None:
    try:
        body = (await page.locator("body").inner_text()).lower()
    except Exception:
        return None
    for marker, name in [("captcha", "captcha"), ("verify you're human", "captcha"), ("one-time code", "otp")]:
        if marker in body:
            return name
    return None
