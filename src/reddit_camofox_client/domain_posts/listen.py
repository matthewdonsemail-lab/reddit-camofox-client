"""posts.listen: continuous polling for new posts across subreddits.

Kennedy's posts.listen shape ported to Reddit: the persisted cursor
(last_post_id + watermark) filters out already-emitted posts even across
a dropped/reconnected session. Records commit before the cursor saves;
posts.new emits (in-process + HTTP push) only after the cursor is durable.
"""
from __future__ import annotations

import asyncio as _asyncio
from datetime import datetime

from reddit_camofox_client.domain_accounts.auth_guard import AuthGuard
from reddit_camofox_client.domain_actions.envelope import ActionEnvelope
from reddit_camofox_client.domain_posts.schemas import PostsListenInput, PostsListenOutput


def _parse_created_at(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class PostsListenAction:
    ACTION_TYPE = "posts.listen"
    CURSOR_KEY = "posts-listen"

    def __init__(self, session_manager, cursor_repo, normalizer, event_emitter, commit):
        self.session_manager = session_manager
        self.cursor_repo = cursor_repo
        self.normalizer = normalizer
        self.event_emitter = event_emitter
        self.commit = commit

    async def execute(self, envelope: ActionEnvelope) -> PostsListenOutput:
        cookies = envelope.input.pop("_cookies", [])
        input_data = PostsListenInput(**envelope.input)
        subreddits = input_data.subreddits or ["all"]
        scope_key = "+".join(sorted(subreddits))

        cursor = await self.cursor_repo.load(
            cursor_key=self.CURSOR_KEY,
            account_id=envelope.account_id,
            scope_key=scope_key,
        )
        watermark = cursor.watermark if cursor else None
        last_post_id = cursor.last_post_id if cursor else None

        session = await self.session_manager.acquire(envelope.account_id, cookies=cookies)
        try:
            subreddit = subreddits[0]
            page = await session.open_surface("reddit_subreddit", {"subreddit": subreddit})
            try:
                # Human scroll triggers Reddit's lazy-loaded feed before extraction.
                from reddit_camofox_client.domain_camofox.constants import SCROLL_VIEWPORT_FRACTION
                from reddit_camofox_client.domain_camofox.scroll import human_scroll_by

                vp = page.viewport_size or {"height": 800}
                await human_scroll_by(page, vp["height"] * SCROLL_VIEWPORT_FRACTION)
            except Exception:
                pass
            title = await page.title()
            url = page.url
            jar = await session.cookies()

            guard = AuthGuard()
            auth = await guard.validate_cookies(jar, page_title=title, page_url=url)
            if not auth.authenticated:
                await self.event_emitter.emit(
                    "posts.listen_failed",
                    {"action_id": envelope.action_id, "reason": auth.requires_action or "auth_required"},
                    dedupe_key=f"{envelope.action_id}-failed",
                )
                return PostsListenOutput(new_posts=[], cursor_advanced=False)

            raw_results = await session.execute("reddit_subreddit_listen", {
                "_page": page, "limit": input_data.limit, "page_url": url, "title": title,
            })

            new_records = []
            newest_watermark = watermark
            newest_post_id = last_post_id

            for post in raw_results.get("results", []):
                post.setdefault("subreddit", subreddit)
                post_id = post.get("post_id") or post.get("external_id") or post.get("id")
                created_at = _parse_created_at(post.get("occurred_at") or post.get("published"))

                if post_id is not None and post_id == last_post_id:
                    continue
                if watermark is not None and created_at is not None and created_at <= watermark:
                    continue

                rec = self.normalizer.normalize(
                    raw=post, account_id=envelope.account_id, source_action="posts.listen")
                new_records.append(rec)
                if created_at is not None and (newest_watermark is None or created_at > newest_watermark):
                    newest_watermark = created_at
                    newest_post_id = post_id

            # Commit all records before saving cursor or emitting.
            for rec in new_records:
                await self.commit(rec)

            cursor_advanced = newest_watermark != watermark or newest_post_id != last_post_id
            if cursor_advanced:
                from reddit_camofox_client.domain_cursors.models import Cursor

                await self.cursor_repo.save(Cursor(
                    cursor_key=self.CURSOR_KEY,
                    action_type="posts.listen",
                    account_id=envelope.account_id,
                    scope_key=scope_key,
                    last_post_id=newest_post_id or "",
                    watermark=newest_watermark,
                ))

            # Emit posts.new after cursor is durable (in-process + HTTP push,
            # concurrently so a catch-up poll never stalls the loop).
            async def _notify(rec) -> None:
                await self.event_emitter.emit(
                    "posts.new",
                    {
                        "action_id": envelope.action_id,
                        "record_id": rec.record_id,
                        "external_id": rec.external_id,
                        "subreddit": rec.subreddit,
                        "title": rec.title,
                        "url": rec.url,
                    },
                    dedupe_key=f"reddit:{rec.subreddit}:{rec.external_id}",
                )
                try:
                    from reddit_camofox_client.domain_contracts.webhooks import dispatch, post_new_event

                    author = rec.author if isinstance(rec.author, str) else rec.author.get("name", "")
                    occurred = getattr(rec, "occurred_at", None)
                    await dispatch(
                        post_new_event(
                            action_id=envelope.action_id, subreddit=rec.subreddit,
                            record_id=rec.record_id, post_id=rec.external_id,
                            title=getattr(rec, "title", "") or "",
                            content=getattr(rec, "content", "") or "",
                            url=getattr(rec, "url", "") or "",
                            author=author,
                            occurred_at=occurred.isoformat() if occurred else None,
                        ),
                        env_vars=("POSTS_WEBHOOK_URL", "REDDIT_WEBHOOK_URL"),
                    )
                except Exception:
                    pass

            await _asyncio.gather(*(_notify(rec) for rec in new_records))

            await self.event_emitter.emit(
                "posts.listen_completed",
                {
                    "action_id": envelope.action_id,
                    "new_count": len(new_records),
                    "cursor_advanced": cursor_advanced,
                },
                dedupe_key=f"{envelope.action_id}-completed",
            )

            fresh: list[dict] = []
            try:
                fresh = await session.cookies()
            except Exception:
                pass
            return PostsListenOutput(
                new_posts=[r.model_dump(mode="json") for r in new_records],
                cursor_advanced=cursor_advanced,
                cookies=fresh,
            )
        except Exception as exc:
            await self.event_emitter.emit(
                "posts.listen_failed",
                {"action_id": envelope.action_id, "reason": str(exc)},
                dedupe_key=f"{envelope.action_id}-failed",
            )
            raise
        finally:
            await self.session_manager.release(session)
