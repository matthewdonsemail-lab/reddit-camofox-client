"""Account-scoped Camofox runtime lifecycle (per-request cookie jars)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import CAMOFOX_GEOIP, CAMOFOX_HUMANIZE
from .session import CamofoxSession


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


class CamofoxSessionManager:
    async def acquire(
        self,
        account_id: str,
        proxy_config: dict[str, Any] | None = None,
        storage_state_path: str | None = None,
        cookies: list[dict[str, Any]] | None = None,
    ) -> CamofoxSession:
        from camoufox.async_api import AsyncCamoufox

        runtime = AsyncCamoufox(
            humanize=CAMOFOX_HUMANIZE,
            geoip=CAMOFOX_GEOIP,
            proxy=proxy_config,
        )
        browser = await runtime.__aenter__()
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
