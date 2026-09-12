"""REST service over the domain actions (FastAPI).

CRM calls us (we serve). Cookies travel per request - no repository
of sessions. Conventions borrowed from Kennedy's facebook-camofox-client
api/app.py (itself borrowed from open-twenty-dialer): /api/* routes,
/healthz, bearer key optional via REDDIT_API_KEY env.

Endpoints:
  POST /api/actions/{action_type}  generic dispatch (the future-proof surface)
  GET  /api/actions                list registered action types
  POST /api/posts/listen           posts.listen convenience route
  POST /api/posts/search           posts.search convenience route
  POST /api/posts                  posts.create convenience route
  POST /api/subreddits/search      subreddits.search convenience route
  POST /api/comments/reply         comments.reply convenience route
  GET  /healthz                    liveness
"""
from __future__ import annotations

import os
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from reddit_camofox_client.api.actions import action_types, dispatch
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_camofox.session_manager import CamofoxSessionManager
from reddit_camofox_client.domain_events.emitter import InMemoryEventEmitter

app = FastAPI(title="reddit-camofox-client", version="0.1.0")


def _manager(cookies: list[dict] | None) -> CamofoxSessionManager:
    mgr = CamofoxSessionManager()
    real_acquire = mgr.acquire

    async def acquire(account_id, **kwargs):
        if cookies is not None:
            kwargs["cookies"] = cookies
        else:
            kwargs.setdefault(
                "storage_state_path",
                os.getenv("CAMOFOX_STORAGE_STATE"),
            )
        return await real_acquire(account_id, **kwargs)

    mgr.acquire = acquire  # type: ignore[assignment]
    return mgr


async def _api_key(authorization: str | None = Header(default=None)) -> None:
    required = os.getenv("REDDIT_API_KEY")
    if not required:
        return
    if authorization != f"Bearer {required}":
        raise HTTPException(status_code=401, detail="missing or invalid bearer key")


class ActionBody(BaseModel):
    account_id: str = "default"
    cookies: list[dict] | None = None
    idempotency_key: str | None = None
    input: dict = Field(default_factory=dict)


def _envelope(action_type: str, body: ActionBody) -> ActionEnvelope:
    return ActionEnvelope(
        action_id=f"api-{uuid.uuid4().hex[:12]}",
        action_type=action_type,
        account_id=body.account_id,
        input=dict(body.input),
        idempotency_key=body.idempotency_key or f"api-{uuid.uuid4().hex}",
    )


async def _run(action_type: str, body: ActionBody) -> dict:
    env = _envelope(action_type, body)
    try:
        result = await dispatch(action_type, _manager(body.cookies), InMemoryEventEmitter(), env)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown action_type: {action_type}")
    return {"action_id": env.action_id, "action_type": action_type, "result": result}


@app.get("/api/actions")
async def action_index(_: None = Depends(_api_key)):
    return {"action_types": action_types()}


@app.post("/api/actions/{action_type}")
async def run_action(action_type: str, body: ActionBody, _: None = Depends(_api_key)):
    return await _run(action_type, body)


@app.post("/api/posts/listen")
async def posts_listen(body: ActionBody, _: None = Depends(_api_key)):
    return await _run("posts.listen", body)


@app.post("/api/posts/search")
async def posts_search(body: ActionBody, _: None = Depends(_api_key)):
    return await _run("posts.search", body)


@app.post("/api/posts")
async def posts_create(body: ActionBody, _: None = Depends(_api_key)):
    return await _run("posts.create", body)


@app.post("/api/subreddits/search")
async def subreddits_search(body: ActionBody, _: None = Depends(_api_key)):
    return await _run("subreddits.search", body)


@app.post("/api/comments/reply")
async def comments_reply(body: ActionBody, _: None = Depends(_api_key)):
    return await _run("comments.reply", body)


@app.get("/healthz")
async def healthz():
    from datetime import UTC, datetime

    return {"ok": True, "at": datetime.now(UTC).isoformat()}
