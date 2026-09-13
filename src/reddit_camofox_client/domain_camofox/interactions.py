"""Primitive browser interactions shared by Reddit domain actions.

Every act follows one mandatory path: ease -> hover -> act. The element
is eased into view along a bell-curve scroll trajectory (never an
instant jump), the cursor moves to its center on Camoufox's humanized
bezier path, and only then does the fill/click happen. This mirrors the
video-agent convention (ui-kit/scripts/video-agent): instant jumps and
cursor-less acts are what get flagged.

Raw locator.click()/fill() and scroll_into_view_if_needed as primary
motion are banned outside this module; everything routes through
fill_first/click_first.
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


async def ease_into_view(page: Any, selector: str) -> bool:
    """Ease a selector into view along a scroll trajectory.

    Falls back to the instant jump only when the trajectory fails; the
    jump is a last resort, never the primary motion.
    """
    try:
        from .scroll import scroll_to_selector

        await scroll_to_selector(page, selector)
        return True
    except Exception as exc:
        LOGGER.debug("trajectory scroll failed (%s), falling back to jump", type(exc).__name__)
    try:
        loc = page.locator(selector).first
        await loc.scroll_into_view_if_needed(timeout=5000)
        return True
    except Exception:
        return False


async def hover_locator(page: Any, locator: Any) -> bool:
    """Hover an element's center: read the bounding box, move there."""
    try:
        box = await locator.bounding_box()
        if not box:
            return False
        return await human_move(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    except Exception as exc:
        LOGGER.debug("hover failed (%s)", type(exc).__name__)
        return False


async def reach(page: Any, selector: str, locator: Any) -> bool:
    """The full approach: ease into view, then hover center.

    Returns True when the element is visible afterwards. Acting without
    reaching first is banned.
    """
    await ease_into_view(page, selector)
    await hover_locator(page, locator)
    try:
        return bool(await locator.is_visible())
    except Exception:
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
            if await loc.count() > 0 and await loc.is_visible():
                await reach(page, sel, loc)
                await loc.fill(value)
                return True
        except Exception:
            continue
    return False


async def click_first(page: Any, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await reach(page, sel, loc)
                await loc.click(timeout=5000)
                return True
        except Exception:
            continue
    return False

