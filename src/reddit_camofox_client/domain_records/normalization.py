"""Normalize raw Reddit extraction (Atom/.json row -> NormalizedPostRecord)."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from reddit_camofox_client.domain_records.models import NormalizedPostRecord


class PostNormalizer:
    def normalize(self, raw: dict, account_id: str, source_action: str) -> NormalizedPostRecord:
        occurred = raw.get("occurred_at") or raw.get("published") or datetime.now(UTC)
        if isinstance(occurred, str):
            try:
                occurred = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
            except ValueError:
                occurred = datetime.now(UTC)
        return NormalizedPostRecord(
            record_id=f"rec-{uuid.uuid4().hex[:12]}",
            external_id=str(raw.get("post_id", "") or raw.get("external_id", "") or raw.get("id", "")),
            source=source_action,
            account_id=account_id,
            subreddit=str(raw.get("subreddit", "")),
            title=str(raw.get("title", "")),
            content=str(raw.get("content", "") or raw.get("selftext", "") or raw.get("text", "")),
            url=str(raw.get("url", "") or raw.get("permalink", "") or raw.get("link", "")),
            permalink=str(raw.get("permalink", "") or raw.get("url", "")),
            author={"id": raw.get("author_id", ""), "name": raw.get("author", "")},
            occurred_at=occurred,
            metrics={
                "score": raw.get("score", 0) or raw.get("metrics", {}).get("score", 0),
                "comments": raw.get("num_comments", 0) or raw.get("comments", 0),
                "upvote_ratio": raw.get("upvote_ratio", 0),
            },
            matched_terms=raw.get("matched_terms", []),
            raw_extraction=raw,
        )
