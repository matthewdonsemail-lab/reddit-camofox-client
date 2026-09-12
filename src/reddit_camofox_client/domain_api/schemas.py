"""HTTP request/response schemas for the Reddit Camofox API."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: float = -1
    httpOnly: bool = False
    secure: bool = True
    sameSite: str = "Lax"


class LoginRequest(BaseModel):
    account_id: str
    username: str
    password: str
    totp_secret: str | None = None
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None


class LoginResponse(BaseModel):
    authenticated: bool
    account_id: str
    cookies: list[Cookie] = Field(default_factory=list)
    state: str = ""
    error: str | None = None


class ActionRequest(BaseModel):
    action_id: str = ""
    action_type: str
    account_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    cookies: list[Cookie] = Field(default_factory=list)
    idempotency_key: str = ""
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None


class ActionResponse(BaseModel):
    action_id: str
    action_type: str
    account_id: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    cookies: list[Cookie] = Field(default_factory=list)
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
