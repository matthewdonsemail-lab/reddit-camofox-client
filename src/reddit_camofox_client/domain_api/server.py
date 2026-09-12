"""FastAPI HTTP server for the Reddit Camofox client.

Cookies travel per-request (no server persistence), mirroring Kennedy.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException

from reddit_camofox_client.domain_accounts.login import RedditLogin
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_connectors.openmagpie import RedditCamofoxConnector

from .schemas import ActionRequest, ActionResponse, Cookie, HealthResponse, LoginRequest, LoginResponse

LOGGER = logging.getLogger("reddit-camofox.api")


class AppState:
    def __init__(self) -> None:
        self.connector: RedditCamofoxConnector | None = None
        self.login_action = RedditLogin()


_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    LOGGER.info("Starting Reddit Camofox API server")
    _state.connector = RedditCamofoxConnector()
    yield
    LOGGER.info("Shutting down Reddit Camofox API server")
    _state.connector = None


app = FastAPI(title="Reddit Camofox Client API", version="0.1.0", lifespan=lifespan)


def _proxy_config(req: LoginRequest | ActionRequest) -> dict[str, str] | None:
    server = getattr(req, "proxy_server", None) or None
    if not server:
        return None
    cfg: dict[str, str] = {"server": server}
    if getattr(req, "proxy_username", None):
        cfg["username"] = req.proxy_username  # type: ignore[attr-defined]
    if getattr(req, "proxy_password", None):
        cfg["password"] = req.proxy_password  # type: ignore[attr-defined]
    return cfg


def _cookies_to_dicts(cookies: list[Cookie]) -> list[dict[str, Any]]:
    return [c.model_dump() for c in cookies]


def _cookies_from_context(raw_cookies: list[dict[str, Any]]) -> list[Cookie]:
    result: list[Cookie] = []
    for c in raw_cookies:
        ss = c.get("sameSite")
        if ss is None or ss == "None":
            ss = "None"
        result.append(Cookie(
            name=c["name"], value=c["value"],
            domain=c.get("domain", ".reddit.com"), path=c.get("path", "/"),
            expires=float(c.get("expires", -1)),
            httpOnly=bool(c.get("httpOnly", False)),
            secure=bool(c.get("secure", True)), sameSite=ss,
        ))
    return result


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    connector = _state.connector
    if connector is None:
        raise HTTPException(status_code=503, detail="Server not initialised")
    proxy = _proxy_config(req)
    session = await connector.session_manager.acquire(req.account_id, proxy_config=proxy)
    try:
        page = await session.open_surface("reddit_subreddit", {"subreddit": "all"})
        result = await _state.login_action.execute(page, username=req.username, password=req.password, totp_secret=req.totp_secret)
        if result.get("authenticated"):
            raw = await session.cookies()
            return LoginResponse(authenticated=True, account_id=req.account_id,
                                 cookies=_cookies_from_context(raw), state=result.get("state", "authenticated"))
        return LoginResponse(authenticated=False, account_id=req.account_id,
                             state=result.get("state", ""), error=result.get("error"))
    finally:
        await connector.session_manager.release(session)


@app.post("/action", response_model=ActionResponse)
async def run_action(req: ActionRequest) -> ActionResponse:
    connector = _state.connector
    if connector is None:
        raise HTTPException(status_code=503, detail="Server not initialised")
    action_id = req.action_id or f"api-{req.action_type}-{req.account_id}"
    idempotency_key = req.idempotency_key or action_id
    input_data = dict(req.input)
    if req.cookies:
        input_data["_cookies"] = _cookies_to_dicts(req.cookies)
    proxy = _proxy_config(req)
    if proxy:
        input_data["proxy_config"] = proxy
    envelope = ActionEnvelope(action_id=action_id, action_type=req.action_type,
                              account_id=req.account_id, input=input_data, idempotency_key=idempotency_key)
    try:
        result = await connector.runner.run(envelope)
    except Exception as exc:
        LOGGER.exception("Action %s failed", req.action_type)
        return ActionResponse(action_id=action_id, action_type=req.action_type,
                              account_id=req.account_id, status="failed", error=str(exc))
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    elif hasattr(result, "dict"):
        result = result.dict()
    raw_cookies = result.pop("_cookies", result.pop("cookies", []))
    cookies = _cookies_from_context(raw_cookies) if raw_cookies else []
    return ActionResponse(action_id=action_id, action_type=req.action_type,
                          account_id=req.account_id, status="completed", result=result, cookies=cookies)
