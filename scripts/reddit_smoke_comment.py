"""Smoke test: load the real cookie jar from .env.local, open Camofox,
visit r/gtmengineering, find a post, and leave a short (<=5 word) comment.

Usage:
    python scripts/reddit_smoke_comment.py [--env-file .env.local] [--comment "Great insights, thanks for sharing"] [--live]

.env.local (gitignored, never commit):
    REDDIT_COOKIES_FILE=state/cookies.json   # browser-export JSON (preferred)
    # or REDDIT_COOKIES_JSON=[{...}]          # inline jar (not recommended)

Default is DRY RUN: everything up to the final submit. Pass --live to
actually post. --live requires a logged-in jar (token_v2 sub == "user")
and a comment of at most 5 words. Cookie values are never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

SUBREDDIT = "gtmengineering"
MAX_WORDS = 5
DEFAULT_COMMENT = "Great insights, thanks for sharing"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        values[key.strip()] = val
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
    if isinstance(raw, dict):  # accept {"cookies": [...]} wrappers
        raw = raw.get("cookies", raw.get("data", []))
    return raw


def mask_names(jar: list[dict]) -> list[str]:
    return sorted({str(c.get("name", "?")) for c in jar})


async def find_first_post(page) -> str | None:
    links = page.locator('a[href*="/comments/"]')
    try:
        count = await links.count()
    except Exception:
        return None
    seen: set[str] = set()
    for i in range(min(count, 40)):
        try:
            href = await links.nth(i).get_attribute("href")
        except Exception:
            continue
        if href and "/comments/" in href and href not in seen:
            seen.add(href)
            if href.startswith("/"):
                return f"https://www.reddit.com{href}"
            return href
    return None


async def main() -> int:
    parser = argparse.ArgumentParser(description="r/gtmengineering smoke comment (dry-run by default)")
    parser.add_argument("--env-file", default=".env.local")
    parser.add_argument("--comment", default=DEFAULT_COMMENT)
    parser.add_argument("--live", action="store_true", help="actually submit the comment")
    args = parser.parse_args()

    words = args.comment.split()
    if len(words) > MAX_WORDS:
        raise SystemExit(f"comment must be <= {MAX_WORDS} words, got {len(words)}: {args.comment!r}")

    from reddit_camofox_client.domain_camofox.cookies import from_browser_export, is_logged_in_jar
    from reddit_camofox_client.domain_camofox.session_manager import CamofoxSessionManager

    root = Path(__file__).resolve().parent.parent
    env = load_env_file(root / args.env_file)
    raw = load_jar(env, root)

    # Browser-export shape (expirationDate/storeId) -> Playwright shape; else passthrough.
    if raw and any("expirationDate" in c or "storeId" in c for c in raw if isinstance(c, dict)):
        jar = from_browser_export(raw)
        print("converted browser-export jar to Playwright shape")
    else:
        jar = raw
    print(f"jar cookies: {mask_names(jar)}")

    logged_in = is_logged_in_jar(jar)
    print(f"logged in: {logged_in}")
    if args.live and not logged_in:
        raise SystemExit("--live needs a logged-in jar (token_v2 sub == 'user'); refusing to post anonymously")

    manager = CamofoxSessionManager()
    session = await manager.acquire("smoke-test", cookies=jar)
    try:
        page = await session.new_page()
        await page.goto(f"https://www.reddit.com/r/{SUBREDDIT}/new", wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        print(f"opened r/{SUBREDDIT}: {page.url}")

        post_url = await find_first_post(page)
        if not post_url:
            raise SystemExit("no post links found on the subreddit page")
        print(f"target post: {post_url}")

        await page.goto(post_url, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass

        composer = None
        for sel in ["div[contenteditable='true']", "textarea[placeholder*='omment' i]", "shreddit-composer"]:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    composer = loc
                    print(f"composer found: {sel}")
                    break
            except Exception:
                continue
        if composer is None:
            raise SystemExit("comment composer not found (login wall or layout change?)")

        if not args.live:
            print(f"DRY RUN: would comment ({len(words)} words): {args.comment!r}")
            return 0

        await composer.click()
        await composer.fill(args.comment)
        posted = False
        for sel in ["button:has-text('Comment')", "button[type='submit']"]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    posted = True
                    break
            except Exception:
                continue
        print(f"submitted: {posted} | url: {page.url}")
        return 0 if posted else 1
    finally:
        await manager.release(session)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
