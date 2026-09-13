"""Human-like scroll execution against a real page.

Ported from ui-kit/scripts/video-agent/src/capability/scroll_motion.py,
minus the recording-specific logging: trajectories come from motion.py
and are driven via page.mouse.wheel() (page-level) or direct scrollTop
assignment (nested containers). Never uses scroll_into_view_if_needed
as the main movement (it jumps instantly); it stays a fallback only.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from .motion import ScrollStep, human_scroll_trajectory

LOGGER = logging.getLogger("reddit-camofox.scroll")


async def _preposition_mouse(page: Any, x: float | None, y: float | None, timeout: float = 5.0) -> None:
    """Park the cursor so wheel events register under a human-like pointer."""
    try:
        vp = page.viewport_size or {"width": 1280, "height": 800}
        mx = x if x is not None else vp["width"] * 0.5 + random.uniform(-60, 60)
        my = y if y is not None else vp["height"] * 0.45 + random.uniform(-50, 50)
        await asyncio.wait_for(page.mouse.move(mx, my), timeout=timeout)
    except (Exception, asyncio.TimeoutError) as exc:
        LOGGER.debug("scroll: could not pre-position mouse: %s", exc)


async def walk_segments_page(page: Any, steps: list[ScrollStep]) -> None:
    """Execute planned wheel deltas on the page."""
    await _preposition_mouse(page, None, None)
    for i, step in enumerate(steps, 1):
        try:
            await page.mouse.wheel(0, step.delta_y)
        except Exception as exc:
            LOGGER.debug("scroll step %d: wheel event failed (%s), stopping", i, type(exc).__name__)
            break
        await asyncio.sleep(step.delay_ms / 1000)


async def human_scroll_by(page: Any, distance: float, *, seed: int | None = None, precise: bool = False) -> None:
    """Scroll the page by distance px along a human trajectory.

    precise=True lands exactly (no overshoot/recoil) for final
    approaches onto known refs; travel scrolls keep full motion.
    """
    steps = human_scroll_trajectory(distance, seed=seed, precise=precise)
    if not steps:
        return
    await walk_segments_page(page, steps)


async def resolve_scroll_owner(page: Any, locator: Any) -> tuple[bool, dict[str, Any]]:
    """Nearest scrollable ancestor walk: (is_window, geometry).

    Geometry for nested containers carries scrollTop / clientHeight /
    scrollHeight / hoverX / hoverY / ownerSelector (a re-locatable CSS
    path, since a locator passed into evaluate() serializes instead of
    staying live).
    """
    result = await locator.evaluate("""
        (el) => {
            let cur = el;
            while (cur && cur !== document.documentElement) {
                const s = getComputedStyle(cur);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll' || s.overflowY === 'hidden')
                    && cur.scrollHeight > cur.clientHeight) {
                    const r = cur.getBoundingClientRect();
                    let path = [];
                    let node = cur;
                    while (node && node !== document.documentElement) {
                        let part = node.tagName.toLowerCase();
                        if (node.id) {
                            part = '#' + node.id;
                            path.unshift(part);
                            break;
                        }
                        const parent = node.parentElement;
                        if (parent) {
                            let idx = 1;
                            let sibling = parent.firstElementChild;
                            while (sibling && sibling !== node) {
                                idx++;
                                sibling = sibling.nextElementSibling;
                            }
                            part += ':nth-child(' + idx + ')';
                        }
                        path.unshift(part);
                        node = parent;
                    }
                    return {
                        isWindow: false,
                        scrollTop: cur.scrollTop,
                        clientHeight: cur.clientHeight,
                        scrollHeight: cur.scrollHeight,
                        hoverX: r.left + r.width / 2,
                        hoverY: r.top + r.height / 2,
                        ownerSelector: path.join(' > '),
                    };
                }
                cur = cur.parentElement;
            }
            return { isWindow: true };
        }
    """)
    return result["isWindow"], result


async def scroll_to_selector(page: Any, selector: str, *, seed: int | None = None) -> dict[str, Any]:
    """Ease a selector into view along a trajectory, then verify.

    Target rests ~28% viewport height from the top; distance is clamped
    to the max scroll so bottom-of-page elements do not request motion
    the browser cannot consume.
    """
    locator = page.locator(selector).first
    await locator.wait_for(state="attached", timeout=3000)

    is_window, geom = await resolve_scroll_owner(page, locator)
    if is_window:
        before = await page.evaluate("window.scrollY")
        max_scroll = await page.evaluate(
            "Math.max(0, document.documentElement.scrollHeight - window.innerHeight)"
        )
        target_y = await locator.evaluate("""
            el => {
                const rect = el.getBoundingClientRect();
                const absoluteY = rect.top + window.scrollY;
                return Math.max(0, absoluteY - window.innerHeight * 0.28);
            }
        """)
    else:
        owner_sel = geom.get("ownerSelector", "")
        owner_loc = page.locator(owner_sel).first if owner_sel else None
        if owner_loc is None:
            is_window = True
            before = await page.evaluate("window.scrollY")
            max_scroll = await page.evaluate(
                "Math.max(0, document.documentElement.scrollHeight - window.innerHeight)"
            )
            target_y = await locator.evaluate("""
                el => {
                    const rect = el.getBoundingClientRect();
                    const absoluteY = rect.top + window.scrollY;
                    return Math.max(0, absoluteY - window.innerHeight * 0.28);
                }
            """)
        else:
            before = geom["scrollTop"]
            max_scroll = max(0, geom["scrollHeight"] - geom["clientHeight"])
            target_y = await owner_loc.evaluate(
                """(container, el) => {
                    const cRect = container.getBoundingClientRect();
                    const eRect = el.getBoundingClientRect();
                    const absStart = (eRect.top - cRect.top) + container.scrollTop;
                    return Math.max(0, absStart - container.clientHeight * 0.28);
                }""",
                await locator.element_handle(),
            )

    target_y = min(target_y, max_scroll)
    distance = target_y - before

    steps = human_scroll_trajectory(distance, seed=seed, precise=True)
    if not steps:
        after = before
    elif is_window:
        await walk_segments_page(page, steps)
        # Final sub-pixel correction: center the ref after the human
        # travel. Correction only, never the primary motion.
        try:
            await locator.evaluate("el => el.scrollIntoView({block: 'center'})")
        except Exception:
            pass
        after = await page.evaluate("window.scrollY")
    else:
        await _preposition_mouse(page, geom.get("hoverX"), geom.get("hoverY"))
        for step in steps:
            try:
                await owner_loc.evaluate("(el, d) => { el.scrollTop += d; }", step.delta_y)
            except Exception:
                break
            await asyncio.sleep(step.delay_ms / 1000)
        after = await owner_loc.evaluate("el => el.scrollTop")

    if is_window:
        visible = await locator.evaluate("""
            el => {
                // Intersects the viewport (Playwright toBeInViewport): fully
                // on-screen is too strict under sticky headers/sidebars.
                const r = el.getBoundingClientRect();
                return r.top < window.innerHeight && r.bottom > 0 && r.height > 0;
            }
        """)
    else:
        visible = await owner_loc.evaluate(
            """(container, el) => {
                const r = el.getBoundingClientRect();
                const cR = container.getBoundingClientRect();
                return r.top >= cR.top && r.bottom <= cR.bottom && r.height > 0;
            }""",
            await locator.element_handle(),
        )
    return {"ok": visible, "ref": selector, "scroll_y_before": before, "scroll_y_after": after, "distance": distance}
