"""Primitive browser interactions shared by Reddit domain actions."""
from __future__ import annotations
from typing import Any


async def fill_first(page: Any, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.fill(value)
                return True
        except Exception:
            continue
    return False


async def click_first(page: Any, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.click()
                return True
        except Exception:
            continue
    return False
