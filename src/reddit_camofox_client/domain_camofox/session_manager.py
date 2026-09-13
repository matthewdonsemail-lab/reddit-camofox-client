"""Account-scoped Camofox runtime lifecycle (per-request cookie jars)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .constants import CAMOFOX_GEOIP, CAMOFOX_HUMANIZE, CAMOFOX_HUMANIZE_FALLBACK
from .session import CamofoxSession

LOGGER = logging.getLogger("reddit-camofox.session")


def _as_context_cookies(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for c in cookies:
        record = dict(c)
        if "sameSite" not in record and "samesite" in record:
            record["sameSite"] = record.pop("samesite")
        if record.get("expires") is None or record["expires"] == 0:
            record["expires"] = -1
        normalized.append(record)
    return normalized


def _is_humanize_error(exc: BaseException) -> bool:
    return "humanize" in str(exc).lower()


class CamofoxSessionManager:
    def __init__(self, *, humanize: float | bool = CAMOFOX_HUMANIZE) -> None:
        self.humanize = humanize

    def _launch(self, proxy_config: dict[str, Any] | None, humanize: float | bool):
        from camoufox.async_api import AsyncCamoufox

        return AsyncCamoufox(
            humanize=humanize,
            geoip=CAMOFOX_GEOIP,
            proxy=proxy_config,
        )

    async def acquire(
        self,
        account_id: str,
        proxy_config: dict[str, Any] | None = None,
        storage_state_path: str | None = None,
        cookies: list[dict[str, Any]] | None = None,
    ) -> CamofoxSession:
        humanize = self.humanize
        try:
            runtime = self._launch(proxy_config, humanize)
            browser = await runtime.__aenter__()
        except Exception as exc:
            # Known Camoufox fault ("humanize:maxTime is not a double"):
            # retry once with humanize disabled rather than failing the action.
            if _is_humanize_error(exc) and humanize is not CAMOFOX_HUMANIZE_FALLBACK:
                LOGGER.warning("humanize launch failed (%s), retrying disabled", exc)
                humanize = CAMOFOX_HUMANIZE_FALLBACK
                runtime = self._launch(proxy_config, humanize)
                browser = await runtime.__aenter__()
            else:
                raise
        context_kwargs: dict[str, Any] = {}
        if storage_state_path:
            context_kwargs["storage_state"] = str(Path(storage_state_path))
        context = await browser.new_context(**context_kwargs)
        if cookies:
            try:
                await context.add_cookies(_as_context_cookies(cookies))
            except Exception:
                pass
        return CamofoxSession(account_id, runtime, browser, context)

    async def release(self, session: CamofoxSession) -> None:
        if session._closed:
            return
        session._closed = True
        try:
            await session.context.close()
        finally:
            await session.runtime.__aexit__(None, None, None)
