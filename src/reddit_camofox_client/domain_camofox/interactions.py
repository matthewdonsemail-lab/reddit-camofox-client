"""Primitive browser interactions shared by Reddit domain actions.

Every act follows one strict, auditable lifecycle:

  resolve owner & geometry
    -> bell-curve scroll trajectory (scroll.scroll_to_selector)
    -> pre-position mouse and curve-glide to element
    -> micro-orbit hover with jittered dwell
    -> print/record the ref receipt (bounding box, coords, timestamps)
    -> click/fill fires

Flags (env; both default ON):

  CAMOFOX_ENFORCE_PRIMITIVES=1  trajectory/hover failures raise instead
      of silently falling back to instant jumps. Missing cursor hover
      aborts the action.
  CAMOFOX_PRINT_REFS=1          every resolved ref emits a [REF_TRACE]
      stdout line and is kept in the in-memory trace for calibration.

Raw locator.click()/fill() and scroll_into_view_if_needed as primary
motion are banned outside this module; everything routes through
fill_first/click_first.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from dataclasses import asdict, dataclass
from typing import Any

from .constants import MOUSE_MOVE_TIMEOUT_SECONDS

LOGGER = logging.getLogger("reddit-camofox.interactions")

ENFORCE_PRIMITIVES = os.getenv("CAMOFOX_ENFORCE_PRIMITIVES", "1").lower() in ("1", "true", "yes")
PRINT_REFS = os.getenv("CAMOFOX_PRINT_REFS", "1").lower() in ("1", "true", "yes")

# In-memory trace of every emitted ref receipt (calibration / replay).
REF_TRACES: list[dict[str, Any]] = []


@dataclass
class RefReceipt:
    selector: str
    box: dict[str, float]
    scroll_distance: float
    hover_x: float
    hover_y: float
    dwell_ms: float
    timestamp: float


def record_ref(receipt: RefReceipt) -> None:
    REF_TRACES.append(asdict(receipt))
    if PRINT_REFS:
        print(f"[REF_TRACE] {asdict(receipt)}", flush=True)


def get_ref_traces() -> list[dict[str, Any]]:
    return list(REF_TRACES)


def clear_ref_traces() -> None:
    REF_TRACES.clear()


async def human_move(page: Any, x: float, y: float, timeout: float = MOUSE_MOVE_TIMEOUT_SECONDS) -> bool:
    """Move the cursor along Camoufox's humanized trajectory, guarded.

    A broken bezier generator hangs instead of failing fast, so every
    move carries a hard timeout.
    """
    try:
        await asyncio.wait_for(page.mouse.move(x, y), timeout=timeout)
        return True
    except (Exception, asyncio.TimeoutError) as exc:
        LOGGER.debug("human_move failed (%s)", type(exc).__name__)
        return False


async def human_hover_and_orbit(page: Any, box: dict[str, float]) -> tuple[float, float, float]:
    """Glide to the element with targeting offset, dwell, micro-drift.

    Offset lands inside the inner 60% of the box (humans rarely hit dead
    center); dwell 140-380ms; drift a few px while "reading". Returns
    (hover_x, hover_y, dwell_ms). Raises under enforcement when the
    cursor cannot move at all.
    """
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2

    jitter_x = center_x + random.uniform(-box["width"] * 0.2, box["width"] * 0.2)
    jitter_y = center_y + random.uniform(-box["height"] * 0.2, box["height"] * 0.2)

    if not await human_move(page, jitter_x, jitter_y):
        raise RuntimeError("primitive enforcement failed: cursor glide to element failed")

    dwell = random.uniform(0.14, 0.38)
    await asyncio.sleep(dwell)

    drift_x = jitter_x + random.uniform(-3, 3)
    drift_y = jitter_y + random.uniform(-2, 2)
    await human_move(page, drift_x, drift_y)

    return drift_x, drift_y, dwell * 1000


async def reach(page: Any, selector: str, locator: Any, *, attempts: int = 3) -> bool:
    """Strict approach, bounded retries: resolve -> scroll -> visible-wait
    -> geometry -> orbit -> receipt.

    The locator is re-resolved fresh every attempt: wheel-scrolls trigger
    re-renders that detach the previously held node, and acting on a
    detached node always fails. Visibility is waited (auto-retry), not
    snapshotted. Raises under enforcement when attempts exhaust; returns
    False only when enforcement is off.
    """
    from .scroll import scroll_to_selector

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            fresh = page.locator(selector).first
            await fresh.wait_for(state="attached", timeout=5000)
            scroll_meta = await scroll_to_selector(page, selector)
            fresh = page.locator(selector).first
            await fresh.wait_for(state="visible", timeout=8000)
            box = await fresh.bounding_box()
            if not box:
                raise RuntimeError(f"no bounding box for '{selector}'")
            hover_x, hover_y, dwell_ms = await human_hover_and_orbit(page, box)
            record_ref(
                RefReceipt(
                    selector=selector,
                    box={k: float(v) for k, v in box.items() if isinstance(v, (int, float))},
                    scroll_distance=float(scroll_meta.get("distance", 0.0)),
                    hover_x=hover_x,
                    hover_y=hover_y,
                    dwell_ms=dwell_ms,
                    timestamp=time.time(),
                )
            )
            await asyncio.sleep(random.uniform(0.06, 0.18))
            return True
        except Exception as exc:
            last_error = exc
            LOGGER.debug("reach attempt %d/%d for '%s' failed (%s)", attempt, attempts, selector, exc)
    if ENFORCE_PRIMITIVES:
        raise RuntimeError(
            f"primitive enforcement failed: could not reach '{selector}' in {attempts} attempts ({last_error})"
        )
    return False


async def await_mount(
    page: Any,
    selectors: list[str],
    *,
    max_scrolls: int = 6,
    viewport_fraction: float = 0.65,
) -> str | None:
    """Progressively scroll until a selector mounts visible, return it.

    Comment trees lazy-mount on scroll: a single count snapshot right
    after load races hydration and loses. Each round eases down a
    viewport fraction (human trajectory) and re-checks.
    """
    from .scroll import human_scroll_by

    for _ in range(max_scrolls + 1):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    return sel
            except Exception:
                continue
        try:
            vp = page.viewport_size or {"height": 800}
            await human_scroll_by(page, vp["height"] * viewport_fraction)
        except Exception:
            pass
    return None


async def fill_focused(page: Any, value: str, typing_delay_ms: float = 30) -> bool:
    """Type into whatever currently holds focus (no locator needed).

    Rich editors (faceplate/shreddit shadow trees) often expose no
    visible node matching our selectors while genuinely focused. A user
    in that state just types. Verifies the focused element is editable
    first, then selects all + types with a human delay.
    """
    try:
        editable = await page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return false;
            const tag = el.tagName.toLowerCase();
            if (tag === 'input' || tag === 'textarea') return true;
            if (el.isContentEditable) return true;
            if (el.getAttribute && el.getAttribute('role') === 'textbox') return true;
            return false;
        }""")
        if not editable:
            return False
        await page.keyboard.press("ControlOrMeta+a")
        await page.keyboard.type(value, delay=typing_delay_ms)
        return True
    except Exception as exc:
        LOGGER.debug("focused fill failed (%s)", type(exc).__name__)
        return False


async def fill_first(page: Any, selectors: list[str], value: str, typing_delay_ms: float = 0) -> bool:
    """Fill via reach(). typing_delay_ms > 0 types character by character
    (visible, human) instead of an instant fill; falls back to fill.

    No is_visible snapshot: reach() waits visible with retries, and the
    fill itself auto-waits for actionability (bounded timeout).
    """
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                if not await reach(page, sel, loc):
                    continue
                if typing_delay_ms > 0:
                    try:
                        await loc.click(timeout=5000)
                        await loc.press("ControlOrMeta+a")
                        await loc.type(value, delay=typing_delay_ms)
                        return True
                    except Exception as exc:
                        LOGGER.debug("typed fill failed (%s), falling back to fill", type(exc).__name__)
                await loc.fill(value, timeout=8000)
                return True
        except Exception:
            continue
    return False


async def click_first(page: Any, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                if not await reach(page, sel, loc):
                    continue
                await loc.click(timeout=8000)
                return True
        except Exception:
            continue
    return False
