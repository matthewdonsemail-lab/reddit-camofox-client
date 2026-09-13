"""Smoke test: submit a text post to a subreddit via the real SubmitAction.

Usage:
    python scripts/reddit_smoke_post.py --title "..." --body "..." [--subreddit gtmengineering] [--live]

.env.local (gitignored, never commit):
    REDDIT_COOKIES_FILE=state/cookies.json

Default is DRY RUN: opens the submit page with the jar, verifies the
title/body/post controls are present and visible, prints what would be
posted. Pass --live to actually submit through SubmitAction (login gate,
/comments/ verification, post-id receipt). Cookie values are never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def load_jar(env: dict[str, str], root: Path) -> list[dict]:
    if env.get("REDDIT_COOKIES_FILE"):
        jar_path = (root / env["REDDIT_COOKIES_FILE"]).resolve()
        raw = json.loads(jar_path.read_text(encoding="utf-8"))
        print(f"loaded {len(raw)} cookies from {jar_path.name}")
    elif env.get("REDDIT_COOKIES_JSON"):
        raw = json.loads(env["REDDIT_COOKIES_JSON"])
        print(f"loaded {len(raw)} inline cookies")
    else:
        raise SystemExit("set REDDIT_COOKIES_FILE or REDDIT_COOKIES_JSON in .env.local")
    if isinstance(raw, dict):
        raw = raw.get("cookies", raw.get("data", []))
    return raw


async def main() -> int:
    parser = argparse.ArgumentParser(description="subreddit post smoke test (dry-run by default)")
    parser.add_argument("--env-file", default=".env.local")
    parser.add_argument("--subreddit", default="gtmengineering")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--live", action="store_true", help="actually submit the post")
    parser.add_argument("--enforce-primitives", action="store_true", help="force CAMOFOX_ENFORCE_PRIMITIVES=1")
    parser.add_argument("--no-enforce-primitives", action="store_true", help="force CAMOFOX_ENFORCE_PRIMITIVES=0")
    args = parser.parse_args()

    # Flags are read at domain import time, so apply .env.local + CLI first.
    root = Path(__file__).resolve().parent.parent
    env = load_env_file(root / args.env_file)
    for key in ("CAMOFOX_ENFORCE_PRIMITIVES", "CAMOFOX_PRINT_REFS"):
        if key in env:
            os.environ.setdefault(key, env[key])
    if args.enforce_primitives:
        os.environ["CAMOFOX_ENFORCE_PRIMITIVES"] = "1"
    if args.no_enforce_primitives:
        os.environ["CAMOFOX_ENFORCE_PRIMITIVES"] = "0"

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    if not args.title.strip():
        raise SystemExit("title must be non-empty")
    if len(args.title) > 300:
        raise SystemExit(f"title must be <= 300 chars, got {len(args.title)}")

    from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
    from reddit_camofox_client.domain_camofox.cookies import from_browser_export, is_logged_in_jar
    from reddit_camofox_client.domain_camofox.session_manager import CamofoxSessionManager
    from reddit_camofox_client.domain_camofox.selectors import SUBMIT_BODY, SUBMIT_BUTTON, SUBMIT_TITLE
    from reddit_camofox_client.domain_events.emitter import InMemoryEventEmitter
    from reddit_camofox_client.domain_posts.submit import SubmitAction

    raw = load_jar(env, root)
    if raw and any("expirationDate" in c or "storeId" in c for c in raw if isinstance(c, dict)):
        jar = from_browser_export(raw)
        print("converted browser-export jar to Playwright shape")
    else:
        jar = raw

    logged_in = is_logged_in_jar(jar)
    print(f"logged in: {logged_in}")
    if args.live and not logged_in:
        raise SystemExit("--live needs a logged-in jar; refusing to post anonymously")

    manager = CamofoxSessionManager()
    if not args.live:
        session = await manager.acquire("smoke-post-dryrun", cookies=jar)
        try:
            page = await session.new_page()
            await page.goto(f"https://www.reddit.com/r/{args.subreddit}/submit", wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            print(f"opened submit page: {page.url}")

            async def check(sels: list[str], label: str) -> bool:
                for sel in sels:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible():
                            print(f"  {label}: {sel}")
                            return True
                    except Exception:
                        continue
                print(f"  {label}: NOT FOUND")
                return False

            ok_title = await check(SUBMIT_TITLE, "title field")
            ok_body = await check(SUBMIT_BODY, "body field") if body else True
            ok_btn = await check(SUBMIT_BUTTON, "post button")
            print(f"DRY RUN: would post to r/{args.subreddit} | title={args.title!r} | body={len(body)} chars")
            return 0 if (ok_title and ok_body and ok_btn) else 1
        finally:
            await manager.release(session)

    action = SubmitAction(manager, InMemoryEventEmitter())
    envelope = ActionEnvelope(
        action_id="smoke-post-live",
        action_type="posts.create",
        account_id="smoke-test",
        input={"subreddit": args.subreddit, "title": args.title, "content": body, "_cookies": jar},
        idempotency_key="smoke-post-live",
    )
    result = await action.execute(envelope)
    print(f"submitted: {result.get('submitted')} | post_id: {result.get('post_id')} | url: {result.get('url')}")
    return 0 if result.get("submitted") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
