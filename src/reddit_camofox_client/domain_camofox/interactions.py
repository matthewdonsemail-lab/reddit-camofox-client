"""Primitive browser interactions shared by Reddit domain actions.

Cursor motion follows the video-agent convention
(ui-kit/scripts/video-agent): Camoufox's native humanize (float, never
bool) draws the bezier trajectory for every mouse.move, so hovering an
element center before acting is what makes clicks/fills read as human.
Every move is timeout-guarded because a broken bezier generator hangs
instead of failing fast.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .constants import MOUSE_MOVE_TIMEOUT_SECONDS

LOGGER = logging.getLogger("reddit-camofox.interactions")


async def human_move(page: Any, x: float, y: float, timeout: float = MOUSE_MOVE_TIMEOUT_SECONDS) -> bool:
    """Move the cursor along Camoufox's humanized trajectory, guarded."""
    try:
        await asyncio.wait_for(page.mouse.move(x, y), timeout=timeout)
        return True
    except (Exception, asyncio.TimeoutError) as exc:
        LOGGER.debug("human_move failed (%s), continuing without hover", type(exc).__name__)
        return False


async def hover_locator(page: Any, locator: Any) -> bool:
    """Hover an element's center (video-agent click convention: scroll
    into view, read the bounding box, move there, then act)."""
    try:
        await locator.scroll_into_view_if_needed(timeout=5000)
        box = await locator.bounding_box()
        if not box:
            return False
        return await human_move(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    except Exception as exc:
        LOGGER.debug("hover failed (%s)", type(exc).__name__)
        return False


async def _first_visible(page: Any, selectors: list[str]):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            continue
    return None


async def fill_first(page: Any, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await hover_locator(page, loc)
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
                await hover_locator(page, loc)
                await loc.click(timeout=5000)
                return True
        except Exception:
            continue
    return False
